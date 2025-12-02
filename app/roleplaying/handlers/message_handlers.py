"""
WebSocket 메시지 핸들러들
=========================

각 메시지 타입별 비즈니스 로직을 처리합니다.
MessageRouter의 핸들러로 사용됩니다.

handler 시그니처:
  async def handler(router, websocket, session_id, message):
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket, status

from app.config import settings
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.core.session_state_manager import session_manager, SessionStatus
from app.roleplaying.handlers.session_validators import ErrorHandler
from app.roleplaying.handlers.ws_message_models import (
    AckMessage, AiTextMessage, AiTextStreamingMessage, AiTypingMessage,
    ErrorMessage, FeedbackMessage, FeedbackStreamingMessage,
    InitMessage, RetryRequiredMessage, SessionEndedMessage,
    SttFinalMessage, SttPartialMessage, UserTextMessage,
    UtteranceSavedMessage
)

logger = logging.getLogger(__name__)


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
    """턴 제한(7 AI↔사용자 페어) 초과 여부를 확인하고 초과 시 세션 종료"""
    try:
        if session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS):
            logger.info(f"Turn limit reached for session {session_id}, ending session.")
            await handle_end_session(None, websocket, session_id, {"reason": "turn_limit"})
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
# 메시지 핸들러들
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

        # STT 스트리밍 세션 생성
        from app.roleplaying.services.stt.speech_to_text_service import stt_service
        try:
            await stt_service.create_streaming_session(session_id)
            logger.info(f"STT streaming session created: {session_id}")
        except Exception as e:
            logger.warning(f"Failed to create STT streaming session: {e}")

        logger.info(
            f"Session initialized: {session_id}, "
            f"role={init_msg.myRole} → {init_msg.aiRole}"
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
        await session_manager.append_message_async(
            session_id=session_id,
            speaker="ai",
            text=first_question,
            is_fixed_question=True,
        )

        first_ai_index = await session_manager.increment_utterance_index_async(session_id)
        await _schedule_spring2_save(
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
        await session_manager.append_message_async(
            session_id=session_id,
            speaker="user",
            text=user_text,
            audio_s3_url=None,
        )

        # Step 2: 피드백 평가
        from app.roleplaying.services.dependencies import get_feedback_orchestrator

        feedback_orchestrator = get_feedback_orchestrator()
        feedback_result = None
        try:
            feedback_start = time.time()
            logger.info(f"⏱️  [피드백 평가 시작] session={session_id}, 텍스트 길이: {len(user_text)} 글자")

            feedback_result = await asyncio.wait_for(
                feedback_orchestrator.evaluate_response_fast(
                    user_text=user_text,
                    audio_data=None,
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
            feedback_elapsed = time.time() - feedback_start
            logger.info(f"✅ [피드백 평가 완료] 총 소요 시간: {feedback_elapsed:.2f}초")

            # 점수 전송
            feedback_msg = FeedbackMessage(
                pronunciation_score=0,
                grammar_score=feedback_result["scores"]["grammar_score"],
                relevance_score=feedback_result["scores"]["relevance_score"],
                overall_score=feedback_result["scores"]["overall_score"]
            )
            await websocket.send_json(feedback_msg.model_dump())

            # 피드백 텍스트 스트리밍
            async def _generate_and_send_feedback():
                try:
                    feedback_text = feedback_result.get("feedback_text", "")
                    if feedback_text:
                        sentences = re.split(r'(?<=[.!?|])\s+', feedback_text)
                        for i, sentence in enumerate(sentences):
                            if sentence.strip():
                                if i < len(sentences) - 1 and not sentence.endswith(('|', '.')):
                                    chunk = sentence.strip() + " "
                                else:
                                    chunk = sentence.strip()
                                await websocket.send_json(
                                    FeedbackStreamingMessage(chunk=chunk).model_dump()
                                )
                                await asyncio.sleep(0.1)
                        logger.info(f"Feedback text streamed: {feedback_text[:60]}...")
                    else:
                        await websocket.send_json(
                            FeedbackStreamingMessage(chunk="평가 완료").model_dump()
                        )
                except Exception as e:
                    logger.error(f"Failed to send feedback text: {e}")

            feedback_task = asyncio.create_task(_generate_and_send_feedback())
            feedback_task.add_done_callback(lambda t: _handle_task_error(t, f"feedback_text(session={session_id})"))

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
                return
            else:
                if session_state:
                    session_state.reset_retry_count()

        except asyncio.TimeoutError:
            logger.error(f"Feedback evaluation timeout: session={session_id}")
            feedback_result = {
                "needs_correction": False,
                "scores": {
                    "grammar_score": 70,
                    "relevance_score": 70,
                    "overall_score": 46
                },
            }
        except Exception as e:
            logger.error(f"Feedback evaluation failed: {e}", exc_info=True)
            feedback_result = {
                "needs_correction": False,
                "scores": {
                    "grammar_score": 70,
                    "relevance_score": 70,
                    "overall_score": 46
                },
            }

        # Step 3: Spring 2에 텍스트 저장
        utterance_index = session_manager.increment_utterance_index(session_id)

        async def _save_user_text_with_feedback():
            try:
                await spring2_client.save_utterance(
                    session_id=session_id,
                    stt_text=user_text,
                    utterance_index=utterance_index,
                    speaker="user",
                    text=user_text,
                    audio_data=None,
                    played_turns=session_state.ai_turn_count if session_state else None,
                    completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
                    status="IN_PROGRESS",
                )
            except Exception as e:
                logger.error(f"Failed to save user text: session={session_id}, error={e}", exc_info=True)

        task = asyncio.create_task(_save_user_text_with_feedback())
        task.add_done_callback(lambda t: _handle_task_error(t, f"spring2_save_user_text(session={session_id})"))

        await websocket.send_json(
            UtteranceSavedMessage(index=utterance_index).model_dump()
        )

        # 턴 제한 확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # Step 4: AI 응답 생성
        await websocket.send_json(AiTypingMessage().model_dump())

        from app.roleplaying.services.business.ai_tutor_service import ai_tutor_service

        full_ai_response = ""
        is_fixed_question = False

        try:
            async for chunk, is_fixed in ai_tutor_service.generate_reply_stream(
                session_state, user_text
            ):
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

        await session_manager.append_message_async(
            session_id=session_id,
            speaker="ai",
            text=full_ai_response,
            is_fixed_question=is_fixed_question,
        )

        if session_state:
            session_state.current_question_text = full_ai_response
            session_state.reset_retry_count()

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

        if await _check_turn_limit(websocket, session_id, session_state):
            return

    except Exception as e:
        logger.error(f"User text handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process text message")


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

        # Step 2: 피드백 평가
        from app.roleplaying.services.dependencies import get_feedback_orchestrator
        from app.roleplaying.services.utils.azure_usage_tracker import usage_tracker

        feedback_orchestrator = get_feedback_orchestrator()
        try:
            can_use_azure = await usage_tracker.can_use_azure()
            logger.info(f"⏱️  [피드백 평가 시작] session={session_id}, STT: '{stt_text[:50]}...', Azure={can_use_azure}")

            feedback_result = await asyncio.wait_for(
                feedback_orchestrator.evaluate_response_fast(
                    user_text=stt_text,
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

            if can_use_azure:
                await usage_tracker.increment_usage()

            feedback_msg = FeedbackMessage(
                pronunciation_score=feedback_result["scores"]["pronunciation_score"],
                grammar_score=feedback_result["scores"]["grammar_score"],
                relevance_score=feedback_result["scores"]["relevance_score"],
                overall_score=feedback_result["scores"]["overall_score"]
            )
            await websocket.send_json(feedback_msg.model_dump())

            # 피드백 텍스트 스트리밍
            async def _generate_and_send_feedback():
                try:
                    feedback_text = feedback_result.get("feedback_text", "")
                    if feedback_text:
                        sentences = re.split(r'(?<=[.!?|])\s+', feedback_text)
                        for i, sentence in enumerate(sentences):
                            if sentence.strip():
                                if i < len(sentences) - 1 and not sentence.endswith(('|', '.')):
                                    chunk = sentence.strip() + " "
                                else:
                                    chunk = sentence.strip()
                                await websocket.send_json(
                                    FeedbackStreamingMessage(chunk=chunk).model_dump()
                                )
                                await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send feedback text: {e}")

            feedback_task = asyncio.create_task(_generate_and_send_feedback())
            feedback_task.add_done_callback(lambda t: _handle_task_error(t, f"feedback_text(session={session_id})"))

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
                return
            else:
                if session_state:
                    session_state.reset_retry_count()

        except asyncio.TimeoutError:
            logger.error(f"Feedback evaluation timeout: session={session_id}")
        except Exception as e:
            logger.error(f"Feedback evaluation failed: {e}", exc_info=True)

        # Step 3: Spring 2에 사용자 발화 저장
        utterance_index = session_manager.increment_utterance_index(session_id)

        async def _save_user_utterance():
            try:
                await spring2_client.save_utterance(
                    session_id=session_id,
                    audio_data=audio_data,
                    stt_text=stt_text,
                    utterance_index=utterance_index,
                    speaker="user",
                    text=stt_text,
                    played_turns=session_state.ai_turn_count if session_state else None,
                    completed_all_turns=session_state.has_reached_turn_limit(settings.ROLEPLAY_MAX_TURNS) if session_state else False,
                    status="IN_PROGRESS",
                )
            except Exception as e:
                logger.error(f"Failed to save user utterance: session={session_id}, error={e}", exc_info=True)

        task = asyncio.create_task(_save_user_utterance())
        task.add_done_callback(lambda t: _handle_task_error(t, f"spring2_save_utterance(session={session_id})"))

        await websocket.send_json(UtteranceSavedMessage(index=utterance_index).model_dump())

        # 턴 제한 확인
        if await _check_turn_limit(websocket, session_id, session_state):
            return

        # Step 4: AI 응답 생성
        await websocket.send_json(AiTypingMessage().model_dump())

        from app.roleplaying.services.business.ai_tutor_service import ai_tutor_service

        full_ai_response = ""
        is_fixed_question = False

        try:
            async for chunk, is_fixed in ai_tutor_service.generate_reply_stream(
                session_state, stt_text
            ):
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

        await session_manager.append_message_async(
            session_id=session_id,
            speaker="ai",
            text=full_ai_response,
            is_fixed_question=is_fixed_question,
        )

        if session_state:
            session_state.current_question_text = full_ai_response
            session_state.reset_retry_count()

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

        if await _check_turn_limit(websocket, session_id, session_state):
            return

    except Exception as e:
        logger.error(f"Utterance end handler error: {e}", exc_info=True)
        await _send_error(websocket, "Failed to process utterance")


async def handle_end_session(router, websocket: WebSocket, session_id: str, message: dict) -> None:
    """
    세션 종료 처리

    1. SessionManager.end_session()
    2. Spring 2에 세션 완료 알림
    3. SESSION_ENDED 메시지 전송
    """
    try:
        reason = message.get("reason", "user_end") if isinstance(message, dict) else "user_end"
        logger.info(f"Ending session: {session_id}, reason={reason}")

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
        logger.info(f"Session ended and cleaned up: {session_id}")

    except Exception as e:
        logger.error(f"End session handler error: {e}", exc_info=True)
