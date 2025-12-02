"""
WebSocket 실시간 롤플레잉 엔드포인트
=====================================
음성 기반 실시간 영어 회화 연습을 위한 WebSocket 서버.

흐름:
1. WebSocket 연결 → Redis 세션 검증 (1회)
2. INIT 메시지 → 세션 초기화 → 첫 AI 질문 전송
3. 오디오 스트리밍 → STT → AI 응답 → TTS (클라이언트)
4. END_SESSION → 세션 종료 → Spring 2 알림

책임:
- WebSocket 연결 관리
- 메시지 라우팅 (메시지 라우터 사용)
- 세션 검증 및 상태 관리
- 에러 핸들링

역할 분리:
- ws_realtime_handler.py: WebSocket 엔드포인트 (이 파일)
- message_handlers.py: 메시지별 핸들러 구현
- ws_message_router.py: 메시지 라우팅 로직
- services/stt_service.py: STT 처리
- services/ai_tutor_service.py: AI 응답 생성
- integrations/clients/spring2_client.py: Spring 2 통신
- session_manager.py: 세션 상태 관리
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app.integrations.clients.redis_client import RedisSessionValidator
from app.roleplaying.core.session_state_manager import SessionStatus, session_manager
from app.roleplaying.handlers.session_validators import ErrorHandler, InitStateValidator
from app.roleplaying.handlers.ws_message_router import create_message_router
from app.roleplaying.handlers.message_handlers import (
    handle_init, handle_user_text,
    handle_utterance_end, handle_end_session
)

logger = logging.getLogger(__name__)


# ========================================
# 유틸리티 함수
# ========================================


def _handle_task_error(task: asyncio.Task, context: str = "") -> None:
    """
    Background task 완료 콜백 - 에러 처리

    Args:
        task: 완료된 asyncio.Task
        context: 컨텍스트 정보 (로깅용)
    """
    try:
        if task.cancelled():
            logger.debug(f"Background task cancelled: {context}")
            return

        exception = task.exception()
        if exception is not None:
            logger.error(
                f"Background task failed: {context}",
                exc_info=(type(exception), exception, exception.__traceback__)
            )
        else:
            result = task.result()
            logger.debug(f"Background task completed: {context}, result={result}")
    except asyncio.CancelledError:
        logger.debug(f"Background task cancellation detected: {context}")
    except Exception as e:
        logger.error(f"Error in task error handler: {e}", exc_info=True)

router = APIRouter()

# Redis 검증기 (전역 인스턴스)
redis_validator = RedisSessionValidator(settings.REDIS_URL)


# ========================================
# WebSocket 엔드포인트
# ========================================
@router.websocket("/ws/roleplaying/{session_id}")
async def roleplaying_websocket(websocket: WebSocket, session_id: str):
    """
    실시간 롤플레잉 WebSocket 엔드포인트

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID (Spring 1에서 발급)

    흐름:
        1. 연결 수락
        2. Redis 세션 검증 (1회만)
        3. INIT 메시지 대기
        4. 메시지 수신 루프 시작 (메시지 라우터 사용)
        5. 연결 종료 시 정리
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted: {session_id}")

    try:
        # ========================================
        # Step 1: 세션 검증 (Redis 캐시 → Spring 2 조회)
        # ========================================
        session_data = await _validate_session(session_id)

        if not session_data:
            logger.warning(f"Invalid session: {session_id}")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid session"
            )
            return

        user_id = session_data.get("userId") or session_data.get("user_id")
        scenario_id = session_data.get("scenarioId") or session_data.get("scenario_id")
        logger.info(
            f"Session validated: {session_id}, user_id={user_id}, scenario_id={scenario_id}"
        )

        # ========================================
        # Step 2: 메시지 라우터 생성 및 websocket.scope 설정
        # ========================================
        # websocket.scope에 session_data와 user_id를 저장 (핸들러에서 접근 가능하도록)
        websocket.scope["session_data"] = session_data
        websocket.scope["user_id"] = user_id

        # 메시지 라우터 생성 (4개 핸들러 등록)
        # 참고: audio_chunk는 binary 데이터로 메인 루프에서 직접 처리하므로 라우터에 등록하지 않음
        message_router = create_message_router(
            init_handler=handle_init,
            user_text_handler=handle_user_text,
            utterance_end_handler=handle_utterance_end,
            end_session_handler=handle_end_session
        )

        # ========================================
        # Step 3: 메시지 수신 루프
        # ========================================
        session_initialized = False

        while True:
            # 메시지 수신
            raw_data = await websocket.receive()

            # Binary 메시지 (오디오 청크)
            if "bytes" in raw_data:
                if not await InitStateValidator.validate_for_message(
                    websocket, "AUDIO_CHUNK", session_initialized
                ):
                    continue

                # 오디오 청크를 세션 버퍼에 저장 (라우터를 거치지 않음 - binary 데이터)
                try:
                    session_manager.append_audio_chunk(session_id, raw_data["bytes"])
                    logger.debug(f"Audio chunk appended: session={session_id}, size={len(raw_data['bytes'])} bytes")
                except Exception as e:
                    logger.error(f"Failed to append audio chunk: {e}", exc_info=True)
                continue

            # Text 메시지 (JSON)
            if "text" in raw_data:
                try:
                    message = json.loads(raw_data["text"])
                    message_type = message.get("type")

                    logger.debug(
                        f"Received message: type={message_type}, session={session_id}"
                    )

                    # 메시지별 초기화 상태 검증
                    if not await InitStateValidator.validate_for_message(
                        websocket, message_type, session_initialized
                    ):
                        continue

                    # 메시지 라우터를 통해 디스패치
                    dispatch_result = await message_router.dispatch(websocket, session_id, message)

                    if not dispatch_result:
                        logger.warning(f"Failed to dispatch message: type={message_type}")
                        continue

                    # INIT 메시지 후 세션 초기화 표시
                    if message_type == "INIT":
                        session_initialized = True

                    # 특정 메시지 후 세션 상태 확인
                    if message_type in ["UTTERANCE_END", "USER_TEXT", "END_SESSION"]:
                        session_state = session_manager.get_session(session_id)
                        if not session_state or session_state.status != SessionStatus.ACTIVE:
                            break

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    await ErrorHandler.send_error(websocket, "Invalid JSON format")

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await ErrorHandler.send_error(websocket, f"Processing error: {str(e)}")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
        await _cleanup_session(session_id, "disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await _cleanup_session(session_id, "error")

        try:
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error"
            )
        except Exception:
            pass  # 이미 연결이 끊긴 경우


# ========================================
# 유틸리티 함수 (SessionManager와 함께 사용)
# ========================================


async def _validate_session(session_id: str) -> Optional[dict]:
    """
    세션 확인 (Redis 캐시 → Spring 2 조회)

    Args:
        session_id: 세션 ID (UUID)

    Returns:
        세션 데이터 또는 None (세션 없음)
        {
            "userId": 1,
            "scenarioId": 31,
            "status": "ACTIVE"
        }
    """
    # 1. Redis 캐시 확인
    session_data = await redis_validator.validate_session(session_id)

    if session_data:
        logger.info(f"Session cache hit: {session_id}")
        return session_data

    # 2. Redis 미스 → Spring 2 조회
    logger.info(f"Session cache miss: {session_id}, querying Spring 2...")

    try:
        from app.integrations.clients.spring2_client import spring2_client

        spring2_data = await spring2_client.get_session(session_id)

        if spring2_data and spring2_data.get("success"):
            # Spring 2 응답을 Redis 형식으로 변환
            session_data = {
                "userId": spring2_data.get("user_id"),
                "scenarioId": spring2_data.get("scenario_id"),
                "status": spring2_data.get("status", "ACTIVE"),
            }

            # 3. Redis에 캐싱 (2시간)
            from app.integrations.clients.redis_client import get_redis_client

            redis_client = await get_redis_client()
            await redis_client.setex(
                f"session:{session_id}", settings.ROLEPLAY_REDIS_CACHE_TTL, json.dumps(session_data)
            )

            logger.info(f"Session loaded from Spring 2 and cached: {session_id}")
            return session_data

        logger.warning(f"Session not found in Spring 2: {session_id}")
        return None

    except Exception as e:
        logger.error(f"Session validation error: {e}", exc_info=True)
        return None


async def _cleanup_session(session_id: str, reason: str) -> None:
    """세션 정리 (연결 끊김 또는 에러 시)"""
    try:
        # STT 스트리밍 세션 강제 정리 (최종 결과 대기 없이)
        from app.roleplaying.services.stt.speech_to_text_service import stt_service
        try:
            # ✅ cleanup() 사용: finalize_streaming()과 달리 최종 결과를 기다리지 않음
            # 이는 예상치 못한 클라이언트 연결 해제 시 리소스 누수를 방지합니다
            await stt_service.cleanup(session_id)
            logger.debug(f"STT streaming session cleaned up: {session_id}")
        except Exception as e:
            logger.debug(f"STT streaming cleanup failed (non-fatal): {e}")

        session_state = session_manager.get_session(session_id)
        if session_state and session_state.status == SessionStatus.ACTIVE:
            session_manager.end_session(session_id, reason)

            # Spring 2에 세션 완료 알림
            from app.integrations.clients.spring2_client import spring2_client

            try:
                await spring2_client.complete_session(
                    session_id=session_id,
                    status="ERROR" if reason == "error" else "FINISHED",
                    reason=reason
                )
            except Exception as e:
                logger.error(f"Failed to notify Spring 2 during cleanup: {e}")
                # 에러가 나도 cleanup은 계속 진행

        session_manager.cleanup(session_id)
        logger.info(f"Session cleaned up: {session_id}, reason={reason}")

    except Exception as e:
        logger.error(f"Cleanup error: {e}", exc_info=True)
