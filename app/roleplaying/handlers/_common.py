"""
공통 핸들러 유틸리티
====================

TEXT/AUDIO 핸들러에서 공유하는 로직:
- 백그라운드 태스크 에러 처리
- 에러 메시지 전송
- 턴 제한 확인
- Spring 2 저장
- 피드백 평가
- AI 응답 생성
- 피드백 메시지 전송
"""

import asyncio
import logging
import re
import time
from typing import Optional, Tuple

from fastapi import WebSocket, status

from app.config import settings
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.core.session_state_manager import session_manager
from app.roleplaying.core.session_message_handler import SessionMessageHandler
from app.roleplaying.handlers.ws_message_models import (
    AiTextMessage, AiTextStreamingMessage, AiTypingMessage,
    ErrorMessage, FeedbackMessage, FeedbackStreamingMessage,
    RetryRequiredMessage, UtteranceSavedMessage
)

logger = logging.getLogger(__name__)


# ========================================
# 기본 유틸리티
# ========================================


def _handle_task_error(task: asyncio.Task, context: str = "") -> None:
    """Background task 완료 콜백 - 에러 처리"""
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


async def _send_error(websocket: WebSocket, message: str, code: str = "ERROR") -> None:
    """에러 메시지 전송"""
    try:
        await websocket.send_json(ErrorMessage(message=message, code=code).model_dump())
    except Exception as e:
        logger.error(f"Failed to send error: {e}")


async def _check_turn_limit(
    websocket: WebSocket, session_id: str, session_state
) -> bool:
    """턴 제한(7 AI↔사용자 페어) 초과 여부를 확인하고 초과 시 세션 종료

    주의: Retry 중에는 이 함수가 호출되지 않으므로 turn count가 증가하지 않음
    """
    try:
        if session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS):
            logger.info(f"Turn limit reached for session {session_id}, ending session.")

            # 클라이언트에 세션 종료 메시지 전송
            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            try:
                await websocket.send_json(
                    SessionEndedMessage(reason="turn_limit").model_dump()
                )
                logger.info(f"SESSION_ENDED message sent: session={session_id}, reason=turn_limit")
            except Exception as e:
                logger.warning(f"Failed to send SESSION_ENDED message: {e}")

            # ✅ WebSocket 연결 종료
            try:
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
                logger.info(f"WebSocket closed: session={session_id}")
            except Exception as e:
                logger.warning(f"Failed to close WebSocket: {e}")

            return True
        return False
    except Exception as exc:
        logger.error(f"Turn limit check failed: {exc}", exc_info=True)
        return False


async def _schedule_spring2_save(
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
        except Exception as e:
            logger.error(
                f"Failed to save to Spring 2: session={session_id}, index={utterance_index}, error={e}",
                exc_info=True
            )

    task = asyncio.create_task(_save())
    context = f"spring2_save(session={session_id}, speaker={speaker}, index={utterance_index})"
    task.add_done_callback(lambda t: _handle_task_error(t, context))


# ========================================
# 피드백 평가 (공통)
# ========================================


async def _evaluate_feedback(
    feedback_orchestrator,
    websocket: WebSocket,
    session_id: str,
    user_text: str,
    audio_data: Optional[bytes],
    session_state,
    can_use_azure: bool = False,
) -> Optional[dict]:
    """
    피드백 평가 (Optional feedback_result 패턴)

    Returns:
        feedback_result dict 또는 None(평가 실패 시)
    """
    feedback_result = None

    try:
        feedback_start = time.time()
        logger.info(
            f"⏱️  [피드백 평가 시작] session={session_id}, 텍스트 길이: {len(user_text)} 글자, "
            f"audio={audio_data is not None}, azure={can_use_azure}"
        )

        feedback_result = await asyncio.wait_for(
            feedback_orchestrator.evaluate_response_fast(
                user_text=user_text,
                audio_data=audio_data if can_use_azure else None,
                conversation_history=session_state.history if session_state else [],
                scenario_context={
                    "my_role": session_state.my_role if session_state else "",
                    "ai_role": session_state.ai_role if session_state else "",
                    "current_question": session_state.current_question_text if session_state else ""
                },
                retry_count=session_state.current_question_retry_count if session_state else 0
            ),
            timeout=60.0
        )

        if feedback_result and (audio_data is None or not can_use_azure):
            scores = feedback_result.get("scores", {})
            if scores:
                scores["pronunciation_score"] = None

        feedback_elapsed = time.time() - feedback_start
        logger.info(f"✅ [피드백 평가 완료] session={session_id}, 소요 시간: {feedback_elapsed:.2f}초")

    except asyncio.TimeoutError:
        logger.warning(f"⏱️  [피드백 평가 타임아웃] session={session_id}")
        await websocket.send_json(
            ErrorMessage(
                code="FEEDBACK_TIMEOUT",
                message="Feedback evaluation timeout. Continuing without feedback.",
            ).model_dump()
        )
        feedback_result = None

    except Exception as e:
        logger.error(f"❌ [피드백 평가 실패] {e}", exc_info=True)
        await websocket.send_json(
            ErrorMessage(
                code="FEEDBACK_ERROR",
                message="Feedback evaluation failed. Continuing without feedback.",
            ).model_dump()
        )
        feedback_result = None

    return feedback_result


# ========================================
# AI 응답 생성 및 전송 (공통)
# ========================================


async def _generate_and_stream_ai_response(
    websocket: WebSocket,
    session_id: str,
    session_state,
    user_text: str,
) -> Tuple[str, bool]:
    """
    AI 응답 생성 및 스트리밍 전송

    Returns:
        (full_ai_response, is_fixed_question)
    """
    from app.roleplaying.services.business.ai_tutor_service import ai_tutor_service

    full_ai_response = ""
    is_fixed_question = False

    try:
        async for chunk, is_fixed in ai_tutor_service.generate_reply_stream(
            session_state, user_text
        ):
            # 빈 chunk는 건너뛰기 (유효하지 않은 JSON 에러 방지)
            if chunk and chunk.strip():
                full_ai_response += chunk
                is_fixed_question = is_fixed
                await websocket.send_json(
                    AiTextStreamingMessage(chunk=chunk, is_fixed_question=is_fixed).model_dump()
                )

    except Exception as e:
        logger.error(f"Error during AI streaming: {e}", exc_info=True)
        full_ai_response = "Could you tell me more about that?"
        is_fixed_question = False
        await websocket.send_json(
            AiTextStreamingMessage(chunk=full_ai_response, is_fixed_question=False).model_dump()
        )

    # 히스토리와 세션 상태 업데이트
    await SessionMessageHandler.append_message_async(
        session_id=session_id,
        speaker="ai",
        text=full_ai_response,
        is_fixed_question=is_fixed_question,
    )

    if session_state:
        session_state.current_question_text = full_ai_response
        session_state.reset_retry_count()

    return full_ai_response, is_fixed_question


# ========================================
# 피드백 메시지 전송 (공통)
# ========================================


async def _send_feedback_messages(
    websocket: WebSocket,
    session_id: str,
    session_state,
    feedback_result: Optional[dict],
) -> bool:
    """
    피드백 메시지 전송 및 재시도 여부 판단

    Returns:
        True if retry needed (early return), False otherwise
    """
    if not feedback_result:
        logger.info(f"Skipping feedback processing: feedback_result is None")
        return False

    # 점수 전송
    scores = feedback_result.get("scores", {})
    feedback_msg = FeedbackMessage(
        pronunciation_score=scores.get("pronunciation_score"),
        grammar_score=scores.get("grammar_score", 0),
        relevance_score=scores.get("relevance_score", 0),
        overall_score=scores.get("overall_score", 0)
    )
    await websocket.send_json(feedback_msg.model_dump())
    logger.info(f"Feedback scores sent: {feedback_result['scores']}")

    # ✅ 구조화된 피드백 섹션 전송 (NEW - 영문 + 한글)
    try:
        feedback_sections = feedback_result.get("feedback_sections", [])
        if feedback_sections:
            from app.roleplaying.handlers.ws_message_models import FeedbackSectionsMessage
            sections_msg = FeedbackSectionsMessage(sections=feedback_sections)
            await websocket.send_json(sections_msg.model_dump())
            logger.info(f"Feedback sections sent: {len(feedback_sections)} sections")
    except Exception as e:
        logger.error(f"Failed to send feedback sections: {e}")

    # 피드백 텍스트 스트리밍 (선택사항 - 한글 피드백)
    try:
        feedback_text = feedback_result.get("feedback_text", "")
        if feedback_text:
            # '|'로 분할하고 각 부분을 별도로 전송
            parts = feedback_text.split('|')
            for part in parts:
                part = part.strip()
                if part:
                    await websocket.send_json(
                        FeedbackStreamingMessage(chunk=part).model_dump()
                    )
                    await asyncio.sleep(0.1)
            logger.info(f"Feedback text streamed: {feedback_text[:60]}...")
    except Exception as e:
        logger.error(f"Failed to send feedback text: {e}")

    # 재시도 처리
    needs_correction = feedback_result.get("needs_correction", False)
    if needs_correction and session_state and session_state.can_retry():
        session_state.increment_retry_count()
        retry_msg = RetryRequiredMessage(
            reason=feedback_result.get("primary_issue", "correction_needed"),
            retry_count=session_state.current_question_retry_count,
            max_retries=session_state.max_retry_per_question
        )
        await websocket.send_json(retry_msg.model_dump())

        if session_state.current_question_text:
            await websocket.send_json(
                AiTextMessage(
                    text=session_state.current_question_text,
                    is_fixed_question=False
                ).model_dump()
            )
        return True  # Early return - 재시도 필요

    else:
        if session_state:
            session_state.reset_retry_count()

    return False  # 재시도 불필요


# ========================================
# Spring 2 저장 (조건부 피드백)
# ========================================


async def _save_utterance_with_feedback(
    session_id: str,
    speaker: str,
    text: str,
    stt_text: str,
    utterance_index: int,
    audio_data: Optional[bytes],
    session_state,
    feedback_result: Optional[dict],
) -> None:
    """
    Spring 2에 발화 저장 (feedback이 있을 때만 포함)

    Option 3: 모든 피드백 데이터(점수, 텍스트, 구조화된 섹션)를 한 번의 호출로 저장
    별도의 save_feedback 호출 불필요
    """
    try:
        # Base kwargs
        save_kwargs = {
            "session_id": session_id,
            "stt_text": stt_text,
            "utterance_index": utterance_index,
            "speaker": speaker.lower(),
            "text": text,
            "audio_data": audio_data,
            "played_turns": session_state.ai_turn_count if session_state else None,
            "completed_all_turns": session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
            "status": "IN_PROGRESS",
        }

        # ✅ Conditionally include feedback fields
        if feedback_result:
            needs_correction = feedback_result.get("needs_correction", False)
            # needs_correction이 True일 때만 retry_count 유지, False면 0
            retry_count = session_state.current_question_retry_count if (session_state and needs_correction) else 0

            save_kwargs.update({
                "pronunciation_score": feedback_result["scores"].get("pronunciation_score"),
                "grammar_score": feedback_result["scores"].get("grammar_score"),
                "relevance_score": feedback_result["scores"].get("relevance_score"),
                "overall_score": feedback_result["scores"].get("overall_score"),
                "feedback_text": feedback_result.get("feedback_text", ""),
                "needs_correction": needs_correction,  # Boolean (변환은 spring2_client에서)
                "retry_count": retry_count,
                "primary_issue": feedback_result.get("primary_issue", "none"),
                "feedback_sections": feedback_result.get("feedback_sections"),  # Option 3: 구조화된 피드백
            })
        else:
            # No feedback data - explicitly set fields
            # needs_correction should be False (not None) when no feedback
            save_kwargs.update({
                "pronunciation_score": None,
                "grammar_score": None,
                "relevance_score": None,
                "overall_score": None,
                "feedback_text": None,
                "needs_correction": False,  # ✅ Boolean False (spring2_client에서 0으로 변환)
                "retry_count": None,
                "primary_issue": "none",  # ✅ 명시적으로 "none"
                "feedback_sections": None,
            })

        result = await spring2_client.save_utterance(**save_kwargs)
        logger.info(f"Utterance saved to Spring 2: session={session_id}, index={utterance_index}")
        return result

    except Exception as e:
        logger.error(f"Failed to save utterance: session={session_id}, error={e}", exc_info=True)
        return None


# ========================================
# ReAct Agent 기반 피드백 평가 (신규)
# ========================================


async def _evaluate_feedback_with_agent(
    agent,
    session_id: str,
    user_text: str,
    audio_data: Optional[bytes],
    session_state,
    can_use_azure: bool = False,
) -> Optional[dict]:
    """
    ReAct Agent를 통한 피드백 평가 및 판단

    Args:
        agent: FeedbackDecisionAgent 인스턴스
        session_id: 세션 ID
        user_text: 사용자 발화 텍스트
        audio_data: 사용자 오디오 데이터
        session_state: 세션 상태
        can_use_azure: Azure 발음 평가 사용 가능 여부

    Returns:
        {
            "action": "FEEDBACK" | "NEXT_QUESTION",
            "feedback_result": {...} | None,
            "reasoning": str,
            "confidence": float
        }
        또는 None (에러 시)
    """
    try:
        logger.info(
            f"🤖 [ReAct] Starting feedback evaluation: session={session_id}, "
            f"text_length={len(user_text)}, audio={audio_data is not None}, azure={can_use_azure}"
        )

        # ReAct Agent 실행
        agent_decision = await agent.decide_feedback_or_question(
            session_state=session_state,
            user_text=user_text,
            audio_data=audio_data if can_use_azure else None,
            retry_count=session_state.current_question_retry_count if session_state else 0,
            can_use_azure=can_use_azure,
        )

        if agent_decision is None:
            logger.warning(f"❌ [ReAct] Agent returned None for session={session_id}")
            return None

        logger.info(
            f"✅ [ReAct] Agent decision: action={agent_decision.get('action')}, "
            f"confidence={agent_decision.get('confidence'):.2f}, "
            f"reasoning={agent_decision.get('reasoning')[:60]}..."
        )

        return agent_decision

    except Exception as e:
        logger.error(f"❌ [ReAct] Agent evaluation failed: {e}", exc_info=True)
        return None


# ========================================
# AI 질문 저장 (바이링궐 + 추천 키워드)
# ========================================


async def _save_question_with_keywords(
    session_id: str,
    question_en: str,
    turn_number: int,
    utterance_index: int,
    user_role: str,
    ai_role: str,
    scenario_context: str,
    session_state=None,
    slack_message: Optional[str] = None,
    is_fixed_question: bool = False,
) -> None:
    """
    AI 질문을 Spring 2에 저장 (영문 + 한글 + 추천 키워드 포함)

    흐름:
    1. 추천 키워드 생성 (RECOMMENDED_KEYWORDS_PROMPT 사용)
    2. 한글 번역 생성 (QUESTION_BILINGUAL_PROMPT 사용)
    3. Spring 2에 저장 (save_utterance() API 호출)

    Args:
        session_id: 세션 ID
        question_en: AI 질문 (영문)
        turn_number: 턴 번호
        user_role: 사용자 역할
        ai_role: AI 역할
        scenario_context: 시나리오 배경
        slack_message: 원본 Slack 메시지 (선택사항)
        is_fixed_question: 고정 질문 여부
    """
    try:
        from app.roleplaying.services.llm.llm_keyword_generator import keyword_generator
        from app.roleplaying.services.llm.llm_base import LLMServiceBase
        from app.roleplaying.prompts.constants import QUESTION_BILINGUAL_PROMPT
        import json

        logger.info(
            f"🟢 [질문 저장] 추천 키워드 생성 중... "
            f"session={session_id}, turn={turn_number}"
        )

        # ====================================
        # Step 1: 추천 키워드 생성
        # ====================================
        keywords = await keyword_generator.generate_recommended_keywords(
            question=question_en,
            user_role=user_role,
            ai_role=ai_role,
            scenario_context=scenario_context,
            slack_message=slack_message,
            conversation_summary=""
        )

        logger.info(f"✅ [질문 저장] 키워드 생성 완료: {keywords}")

        # ====================================
        # Step 2: 한글 번역 생성
        # ====================================
        logger.info(f"🟢 [질문 저장] 한글 번역 생성 중...")

        llm = LLMServiceBase(
            api_key=settings.openai_api_key,
            model_name=settings.OPENAI_MODEL_FEEDBACK,
            temperature=0.3
        ).llm

        translation_prompt = QUESTION_BILINGUAL_PROMPT.format(
            english_question=question_en
        )
        translation_response = await llm.invoke(translation_prompt)

        # JSON에서 korean_question 추출
        question_ko = question_en  # 기본값: 번역 실패 시 영문 사용
        try:
            json_match = re.search(r'\{[^{}]*"korean_question"[^{}]*\}', translation_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                question_ko = parsed.get("korean_question", question_en)
        except Exception as e:
            logger.warning(f"Failed to parse Korean translation: {e}")

        logger.info(f"✅ [질문 저장] 한글 번역 완료")

        # ====================================
        # Step 3: Spring 2에 저장 (ScenarioMessage에 통합)
        # ====================================
        logger.info(
            f"🟢 [질문 저장] Spring 2에 저장 중... "
            f"session={session_id}, utterance_index={utterance_index}"
        )

        # Option 3: AI 질문을 ScenarioMessage에 직접 저장
        # save_utterance()에 question_ko와 recommended_keywords를 포함시킴
        await spring2_client.save_utterance(
            session_id=session_id,
            stt_text=question_en,
            utterance_index=utterance_index,
            speaker="ai",
            text=question_en,
            audio_data=None,
            played_turns=session_state.ai_turn_count if session_state else None,
            completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
            status="IN_PROGRESS",
            question_ko=question_ko,  # 한글 질문
            recommended_keywords=keywords,  # 추천 키워드
        )

        logger.info(
            f"✅ [질문 저장] 완료: session={session_id}, utterance_index={utterance_index}, "
            f"keywords={len(keywords)}"
        )

    except Exception as e:
        logger.error(
            f"❌ [질문 저장] 실패: session={session_id}, turn={turn_number}, error={e}",
            exc_info=True
        )
        raise  # ✅ 에러를 호출자에게 전파
