"""
발화 종료 메시지 핸들러
=======================

UTTERANCE_END 메시지 처리 (오디오 기반)

흐름:
1. STT 처리 (오디오 → 텍스트)
2. 피드백 평가 (실패 시 None 반환)
3. Spring 2에 발화 저장 (feedback 조건부)
4. AI 응답 생성
5. 턴 제한 확인
"""

import asyncio
import logging
from typing import Optional

from fastapi import WebSocket, status

from app.config import settings
from app.roleplaying.core.session_state_manager import (
    session_manager,
    SessionMessageHandler,
    SessionAudioHandler,
)
from app.roleplaying.handlers._common import (
    _send_error,
    _check_turn_limit,
    _evaluate_feedback,
    _send_feedback_messages,
    _generate_and_stream_ai_response,
    _save_utterance_with_feedback,
    _handle_task_error,
    _save_question_with_keywords,
)
from app.roleplaying.handlers.session_validators import ErrorHandler
from app.roleplaying.handlers.ws_message_models import (
    AiTypingMessage,
    ErrorMessage,
    SttFinalMessage,
    UtteranceSavedMessage,
)
from app.roleplaying.processing.user_utterance_processor import UtteranceProcessor

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

        audio_data = await SessionAudioHandler.get_current_audio_async(session_id)
        if not audio_data:
            await _send_error(websocket, "No audio data received")
            return

        stt_text = await UtteranceProcessor.process_stt(audio_data)

        # 히스토리에 추가
        if stt_text:
            try:
                await SessionMessageHandler.append_message_async(
                    session_id=session_id,
                    speaker="user",
                    text=stt_text,
                    audio_s3_url=None,
                )
            except Exception as e:
                logger.error(f"Failed to save to history: {e}", exc_info=True)

        if not stt_text:
            await websocket.send_json(SttFinalMessage(text="").model_dump())
            await ErrorHandler.send_error(
                websocket,
                "Silence detected. Please speak again.",
                code="SILENCE_DETECTED",
            )
            await SessionAudioHandler.clear_audio_buffer_async(session_id)
            return

        await websocket.send_json(SttFinalMessage(text=stt_text).model_dump())

        # Step 2: 피드백 평가 (ReAct Agent 우선, Fallback 지원)
        from app.roleplaying.services.dependencies import (
            get_feedback_orchestrator,
            get_feedback_decision_agent,
        )
        from app.roleplaying.services.utils.azure_usage_tracker import usage_tracker

        feedback_orchestrator = get_feedback_orchestrator()
        feedback_decision_agent = get_feedback_decision_agent()

        can_use_azure = await usage_tracker.can_use_azure()

        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        is_last_turn = next_ai_turn > 7

        # Step 1: 평가 수행 (1회만)
        evaluation_result = await _evaluate_feedback(
            feedback_orchestrator=feedback_orchestrator,
            websocket=websocket,
            session_id=session_id,
            user_text=stt_text,
            audio_data=audio_data if can_use_azure else None,
            session_state=session_state,
            can_use_azure=can_use_azure,
        )

        # Step 2: Agent는 평가 결과를 받아 판단만 수행 (재평가 없음)
        agent_decision = None
        if evaluation_result:
            agent_decision = await feedback_decision_agent.decide_based_on_evaluation(
                evaluation_result=evaluation_result,
                session_state=session_state,
                retry_count=session_state.current_question_retry_count if session_state else 0,
                can_use_azure=can_use_azure,
            )

        needs_correction = False
        if evaluation_result and isinstance(evaluation_result, dict):
            needs_correction = evaluation_result.get("needs_correction", False)

        if needs_correction:
            if agent_decision and agent_decision.get("action") == "FEEDBACK":
                show_feedback = True
            elif is_last_turn:
                show_feedback = True
            else:
                show_feedback = False
        else:
            show_feedback = False

        feedback_result = None
        if evaluation_result:
            feedback_result = evaluation_result.copy() if isinstance(evaluation_result, dict) else evaluation_result

            if not show_feedback:
                if isinstance(feedback_result, dict):
                    feedback_result['feedback_sections'] = []

        # Azure 사용 시 usage 증가
        if can_use_azure and feedback_result:
            try:
                await usage_tracker.increment_usage()
            except Exception as e:
                logger.warning(f"Failed to increment Azure usage: {e}")

        utterance_index = await SessionMessageHandler.increment_utterance_index_async(session_id)
        needs_retry = await _send_feedback_messages(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            feedback_result=feedback_result,
            show_feedback=show_feedback,
        )

        try:
            result = await _save_utterance_with_feedback(
                session_id=session_id,
                speaker="user",
                text=stt_text,
                stt_text=stt_text,
                utterance_index=utterance_index,
                audio_data=audio_data,
                session_state=session_state,
                feedback_result=feedback_result,
            )
        except Exception as e:
            logger.error(f"Failed to save user utterance: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save user utterance", code="DB_SAVE_ERROR").model_dump()
            )

        await websocket.send_json(UtteranceSavedMessage(index=utterance_index).model_dump())

        if needs_retry:
            return

        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        if next_ai_turn > 7:
            from app.integrations.clients.spring2_client import spring2_client
            try:
                await spring2_client.complete_session(
                    session_id=session_id,
                    status="FINISHED",
                    reason="turn_limit",
                    played_turns=session_state.ai_turn_count if session_state else 0,
                    completed_all_turns=True,  # 모든 턴 완료
                    finish_reason="turn_limit",
                    finished_at=None,  # Spring 2가 현재 시간 사용
                )
            except Exception as e:
                logger.error(f"Failed to notify Spring 2 of session completion: {e}", exc_info=True)

            # 클라이언트에 세션 종료 알림
            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            await websocket.send_json(SessionEndedMessage(reason="turn_limit").model_dump())

            # 세션 정리 및 종합 피드백 생성
            from app.roleplaying.handlers.ws_realtime_handler import _cleanup_session
            await _cleanup_session(session_id, "turn_limit")

            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
            session_manager.cleanup(session_id)
            return

        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question, full_ai_response_ko = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=stt_text,
        )

        ai_index = await SessionMessageHandler.increment_utterance_index_async(session_id)
        turn_number = session_state.get_ai_turn_number() if session_state else 1

        try:
            await _save_question_with_keywords(
                session_id=session_id,
                question_en=full_ai_response,
                turn_number=turn_number,
                utterance_index=ai_index,
                user_role=session_state.my_role if session_state else "User",
                ai_role=session_state.ai_role if session_state else "AI",
                scenario_context=session_state.subject_id if session_state else "",
                session_state=session_state,
                slack_message=None,  # TODO: slack_message를 session_state에서 가져오기
                is_fixed_question=is_fixed_question,
                question_ko=full_ai_response_ko,  # ✅ 이미 생성된 번역을 재사용 (중복 생성 방지)
            )
        except Exception as e:
            logger.error(f"Failed to save AI question: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save AI question", code="AI_SAVE_ERROR").model_dump()
            )

    except Exception as e:
        logger.error(f"Utterance end handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process utterance")
