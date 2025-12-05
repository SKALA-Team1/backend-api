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

        # 🔑 마지막 턴 확인 (Turn 7 = 마지막 질문)
        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        is_last_turn = next_ai_turn > 7
        logger.info(f"🔑 [턴 정보] next_ai_turn={next_ai_turn}, is_last_turn={is_last_turn}")

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
            # 🔑 마지막 턴은 항상 피드백 제공 (다음 질문이 없으므로)
            if is_last_turn:
                logger.info(
                    f"🔑 [마지막 턴 피드백 강제] Agent said NEXT_QUESTION but this is turn 7 (last), "
                    f"forcing feedback evaluation"
                )
                feedback_result = await _evaluate_feedback(
                    feedback_orchestrator=feedback_orchestrator,
                    websocket=websocket,
                    session_id=session_id,
                    user_text=user_text,
                    audio_data=None,  # Text mode - no audio
                    session_state=session_state,
                    can_use_azure=False,  # Text mode - no Azure pronunciation
                )
            else:
                # Agent가 다음 질문 결정 (일반 턴)
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

        # Step 3: 🔑 항상 먼저 index를 증가 (Retry든 Success든 상관없이)
        logger.info(f"🔼 Before increment: session={session_id}")
        utterance_index = await SessionMessageHandler.increment_utterance_index_async(session_id)
        logger.info(f"🔼 After increment: session={session_id}, index={utterance_index}")

        # ✅ Step 4a: 피드백 메시지 전송 및 재시도 확인 (feedback_sections 생성 먼저!)
        needs_retry = await _send_feedback_messages(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            feedback_result=feedback_result,
        )

        # ✅ Step 4b: 사용자 메시지 DB에 저장 (피드백 섹션이 생성된 후)
        try:
            result = await _save_utterance_with_feedback(
                session_id=session_id,
                speaker="user",
                text=user_text,
                stt_text=user_text,
                utterance_index=utterance_index,
                audio_data=None,
                session_state=session_state,
                feedback_result=feedback_result,
            )
            logger.info(f"✅ User text saved to Spring2: session={session_id}, index={utterance_index}")
        except Exception as e:
            logger.error(f"❌ Failed to save user text: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save user text", code="DB_SAVE_ERROR").model_dump()
            )

        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )

        # Step 6: Retry일 때는 조기 종료 (AI 응답 생성 안 함)
        if needs_retry:
            logger.info(f"Retry required for session={session_id}, exiting without generating AI response")
            return

        # Step 7: 🔑 다음 AI 질문이 8번째가 될 것인지 미리 확인 (생성 전)
        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        if next_ai_turn > 7:
            logger.info(f"Turn limit reached: next_ai_turn={next_ai_turn}, ending session")
            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            await websocket.send_json(SessionEndedMessage(reason="turn_limit").model_dump())
            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
            return

        # Step 8: AI 응답 생성 (정상 응답일 때만)
        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=user_text,
        )

        # Step 8: AI 질문 저장
        ai_index = await SessionMessageHandler.increment_utterance_index_async(session_id)
        turn_number = session_state.get_ai_turn_number() if session_state else 1

        # AI 질문 저장 (즉시 동기 실행 + 에러 처리)
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
            )
            logger.info(f"✅ AI question saved: session={session_id}, index={ai_index}, turn={turn_number}")
        except Exception as e:
            logger.error(f"❌ Failed to save AI question: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save AI question", code="AI_SAVE_ERROR").model_dump()
            )

        logger.info(f"AI response completed: {full_ai_response[:50]}...")

    except Exception as e:
        logger.error(f"User text handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process text message")
