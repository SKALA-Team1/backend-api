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
    _evaluate_feedback_with_agent,
    _send_feedback_messages,
    _generate_and_stream_ai_response,
    _save_utterance_with_feedback,
    _handle_task_error,
    _schedule_spring2_save,
)
from app.roleplaying.handlers.ws_message_models import (
    AiTypingMessage,
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

        logger.info(
            f"Processing text message: session={session_id}, text='{user_text[:50]}...'"
        )

        # Step 1: 세션 히스토리에 사용자 발화 추가
        await SessionMessageHandler.append_message_async(
            session_id=session_id,
            speaker="user",
            text=user_text,
            audio_s3_url=None,
        )

        # Step 2: 피드백 평가 (ReAct Agent 우선, Fallback 지원)
        from app.roleplaying.services.dependencies import (
            get_feedback_orchestrator,
            get_feedback_decision_agent,
        )

        feedback_orchestrator = get_feedback_orchestrator()
        feedback_decision_agent = get_feedback_decision_agent()

        # ========================================
        # Step 2a: ReAct Agent를 통한 피드백 판단
        # ========================================
        agent_decision = await _evaluate_feedback_with_agent(
            agent=feedback_decision_agent,
            session_id=session_id,
            user_text=user_text,
            audio_data=None,  # Text mode - no audio
            session_state=session_state,
            can_use_azure=False,  # Text mode - no Azure pronunciation
        )

        if agent_decision and agent_decision.get("action") == "FEEDBACK":
            # Agent가 피드백 결정
            feedback_result = agent_decision.get("feedback_result")
            logger.info(
                f"🤖 [Agent Decision] FEEDBACK - reasoning: {agent_decision.get('reasoning')}"
            )
        elif agent_decision and agent_decision.get("action") == "NEXT_QUESTION":
            # Agent가 다음 질문 결정
            feedback_result = None
            logger.info(
                f"🤖 [Agent Decision] NEXT_QUESTION - reasoning: {agent_decision.get('reasoning')}"
            )
        else:
            # Agent 실패 시 Fallback: 기존 평가 로직 사용
            logger.info("⏮️  [Fallback] Using traditional feedback evaluation")
            feedback_result = await _evaluate_feedback(
                feedback_orchestrator=feedback_orchestrator,
                websocket=websocket,
                session_id=session_id,
                user_text=user_text,
                audio_data=None,  # Text mode - no audio
                session_state=session_state,
                can_use_azure=False,  # Text mode - no Azure pronunciation
            )

        # ✅ 피드백 메시지 전송 및 재시도 확인
        if await _send_feedback_messages(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            feedback_result=feedback_result,
        ):
            # 재시도 필요 - early return
            return

        # Step 3: Spring 2에 텍스트 저장
        utterance_index = await SessionMessageHandler.increment_utterance_index_async(session_id)

        async def _save_user_text():
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

        task = asyncio.create_task(_save_user_text())
        task.add_done_callback(lambda t: _handle_task_error(t, f"save_user_text(session={session_id})"))

        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )

        # 턴 제한 확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # Step 4: AI 응답 생성
        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=user_text,
        )

        ai_index = await SessionMessageHandler.increment_utterance_index_async(session_id)
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
        logger.error(f"User text handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process text message")
