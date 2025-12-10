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
    _evaluate_feedback_with_agent,
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

        audio_data = SessionAudioHandler.get_current_audio(session_id)
        if not audio_data:
            await _send_error(websocket, "No audio data received")
            return

        logger.info(f"Processing utterance: session={session_id}, audio_size={len(audio_data)} bytes")

        # Step 1: STT 처리
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
            SessionAudioHandler.clear_audio_buffer(session_id)
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
        logger.info(
            f"⏱️  [Azure 사용 가능] session={session_id}, can_use_azure={can_use_azure}"
        )

        # 🔑 마지막 턴 확인 (Turn 7 = 마지막 질문)
        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        is_last_turn = next_ai_turn > 7
        logger.info(f"🔑 [턴 정보] next_ai_turn={next_ai_turn}, is_last_turn={is_last_turn}")

        # ========================================
        # Step 2: 🔑 항상 평가 수행 (점수는 항상 계산)
        # ========================================
        logger.info(f"📊 [평가 수행] 항상 평가를 수행하여 점수 계산: session={session_id}")
        evaluation_result = await _evaluate_feedback(
            feedback_orchestrator=feedback_orchestrator,
            websocket=websocket,
            session_id=session_id,
            user_text=stt_text,
            audio_data=audio_data if can_use_azure else None,
            session_state=session_state,
            can_use_azure=can_use_azure,
        )

        # ========================================
        # Step 2a: Agent를 통한 피드백 섹션 표시 여부 판단
        # ========================================
        agent_decision = await _evaluate_feedback_with_agent(
            agent=feedback_decision_agent,
            session_id=session_id,
            user_text=stt_text,
            audio_data=audio_data if can_use_azure else None,
            session_state=session_state,
            can_use_azure=can_use_azure,
        )

        # 🔑 needs_correction을 기준으로 피드백 표시 여부 결정
        # needs_correction = 점수 기반 판단 (신뢰도 높음)
        # agent_decision = LLM 기반 판단 (참고용)
        needs_correction = False
        if evaluation_result and isinstance(evaluation_result, dict):
            needs_correction = evaluation_result.get("needs_correction", False)

        logger.info(f"📊 [피드백 표시 결정] needs_correction={needs_correction}, is_last_turn={is_last_turn}")

        if needs_correction:
            # needs_correction = True → Agent 판단 존중 또는 마지막 턴이면 표시
            if agent_decision and agent_decision.get("action") == "FEEDBACK":
                show_feedback = True
                logger.info(f"🤖 [Agent + needs_correction] FEEDBACK 표시 - reasoning: {agent_decision.get('reasoning')}")
            elif is_last_turn:
                # 마지막 턴은 무조건 피드백 표시
                show_feedback = True
                logger.info(f"🔑 [마지막 턴 피드백 강제 표시] needs_correction=True + is_last_turn")
            else:
                # Agent가 NEXT_QUESTION이지만 needs_correction=True면 피드백 안 함
                show_feedback = False
                logger.info(f"📊 [needs_correction=True 무시] Agent said NEXT_QUESTION but needs_correction shows correction needed")
        else:
            # needs_correction = False → 무조건 피드백 미표시 (점수 기준 충분)
            show_feedback = False
            logger.info(f"📊 [needs_correction=False] 점수 기준 충분 - 피드백 미표시")

        # 최종 feedback_result 구성
        feedback_result = None
        if evaluation_result:
            feedback_result = evaluation_result.copy() if isinstance(evaluation_result, dict) else evaluation_result

            # 🔑 피드백 섹션 조건부 설정
            if not show_feedback:
                logger.info(f"📝 [피드백 섹션 제외] session={session_id} - show_feedback=False")
                if isinstance(feedback_result, dict):
                    feedback_result['feedback_sections'] = []  # ✅ 빈 배열로 저장 (NULL 대신)

            # 항상 needs_correction과 retry_count 설정
            if isinstance(feedback_result, dict):
                needs_correction = feedback_result.get("needs_correction", False)
                retry_count = session_state.current_question_retry_count if (session_state and needs_correction) else 0
                feedback_result['needs_correction'] = needs_correction
                feedback_result['retry_count'] = retry_count
                logger.info(f"📊 [점수 및 재시도 정보] session={session_id}, needs_correction={needs_correction}, retry_count={retry_count}")

        # Azure 사용 시 usage 증가
        if can_use_azure and feedback_result:
            try:
                await usage_tracker.increment_usage()
            except Exception as e:
                logger.warning(f"Failed to increment Azure usage: {e}")

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
            show_feedback=show_feedback,
        )

        # ✅ Step 4b: 사용자 발화 DB에 저장 (피드백 섹션이 생성된 후)
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
            logger.info(f"✅ User utterance saved to Spring2: session={session_id}, index={utterance_index}")
        except Exception as e:
            logger.error(f"❌ Failed to save user utterance: session={session_id}, error={e}", exc_info=True)
            await websocket.send_json(
                ErrorMessage(message="Failed to save user utterance", code="DB_SAVE_ERROR").model_dump()
            )

        await websocket.send_json(UtteranceSavedMessage(index=utterance_index).model_dump())

        # Step 6: Retry일 때는 조기 종료 (AI 응답 생성 안 함)
        if needs_retry:
            logger.info(f"Retry required for session={session_id}, exiting without generating AI response")
            return

        # Step 7: 🔑 다음 AI 질문이 8번째가 될 것인지 미리 확인 (생성 전)
        next_ai_turn = session_state.get_ai_turn_number() if session_state else 1
        if next_ai_turn > 7:
            logger.info(f"🏁 Turn limit reached: next_ai_turn={next_ai_turn}, ending session")

            # 🔑 Spring 2에 세션 완료 알림 (DB 업데이트)
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
                logger.info(f"✅ Session completion notified to Spring 2: session={session_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify Spring 2 of session completion: {e}", exc_info=True)

            # 클라이언트에 세션 종료 알림
            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            await websocket.send_json(SessionEndedMessage(reason="turn_limit").model_dump())

            # 세션 정리 및 종합 피드백 생성
            from app.roleplaying.handlers.ws_realtime_handler import _cleanup_session
            await _cleanup_session(session_id, "turn_limit")

            await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
            session_manager.cleanup(session_id)
            return

        # Step 8: AI 응답 생성 (정상 응답일 때만)
        await websocket.send_json(AiTypingMessage().model_dump())

        full_ai_response, is_fixed_question = await _generate_and_stream_ai_response(
            websocket=websocket,
            session_id=session_id,
            session_state=session_state,
            user_text=stt_text,
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
        logger.error(f"Utterance end handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process utterance")
