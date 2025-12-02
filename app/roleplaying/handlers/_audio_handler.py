"""
발화 종료 메시지 핸들러
=======================

UTTERANCE_END 메시지 처리 (오디오 기반)

흐름:
1. STT 처리 (오디오 → 텍스트)
2. 피드백 평가 (Option 1: 실패 시 None)
3. Spring 2에 발화 저장 (feedback 조건부)
4. AI 응답 생성
5. 턴 제한 확인
"""

import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

from app.config import settings
from app.roleplaying.core.session_state_manager import session_manager
from app.roleplaying.handlers._common import (
    _send_error,
    _check_turn_limit,
    _evaluate_feedback,
    _send_feedback_messages,
    _generate_and_stream_ai_response,
    _save_utterance_with_feedback,
    _handle_task_error,
    _schedule_spring2_save,
)
from app.roleplaying.handlers.session_validators import ErrorHandler
from app.roleplaying.handlers.ws_message_models import (
    AiTypingMessage,
    SttFinalMessage,
    UtteranceSavedMessage,
)

logger = logging.getLogger(__name__)


async def handle_utterance_end(router, websocket: WebSocket, session_id: str, message: dict) -> None:
    """
    발화 종료 처리

    1. STT 처리
    2. STT 결과 전송
    3. AI 응답 생성
    4. 피드백 계산
    """
    try:
        session_state = session_manager.get_session(session_id)
        if not session_state:
            await _send_error(websocket, "Session not found")
            return

        audio_data = session_manager.get_current_audio(session_id)
        if not audio_data:
            await _send_error(websocket, "No audio data received")
            return

        logger.info(f"Processing utterance: session={session_id}, audio_size={len(audio_data)} bytes")

        # Step 1: STT 처리
        from app.roleplaying.services.stt.speech_to_text_service import stt_service

        async def process_stt_and_history(audio_data: bytes) -> Optional[str]:
            """STT 처리 및 히스토리 추가"""
            try:
                stt_text = await stt_service.transcribe(audio_data)
                if not stt_text or stt_text.strip() == "":
                    logger.warning(f"Silence detected: {len(audio_data)} bytes of audio but no speech")
                    return None

                await session_manager.append_message_async(
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

        stt_task = asyncio.create_task(process_stt_and_history(audio_data))
        stt_text = await stt_task

        if not stt_text:
            await websocket.send_json(SttFinalMessage(text="").model_dump())
            await ErrorHandler.send_error(
                websocket,
                "Silence detected. Please speak again.",
                code="SILENCE_DETECTED",
            )
            session_manager.clear_audio_buffer(session_id)
            return

        await websocket.send_json(SttFinalMessage(text=stt_text).model_dump())

        # Step 2: 피드백 평가 (Azure 사용 가능 여부 확인)
        from app.roleplaying.services.dependencies import get_feedback_orchestrator
        from app.roleplaying.services.utils.azure_usage_tracker import usage_tracker

        feedback_orchestrator = get_feedback_orchestrator()

        can_use_azure = await usage_tracker.can_use_azure()
        logger.info(f"⏱️  [Azure 사용 가능] session={session_id}, can_use_azure={can_use_azure}")

        feedback_result = await _evaluate_feedback(
            feedback_orchestrator=feedback_orchestrator,
            websocket=websocket,
            session_id=session_id,
            user_text=stt_text,
            audio_data=audio_data if can_use_azure else None,
            session_state=session_state,
            can_use_azure=can_use_azure,
        )

        # Azure 사용 시 usage 증가
        if can_use_azure and feedback_result:
            try:
                await usage_tracker.increment_usage()
            except Exception as e:
                logger.warning(f"Failed to increment Azure usage: {e}")

        # ✅ 피드백 메시지 전송 및 재시도 확인
        if await _send_feedback_messages(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            feedback_result=feedback_result,
        ):
            # 재시도 필요 - early return
            return

        # Step 3: Spring 2에 사용자 발화 저장
        utterance_index = session_manager.increment_utterance_index(session_id)

        async def _save_user_utterance():
            await _save_utterance_with_feedback(
                session_id=session_id,
                speaker="user",
                text=stt_text,
                stt_text=stt_text,
                utterance_index=utterance_index,
                audio_data=audio_data,
                session_state=session_state,
                feedback_result=feedback_result,
            )

        task = asyncio.create_task(_save_user_utterance())
        task.add_done_callback(lambda t: _handle_task_error(t, f"save_utterance(session={session_id})"))

        await websocket.send_json(UtteranceSavedMessage(index=utterance_index).model_dump())

        # 턴 제한 확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # Step 4: AI 응답 생성
        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=stt_text,
        )

        ai_index = await session_manager.increment_utterance_index_async(session_id)
        await _schedule_spring2_save(
            session_id=session_id,
            text=full_ai_response,
            utterance_index=ai_index,
            speaker="AI",
            played_turns=session_state.ai_turn_count if session_state else None,
            completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
            status="IN_PROGRESS",
        )

        logger.info(f"AI response completed: {full_ai_response[:50]}...")

        # 턴 제한 재확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

    except Exception as e:
        logger.error(f"Utterance end handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process utterance")
