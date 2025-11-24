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
- 메시지 라우팅 (INIT, AUDIO_CHUNK, UTTERANCE_END, END_SESSION)
- 세션 검증 및 상태 관리
- STT/AI 서비스 조율
- 에러 핸들링

역할 분리:
- ws_realtime.py: 메시지 라우팅 및 흐름 제어 (이 파일)
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
from app.roleplaying.session_manager import SessionStatus, SessionState, session_manager
from app.roleplaying.validators import (ErrorHandler, InitStateValidator,
                                        SessionValidator)
from app.roleplaying.ws_models import (AckMessage, AiTextMessage,
                                       AiTypingMessage, EndSessionMessage,
                                       InitMessage, SessionEndedMessage,
                                       SttFinalMessage, SttPartialMessage,
                                       UserTextMessage, UtteranceEndMessage,
                                       UtteranceSavedMessage)

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
        4. 메시지 수신 루프 시작
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
        # Step 2: 메시지 수신 루프
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

                await _handle_audio_chunk(websocket, session_id, raw_data["bytes"])
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

                    # INIT 메시지
                    if message_type == "INIT":
                        init_msg = InitMessage(**message)
                        await _handle_init(
                            websocket, session_id, user_id, session_data, init_msg
                        )
                        session_initialized = True

                    # UTTERANCE_END 메시지
                    elif message_type == "UTTERANCE_END":
                        session_state = await SessionValidator.validate_active(
                            websocket, session_id
                        )
                        if not session_state:
                            break

                        await _handle_utterance_end(websocket, session_id)

                        # 세션이 종료되었으면 루프 탈출
                        session_state = session_manager.get_session(session_id)
                        if not session_state or session_state.status != SessionStatus.ACTIVE:
                            break

                    # USER_TEXT 메시지 (테스트용 - STT 없이 텍스트로 직접 전송)
                    elif message_type == "USER_TEXT":
                        session_state = await SessionValidator.validate_active(
                            websocket, session_id
                        )
                        if not session_state:
                            break

                        user_text_msg = UserTextMessage(**message)
                        await _handle_user_text(
                            websocket, session_id, user_text_msg.text
                        )

                        # 세션이 종료되었으면 루프 탈출
                        session_state = session_manager.get_session(session_id)
                        if not session_state or session_state.status != SessionStatus.ACTIVE:
                            break

                    # END_SESSION 메시지
                    elif message_type == "END_SESSION":
                        await _handle_end_session(websocket, session_id, "user_end")
                        break  # 루프 종료

                    else:
                        logger.warning(f"Unknown message type: {message_type}")
                        await ErrorHandler.send_error(
                            websocket, f"Unknown message type: {message_type}"
                        )

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
# 메시지 핸들러
# ========================================


async def _handle_init(
    websocket: WebSocket,
    session_id: str,
    user_id: int,
    session_data: dict,
    init_msg: InitMessage,
) -> None:
    """
    INIT 메시지 처리

    1. SessionManager에 세션 생성
    2. ACK 전송
    3. 첫 AI 질문 생성 및 전송 (고정 질문[0] 사용)
    """
    try:
        # Redis의 expiresAt을 datetime으로 파싱
        expires_at_str = session_data.get("expiresAt")
        expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None

        # SessionManager에 세션 생성
        session_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            subject_id=init_msg.subjectId,
            my_role=init_msg.myRole,
            ai_role=init_msg.aiRole,
            fixed_questions=init_msg.fixedQuestions,
            expires_at=expires_at,
        )

        # STT 스트리밍 세션 생성 (Deepgram WebSocket)
        from app.roleplaying.services.stt_service import stt_service
        try:
            stt_service.create_streaming_session(session_id)
            logger.info(f"STT streaming session created: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to create STT streaming session: {e}")
            # 스트리밍 실패 시에도 배치 STT는 계속 사용 가능하므로 계속 진행

        logger.info(
            f"Session initialized: {session_id}, "
            f"role={init_msg.myRole} → {init_msg.aiRole}"
        )

        # ACK 전송
        ack = AckMessage(message="Session initialized")
        await websocket.send_json(ack.model_dump())

        # 첫 AI 질문 전송 (고정 질문[0] 사용 - 턴 1)
        first_question = init_msg.fixedQuestions[0]

        # 세션 히스토리에 추가
        session_manager.append_message(
            session_id=session_id,
            speaker="ai",
            text=first_question,
            is_fixed_question=True,
        )

        first_ai_index = session_manager.increment_utterance_index(session_id)
        _schedule_spring2_save(
            session_id=session_id,
            text=first_question,
            utterance_index=first_ai_index,
            speaker="AI",
        )

        # 클라이언트에 전송
        ai_msg = AiTextMessage(text=first_question, is_fixed_question=True)
        await websocket.send_json(ai_msg.model_dump())

        logger.info(f"First question sent: {first_question[:50]}...")

    except ValueError as e:
        logger.error(f"Session creation failed: {e}")
        await _send_error(websocket, str(e))
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))

    except Exception as e:
        logger.error(f"INIT handler error: {e}", exc_info=True)
        await _send_error(websocket, "Session initialization failed")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


async def _handle_audio_chunk(
    websocket: WebSocket, session_id: str, chunk: bytes
) -> None:
    """
    오디오 청크 처리

    1. SessionManager에 오디오 청크 추가
    2. STT 스트리밍 처리 (향후 구현)
    3. 부분 결과 전송 (향후 구현)

    Note:
        현재는 버퍼에만 추가. STT 스트리밍은 services/stt_service.py에서 구현 예정.
    """
    try:
        # 세션 검증
        session_state = session_manager.get_session(session_id)
        if not session_state:
            await _send_error(websocket, "Session not found")
            return

        # 세션 만료 확인
        if session_state.is_expired():
            await _send_error(websocket, "Session expired")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Session expired"
            )
            return

        # 오디오 버퍼에 추가
        session_manager.append_audio_chunk(session_id, chunk)

        # STT 스트리밍 처리 (Deepgram WebSocket)
        from app.roleplaying.services.stt_service import stt_service
        try:
            partial_text = await stt_service.process_chunk(session_id, chunk)
            if partial_text:
                await websocket.send_json(SttPartialMessage(text=partial_text).model_dump())
                logger.debug(f"STT partial sent: {partial_text}")
        except Exception as e:
            logger.warning(f"Streaming STT error (non-fatal): {e}")

    except Exception as e:
        logger.error(f"Audio chunk handler error: {e}", exc_info=True)
        await _send_error(websocket, "Audio processing failed")


async def _handle_user_text(
    websocket: WebSocket, session_id: str, user_text: str
) -> None:
    """
    사용자 텍스트 메시지 처리 (테스트용 - STT 없이)

    1. 세션 히스토리에 사용자 발화 추가 (텍스트로)
    2. Spring 2에 텍스트 저장 (비동기, 오디오 없이)
    3. AI 응답 생성
    4. AI 응답 전송

    Note:
        오디오 처리 및 STT를 건너뛰고 바로 AI 응답 생성으로 이동.
        텍스트는 DB에 저장되어 대화 히스토리를 기록.
    """
    try:
        # 세션 조회
        session_state = session_manager.get_session(session_id)
        if not session_state:
            await _send_error(websocket, "Session not found")
            return

        # 세션 만료 확인
        if session_state.is_expired():
            await _send_error(websocket, "Session expired")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Session expired"
            )
            return

        logger.info(
            f"Processing text message: session={session_id}, text='{user_text[:50]}...'"
        )

        # ========================================
        # Step 1: 세션 히스토리에 사용자 발화 추가
        # ========================================
        session_manager.append_message(
            session_id=session_id,
            speaker="user",
            text=user_text,
            audio_s3_url=None,  # 텍스트 모드에서는 오디오 없음
        )

        # ========================================
        # Step 2: Spring 2에 텍스트 저장 (비동기)
        # ========================================
        utterance_index = session_manager.increment_utterance_index(session_id)

        _schedule_spring2_save(
            session_id=session_id,
            text=user_text,
            utterance_index=utterance_index,
            speaker="USER",
        )

        # 클라이언트에 저장 완료 알림 (실제로는 비동기 진행 중)
        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )

        # 턴 제한 확인 (사용자 답변 후, AI 응답 생성 전)
        # AI가 이미 10번 질문했고, 사용자가 10번 답변했으면 세션 종료
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # ========================================
        # Step 3: AI 응답 생성 (스트리밍)
        # ========================================
        await websocket.send_json(AiTypingMessage().model_dump())

        # AI 튜터 서비스를 사용하여 동적 응답 생성 (스트리밍)
        from app.roleplaying.services.ai_tutor_service import ai_tutor_service
        from app.roleplaying.ws_models import AiTextStreamingMessage

        full_ai_response = ""
        is_fixed_question = False

        try:
            async for chunk, is_fixed in ai_tutor_service.generate_reply_stream(
                session_state, user_text
            ):
                full_ai_response += chunk
                is_fixed_question = is_fixed

                # ✅ 청크를 즉시 클라이언트에 전송
                await websocket.send_json(
                    AiTextStreamingMessage(chunk=chunk, is_fixed_question=is_fixed).model_dump()
                )
                logger.debug(f"AI streaming chunk sent: {chunk[:30]}...")

        except Exception as e:
            logger.error(f"Error during AI streaming: {e}", exc_info=True)
            # Fallback: 기본 응답 전송
            full_ai_response = "Could you tell me more about that?"
            is_fixed_question = False
            await websocket.send_json(
                AiTextStreamingMessage(chunk=full_ai_response, is_fixed_question=False).model_dump()
            )

        # 세션 히스토리에 완전한 AI 응답 추가
        session_manager.append_message(
            session_id=session_id,
            speaker="ai",
            text=full_ai_response,
            is_fixed_question=is_fixed_question,
        )

        ai_index = session_manager.increment_utterance_index(session_id)
        _schedule_spring2_save(
            session_id=session_id,
            text=full_ai_response,
            utterance_index=ai_index,
            speaker="AI",
            played_turns=session_state.ai_turn_count,
            completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS),
            finish_reason=None,
            status="IN_PROGRESS",
        )

        logger.info(f"AI response completed: {full_ai_response[:50]}... (fixed={is_fixed_question})")

        # 턴 제한 확인 후 종료 처리
        if await _check_turn_limit(websocket, session_id, session_state):
            return

    except Exception as e:
        logger.error(f"User text handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process text message")


async def _handle_utterance_end(websocket: WebSocket, session_id: str) -> None:
    """
    발화 종료 처리 (비동기 병렬 처리)

    1. STT 처리 시작 (백그라운드)
    2. STT 결과 대기 & 수신 즉시 전송
    3. AI 응답 생성 (STT와 병렬)
    4. 세션 히스토리, Spring 2 저장 (비동기 백그라운드)
    """
    try:
        # 세션 조회
        session_state = session_manager.get_session(session_id)
        if not session_state:
            await _send_error(websocket, "Session not found")
            return

        # 오디오 데이터 가져오기
        audio_data = session_manager.get_current_audio(session_id)

        if not audio_data:
            await _send_error(websocket, "No audio data received")
            return

        logger.info(
            f"Processing utterance: session={session_id}, audio_size={len(audio_data)} bytes"
        )

        # ========================================
        # Step 1: STT 처리 시작 (백그라운드 태스크)
        # ========================================
        from app.roleplaying.services.stt_service import stt_service
        from app.roleplaying.services.ai_tutor_service import ai_tutor_service

        async def process_stt_and_history(audio_data: bytes) -> Optional[str]:
            """STT 처리 및 히스토리 추가"""
            try:
                stt_text = await stt_service.transcribe(audio_data)

                # Silence 감지
                if not stt_text or stt_text.strip() == "":
                    logger.warning(f"Silence detected: {len(audio_data)} bytes of audio but no speech")
                    return None

                # 세션 히스토리에 사용자 발화 추가
                session_manager.append_message(
                    session_id=session_id,
                    speaker="user",
                    text=stt_text,
                    audio_s3_url=None,
                )

                logger.info(f"STT completed: {stt_text}")
                return stt_text
            except Exception as e:
                logger.error(f"STT processing error: {e}", exc_info=True)
                return None

        # STT 처리 시작 (비동기)
        stt_task = asyncio.create_task(process_stt_and_history(audio_data))

        # ========================================
        # Step 2: STT 결과 대기 & 클라이언트에 전송
        # ========================================
        stt_text = await stt_task

        if not stt_text:
            # Silence 감지 시 에러 전송
            await websocket.send_json(SttFinalMessage(text="").model_dump())
            await ErrorHandler.send_error(
                websocket,
                "Silence detected. Please speak again.",
                code="SILENCE_DETECTED",
                severity=ErrorHandler.SEVERITY_INFO
            )
            session_manager.clear_audio_buffer(session_id)
            logger.info(f"Silence detected for session {session_id}, waiting for next utterance")
            return

        # STT 최종 결과 전송
        await websocket.send_json(SttFinalMessage(text=stt_text).model_dump())

        # ========================================
        # Step 3: AI 응답 생성 (동시 진행 가능)
        # ========================================
        utterance_index = session_manager.increment_utterance_index(session_id)

        # Spring 2 저장을 백그라운드에서 시작
        from app.integrations.clients.spring2_client import spring2_client

        async def _save_user_utterance():
            try:
                await spring2_client.save_utterance(
                    session_id=session_id,
                    audio_data=audio_data,
                    stt_text=stt_text,
                    utterance_index=utterance_index,
                    speaker="user",
                    text=stt_text,
                    played_turns=session_state.ai_turn_count,
                    completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS),
                    finish_reason=None,
                    status="IN_PROGRESS",
                )
            except Exception as e:
                logger.error(
                    f"Failed to save user utterance: session={session_id}, index={utterance_index}, error={e}",
                    exc_info=True
                )

        # ✅ 태스크 생성 후 에러 콜백 추가
        task = asyncio.create_task(_save_user_utterance())
        context = f"spring2_save_utterance(session={session_id}, speaker=user, index={utterance_index})"
        task.add_done_callback(lambda t: _handle_task_error(t, context))

        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )
        logger.info(f"Utterance save requested to Spring 2: index={utterance_index}")

        # 턴 제한 확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # AI 응답 생성 (스트리밍)
        await websocket.send_json(AiTypingMessage().model_dump())

        # 스트리밍으로 응답 생성
        full_ai_response = ""
        is_fixed_question = False

        try:
            async for chunk, is_fixed in ai_tutor_service.generate_reply_stream(
                session_state, stt_text
            ):
                full_ai_response += chunk
                is_fixed_question = is_fixed

                # ✅ 청크를 즉시 클라이언트에 전송
                from app.roleplaying.ws_models import AiTextStreamingMessage
                await websocket.send_json(
                    AiTextStreamingMessage(chunk=chunk, is_fixed_question=is_fixed).model_dump()
                )
                logger.debug(f"AI streaming chunk sent: {chunk[:30]}...")

        except Exception as e:
            logger.error(f"Error during AI streaming: {e}", exc_info=True)
            # Fallback: 기본 응답 전송
            full_ai_response = "Could you tell me more about that?"
            is_fixed_question = False
            await websocket.send_json(
                AiTextStreamingMessage(chunk=full_ai_response, is_fixed_question=False).model_dump()
            )

        # 세션 히스토리에 완전한 AI 응답 추가
        session_manager.append_message(
            session_id=session_id,
            speaker="ai",
            text=full_ai_response,
            is_fixed_question=is_fixed_question,
        )

        # AI 응답 저장 (Spring 2 - 백그라운드)
        ai_index = session_manager.increment_utterance_index(session_id)
        _schedule_spring2_save(
            session_id=session_id,
            text=full_ai_response,
            utterance_index=ai_index,
            speaker="AI",
            played_turns=session_state.ai_turn_count,
            completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS),
            finish_reason=None,
            status="IN_PROGRESS",
        )

        logger.info(f"AI response completed: {full_ai_response[:50]}... (fixed={is_fixed_question})")

        # 턴 제한 확인 후 종료 처리
        if await _check_turn_limit(websocket, session_id, session_state):
            return

    except Exception as e:
        logger.error(f"Utterance end handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process utterance")


async def _check_turn_limit(
    websocket: WebSocket, session_id: str, session_state: SessionState
) -> bool:
    """
    턴 제한(10 AI↔사용자 페어) 초과 여부를 확인하고 초과 시 세션 종료

    Returns:
        True if 세션을 종료했으면 True, 계속 진행해도 되면 False
    """
    try:
        if session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS):
            logger.info(f"Turn limit reached for session {session_id}, ending session.")
            await _handle_end_session(websocket, session_id, "turn_limit")
            return True
        logger.debug(
            "Turn limit not reached yet: session=%s, ai_turns=%s, user_turns=%s, utterance_index=%s",
            session_id,
            session_state.ai_turn_count,
            session_state.user_turn_count,
            session_state.utterance_index,
        )
        return False
    except Exception as exc:
        logger.error(f"Turn limit check failed: {exc}", exc_info=True)
        return False


async def _handle_end_session(
    websocket: WebSocket, session_id: str, reason: str
) -> None:
    """
    세션 종료 처리

    1. SessionManager.end_session()
    2. Spring 2에 세션 완료 알림
    3. SESSION_ENDED 메시지 전송
    4. WebSocket 연결 종료
    """
    try:
        logger.info(f"Ending session: {session_id}, reason={reason}")

        # SessionManager에서 세션 종료
        session_state = session_manager.get_session(session_id)
        session_manager.end_session(session_id, reason)

        # Spring 2에 세션 완료 알림
        from app.integrations.clients.spring2_client import spring2_client

        try:
            await spring2_client.complete_session(
                session_id=session_id,
                status="FINISHED" if reason != "error" else "ERROR",
                reason=reason,
                played_turns=session_state.ai_turn_count if session_state else None,
                completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
                finish_reason=reason,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Failed to notify Spring 2 of session completion: {e}")
            # 에러가 나도 세션 종료는 계속 진행

        # SESSION_ENDED 메시지 전송
        await websocket.send_json(SessionEndedMessage(reason=reason).model_dump())

        # WebSocket 연결 종료
        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason=reason)

        # 메모리 정리
        session_manager.cleanup(session_id)
        logger.info(f"Session ended and cleaned up: {session_id}")

    except Exception as e:
        logger.error(f"End session handler error: {e}", exc_info=True)


# ========================================
# 유틸리티 함수
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
            import json

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


def _schedule_spring2_save(
    session_id: str,
    text: str,
    utterance_index: int,
    speaker: str,
    played_turns: Optional[int] = None,
    completed_all_turns: bool = False,
    finish_reason: Optional[str] = None,
    status: str = "IN_PROGRESS",
) -> None:
    """Spring 2 저장을 비동기로 수행하도록 스케줄합니다."""

    async def _save():
        try:
            from app.integrations.clients.spring2_client import spring2_client

            normalized_speaker = (speaker or "user").lower()

            await spring2_client.save_utterance(
                session_id=session_id,
                stt_text=text,
                utterance_index=utterance_index,
                speaker=normalized_speaker,
                text=text,
                audio_data=None,
                played_turns=played_turns,
                completed_all_turns=completed_all_turns,
                finish_reason=finish_reason,
                status=status,
            )
            logger.info(
                f"Text saved to Spring 2: session={session_id}, index={utterance_index}, speaker={normalized_speaker}"
            )
        except Exception as exc:
            logger.error(f"Failed to save text to Spring 2: {exc}", exc_info=True)

    # ✅ 태스크 생성 후 에러 콜백 추가
    task = asyncio.create_task(_save())
    context = f"spring2_save(session={session_id}, speaker={speaker}, index={utterance_index})"
    task.add_done_callback(lambda t: _handle_task_error(t, context))


async def _send_error(
    websocket: WebSocket, message: str, code: Optional[str] = None
) -> None:
    """에러 메시지 전송"""
    try:
        error_msg = ErrorMessage(message=message, code=code)
        await websocket.send_json(error_msg.model_dump())
        logger.error(f"Error sent to client: {message}")
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


async def _cleanup_session(session_id: str, reason: str) -> None:
    """세션 정리 (연결 끊김 또는 에러 시)"""
    try:
        # STT 스트리밍 세션 정리
        from app.roleplaying.services.stt_service import stt_service
        try:
            await stt_service.finalize_streaming(session_id)
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


