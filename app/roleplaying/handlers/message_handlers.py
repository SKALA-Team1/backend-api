"""
WebSocket 메시지 핸들러들
=========================

각 메시지 타입별 비즈니스 로직을 처리합니다.
MessageRouter의 핸들러로 사용됩니다.

handler 시그니처:
  async def handler(router, websocket, session_id, message):

구조:
- message_handlers.py (이 파일): INIT, END_SESSION 핸들러
- _text_handler.py: USER_TEXT 핸들러
- _audio_handler.py: UTTERANCE_END 핸들러
- _common.py: 공통 유틸리티 및 공유 로직
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket, status

from app.config import settings
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.core.session_state_manager import session_manager, SessionMessageHandler
from app.roleplaying.handlers._common import _send_error, _handle_task_error, _save_question_with_keywords
from app.roleplaying.handlers._text_handler import handle_user_text
from app.roleplaying.handlers._audio_handler import handle_utterance_end
from app.roleplaying.handlers.ws_message_models import (
    AckMessage, AiTextMessage, InitMessage, SessionEndedMessage,
)

logger = logging.getLogger(__name__)


# ========================================
# INIT 메시지 핸들러
# ========================================


async def handle_init(router, websocket: WebSocket, session_id: str, message: dict) -> None:
    """
    INIT 메시지 처리

    1. SessionManager에 세션 생성
    2. ACK 전송
    3. 첫 AI 질문 생성 및 전송 (고정 질문[0] 사용)
    """
    try:
        # websocket.scope에서 세션 데이터 가져오기
        session_data = websocket.scope.get("session_data")
        user_id = websocket.scope.get("user_id")

        if not session_data or not user_id:
            await _send_error(websocket, "Invalid session initialization")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        init_msg = InitMessage(**message)

        # Redis의 expiresAt을 datetime으로 파싱
        expires_at_str = session_data.get("expiresAt")
        expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None

        # Redis에서 voiceId 가져오기
        voice_id = session_data.get("voiceId")

        # SessionManager에 세션 생성
        session_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            subject_id=init_msg.subjectId,
            my_role=init_msg.myRole,
            ai_role=init_msg.aiRole,
            fixed_questions=init_msg.fixedQuestions,
            expires_at=expires_at,
            interaction_mode=init_msg.interactionMode,  # Pass interaction mode
            voice_id=voice_id  # Pass voice ID
        )

        # ACK 전송
        ack = AckMessage(message="Session initialized")
        await websocket.send_json(ack.model_dump())

        # 첫 AI 질문 전송 (고정 질문[0] 사용 - 턴 1)
        first_question = init_msg.fixedQuestions[0]

        # 세션에 현재 질문 저장
        session_state = session_manager.get_session(session_id)
        if session_state:
            session_state.current_question_text = first_question

        # 세션 히스토리에 추가
        await SessionMessageHandler.append_message_async(
            session_id=session_id,
            speaker="ai",
            text=first_question,
            is_fixed_question=True,
        )

        first_ai_index = await SessionMessageHandler.increment_utterance_index_async(session_id)

        # ========================================
        # 병렬 처리: 한글 번역 + TTS 생성 + 키워드 생성
        # ========================================
        # 한글 번역과 TTS는 독립적이므로 동시 실행
        import asyncio
        from app.roleplaying.handlers._common import (
            _save_question_with_keywords,
            _translate_question_to_korean,
            _send_tts_audio_and_visemes,
            _generate_recommended_keywords_task
        )

        translate_task = asyncio.create_task(_translate_question_to_korean(first_question))
        tts_task = asyncio.create_task(
            _send_tts_audio_and_visemes(websocket, first_question, context="INIT", session_id=session_id)
        )
        keywords_task = asyncio.create_task(
             _generate_recommended_keywords_task(first_question, session_state)
        )

        # 병렬 실행
        results = await asyncio.gather(translate_task, tts_task, keywords_task, return_exceptions=True)

        first_question_ko = results[0] if not isinstance(results[0], Exception) else first_question
        tts_error = results[1] if isinstance(results[1], Exception) else None
        keywords = results[2] if not isinstance(results[2], Exception) else []

        if tts_error:
            logger.warning(f"TTS error during init: {tts_error}")

        # 클라이언트에 전송 (영문 + 한글 + 키워드) - 먼저 전송
        ai_msg = AiTextMessage(
            text=first_question, 
            text_ko=first_question_ko, 
            is_fixed_question=True,
            recommended_keywords=keywords
        )
        await websocket.send_json(ai_msg.model_dump())

        # ✅ Background task: Spring 2 저장 (응답 후 비동기 처리)
        async def save_first_question_background():
            try:
                await _save_question_with_keywords(
                    session_id=session_id,
                    question_en=first_question,
                    turn_number=1,
                    utterance_index=first_ai_index,
                    user_role=init_msg.myRole,
                    ai_role=init_msg.aiRole,
                    scenario_context=init_msg.subjectId,
                    session_state=session_state,
                    slack_message=None,
                    is_fixed_question=True,  # ✅ 고정 질문임을 명시
                    question_ko=first_question_ko,  # ✅ 이미 생성된 번역을 재사용 (중복 생성 방지)
                    keywords=keywords # ✅ 이미 생성된 키워드 재사용
                )
            except Exception as e:
                logger.error(f"Background task - Failed to save first fixed question: {e}", exc_info=True)

        # 백그라운드 태스크로 실행 (응답을 기다리지 않음)
        save_task = asyncio.create_task(save_first_question_background())
        save_task.add_done_callback(lambda task: _handle_task_error(task, "save_first_question_background"))

    except ValueError as e:
        logger.error(f"Session creation failed: {e}")
        await _send_error(websocket, str(e))
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e))
    except Exception as e:
        logger.error(f"INIT handler error: {e}", exc_info=True)
        await _send_error(websocket, "Session initialization failed")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# ========================================
# END_SESSION 메시지 핸들러
# ========================================


async def handle_end_session(router, websocket: WebSocket, session_id: str, message: dict) -> None:
    """
    세션 종료 처리

    1. SessionManager.end_session()
    2. Spring 2에 세션 완료 알림
    3. SESSION_ENDED 메시지 전송
    """
    try:
        reason = message.get("reason", "user_end") if isinstance(message, dict) else "user_end"

        session_state = session_manager.get_session(session_id)
        session_manager.end_session(session_id, reason)

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

        await websocket.send_json(SessionEndedMessage(reason=reason).model_dump())
        await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason=reason)

        session_manager.cleanup(session_id)

    except Exception as e:
        logger.error(f"End session handler error: {e}", exc_info=True)


# ========================================
# Export all handlers
# ========================================

__all__ = [
    'handle_init',
    'handle_user_text',
    'handle_utterance_end',
    'handle_end_session',
]
