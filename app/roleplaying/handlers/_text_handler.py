"""
사용자 텍스트 메시지 핸들러
==========================

USER_TEXT 메시지 처리 (테스트용 - STT 없이)

흐름:
1. 세션 히스토리에 사용자 발화 추가
2. 피드백 평가 (Option 1: 실패 시 None)
3. Spring 2에 텍스트 저장 (feedback 조건부)
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
from app.roleplaying.handlers.ws_message_models import (
    AiTypingMessage,
    ErrorMessage,
    UtteranceSavedMessage,
    UserTextMessage,
)

logger = logging.getLogger(__name__)


async def handle_user_text(router, websocket: WebSocket, session_id: str, message: dict) -> None:
    """
    사용자 텍스트 메시지 처리 (테스트용 - STT 없이)

    1. 세션 히스토리에 사용자 발화 추가
    2. Spring 2에 텍스트 저장
    3. AI 응답 생성
    4. 피드백 계산
    """
    try:
        # 메시지 파싱
        user_text_msg = UserTextMessage(**message)
        user_text = user_text_msg.text

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

        # 세션 히스토리에 사용자 발화 추가
        await SessionMessageHandler.append_message_async(
            session_id=session_id,
            speaker="user",
            text=user_text,
            audio_s3_url=None,
        )

        from app.roleplaying.services.dependencies import (
            get_feedback_orchestrator,
            get_feedback_decision_agent,
        )

        feedback_orchestrator = get_feedback_orchestrator()
        feedback_decision_agent = get_feedback_decision_agent()

        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        is_last_turn = next_ai_turn > 7

        # Step 1: 평가 수행 (1회만)
        evaluation_result = await _evaluate_feedback(
            feedback_orchestrator=feedback_orchestrator,
            websocket=websocket,
            session_id=session_id,
            user_text=user_text,
            audio_data=None,
            session_state=session_state,
            can_use_azure=False,
        )

        # Step 2: Agent는 평가 결과를 받아 판단만 수행 (재평가 없음)
        agent_decision = None
        if evaluation_result:
            agent_decision = await feedback_decision_agent.decide_based_on_evaluation(
                evaluation_result=evaluation_result,
                session_state=session_state,
                retry_count=session_state.current_question_retry_count if session_state else 0,
                can_use_azure=False,
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

            if not show_feedback and isinstance(feedback_result, dict):
                feedback_result['feedback_sections'] = []

            if isinstance(feedback_result, dict):
                needs_correction = feedback_result.get("needs_correction", False)
                retry_count = session_state.current_question_retry_count if (session_state and needs_correction) else 0
                feedback_result['needs_correction'] = needs_correction
                feedback_result['retry_count'] = retry_count

        utterance_index = await SessionMessageHandler.increment_utterance_index_async(session_id)

        needs_retry = await _send_feedback_messages(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            feedback_result=feedback_result,
            show_feedback=show_feedback,
        )

        try:
            await _save_utterance_with_feedback(
                session_id=session_id,
                speaker="user",
                text=user_text,
                stt_text=user_text,
                utterance_index=utterance_index,
                audio_data=None,
                session_state=session_state,
                feedback_result=feedback_result,
            )
        except Exception as e:
            logger.error(f"Failed to save user text: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save user text", code="DB_SAVE_ERROR").model_dump()
            )

        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )

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
                    completed_all_turns=True,
                    finish_reason="turn_limit",
                    finished_at=None,
                )
            except Exception as e:
                logger.error(f"Failed to notify Spring 2 of session completion: {e}", exc_info=True)

            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            await websocket.send_json(SessionEndedMessage(reason="turn_limit").model_dump())
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
            session_manager.cleanup(session_id)
            return

        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=user_text,
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
                slack_message=None,
                is_fixed_question=is_fixed_question,
            )
        except Exception as e:
            logger.error(f"Failed to save AI question: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save AI question", code="AI_SAVE_ERROR").model_dump()
            )

    except Exception as e:
        logger.error(f"User text handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process text message")
