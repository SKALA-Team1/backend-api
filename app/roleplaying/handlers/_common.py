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
    AiTextMessage, AiTextStreamingMessage, AiTextKoreanMessage, AiTypingMessage,
    ErrorMessage, FeedbackMessage, FeedbackSectionsMessage, FeedbackStreamingMessage,
    RetryRequiredMessage, UtteranceSavedMessage, TtsAudioMessage, TtsVisemeMessage
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
            from app.roleplaying.handlers.ws_message_models import SessionEndedMessage
            try:
                await websocket.send_json(
                    SessionEndedMessage(reason="turn_limit").model_dump()
                )
            except Exception as e:
                logger.warning(f"Failed to send SESSION_ENDED message: {e}")

            try:
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason="Turn limit reached")
            except Exception as e:
                logger.warning(f"Failed to close WebSocket: {e}")

            return True
        return False
    except Exception as exc:
        logger.error(f"Turn limit check failed: {exc}", exc_info=True)
        return False


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

        conversation_history = session_state.history if session_state else []
        scenario_context = {
            "my_role": session_state.my_role if session_state else "",
            "ai_role": session_state.ai_role if session_state else "",
            "current_question": session_state.current_question_text if session_state else ""
        }

        feedback_result = await asyncio.wait_for(
            feedback_orchestrator.evaluate_response_fast(
                user_text=user_text,
                audio_data=audio_data if can_use_azure else None,
                conversation_history=conversation_history,
                scenario_context=scenario_context,
                retry_count=session_state.current_question_retry_count if session_state else 0
            ),
            timeout=60.0
        )

        # ✅ 스트리밍에 필요한 추가 정보를 feedback_result에 추가
        if feedback_result:
            feedback_result["user_text"] = user_text
            feedback_result["conversation_history"] = conversation_history
            feedback_result["scenario_context"] = scenario_context
            feedback_result["audio_data"] = audio_data if can_use_azure else None

        if feedback_result and (audio_data is None or not can_use_azure):
            scores = feedback_result.get("scores", {})
            if scores:
                scores["pronunciation_score"] = None

    except asyncio.TimeoutError:
        logger.warning(f"Feedback evaluation timeout: session={session_id}")
        await websocket.send_json(
            ErrorMessage(
                code="FEEDBACK_TIMEOUT",
                message="Feedback evaluation timeout. Continuing without feedback.",
            ).model_dump()
        )
        feedback_result = None

    except Exception as e:
        logger.error(f"Feedback evaluation failed: {e}", exc_info=True)
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
) -> Tuple[str, bool, str, list]:
    """
    AI 응답 생성 및 스트리밍 전송

    Returns:
        (full_ai_response, is_fixed_question, full_ai_response_ko, keywords)
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

    # ========================================
    # 병렬 처리: 한글 번역 + TTS 생성 + 키워드 생성
    # ========================================
    # 한글 번역, TTS, 키워드 생성은 독립적이므로 동시 실행
    translate_task = asyncio.create_task(_translate_question_to_korean(full_ai_response))
    tts_task = asyncio.create_task(_send_tts_audio_and_visemes(websocket, full_ai_response, context="", session_id=session_id))
    
    # 키워드 생성 태스크 추가
    keywords_task = asyncio.create_task(_generate_recommended_keywords_task(
        question=full_ai_response,
        session_state=session_state
    ))

    # 병렬 실행 (TTS는 WebSocket 전송 포함)
    results = await asyncio.gather(translate_task, tts_task, keywords_task, return_exceptions=True)

    full_ai_response_ko = results[0] if not isinstance(results[0], Exception) else full_ai_response
    tts_error = results[1] if isinstance(results[1], Exception) else None
    keywords = results[2] if not isinstance(results[2], Exception) else []

    if tts_error:
        logger.warning(f"TTS error during streaming: {tts_error}")

    # 한글 번역과 키워드를 별도 메시지로 전송 (스트리밍이 아닌 경우에만)
    if full_ai_response_ko and full_ai_response_ko != full_ai_response:
        try:
            # 키워드 포함하여 전송
            await websocket.send_json(
                AiTextKoreanMessage(
                    text_ko=full_ai_response_ko, 
                    is_fixed_question=is_fixed_question,
                    recommended_keywords=keywords
                ).model_dump()
            )
        except Exception as e:
            logger.warning(f"Failed to send Korean translation: {e}")
    elif keywords:
        # 한글 번역이 없더라도 키워드가 있으면 전송 (드문 경우)
        try:
             await websocket.send_json(
                AiTextKoreanMessage(
                    text_ko=full_ai_response, # 영문 그대로
                    is_fixed_question=is_fixed_question,
                    recommended_keywords=keywords
                ).model_dump()
            )
        except Exception as e:
            logger.warning(f"Failed to send keywords: {e}")


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

    return full_ai_response, is_fixed_question, full_ai_response_ko, keywords


# ========================================
# TTS 오디오 및 Viseme 전송 (공통)
# ========================================

async def _send_tts_audio_and_visemes(websocket: WebSocket, text: str, context: str = "", session_id: str = None) -> None:
    """
    ElevenLabs TTS를 호출하고 오디오 및 Viseme 데이터를 WebSocket으로 전송
    
    Args:
        websocket: WebSocket 연결
        text: TTS로 변환할 텍스트
        context: 에러 로그에 포함할 컨텍스트 정보 (예: "INIT")
        session_id: 세션 ID (voice_id 조회용, 선택적)
    """
    try:
        from app.adapters.tts_adapter import get_tts_adapter
        from app.roleplaying.core.session_state_manager import session_manager
        
        # 세션에서 voice_id 가져오기
        voice_id = None
        if session_id:
            session_state = session_manager.get_session(session_id)
            if session_state and session_state.voice_id:
                voice_id = session_state.voice_id
        
        tts_adapter = get_tts_adapter()
        tts_result = await tts_adapter.synthesize_with_viseme(text, voice_id=voice_id)
        
        # 오디오 전송
        await websocket.send_json(
            TtsAudioMessage(
                audio_base64=tts_result['audio_base64']
            ).model_dump()
        )

        # Viseme 데이터 배치 전송 (개별 메시지 폭발 방지)
        # 10개씩 배치하여 WebSocket 메시지 수 90% 감소
        viseme_batch_size = 10
        viseme_batch = []

        for viseme in tts_result['visemes']:
            viseme_batch.append(
                TtsVisemeMessage(
                    start_time=viseme['start_time'],
                    end_time=viseme['end_time'],
                    value=viseme['value']
                ).model_dump()
            )

            # 배치 크기에 도달하면 전송
            if len(viseme_batch) >= viseme_batch_size:
                for batched_viseme in viseme_batch:
                    await websocket.send_json(batched_viseme)
                viseme_batch = []

        # 남은 Viseme 전송
        if viseme_batch:
            for batched_viseme in viseme_batch:
                await websocket.send_json(batched_viseme)
    except Exception as e:
        error_context = f" ({context})" if context else ""
        logger.error(f"TTS error{error_context}: {e}", exc_info=True)
        # TTS 실패해도 세션은 계속 진행


# ========================================
# 피드백 메시지 전송 (공통)
# ========================================


async def _send_feedback_messages(
    websocket: WebSocket,
    session_id: str,
    session_state,
    feedback_result: Optional[dict],
    show_feedback: bool = True,
) -> bool:
    """
    피드백 메시지 전송 및 재시도 여부 판단
    - 점수 전송
    - 피드백 섹션 스트리밍 (각 섹션이 생성되면 즉시 전송)

    Args:
        show_feedback: False면 피드백 섹션을 생성하지 않음 (점수는 여전히 전송)

    Returns:
        True if retry needed (early return), False otherwise
    """
    if not feedback_result:
        return False

    scores = feedback_result.get("scores", {})
    feedback_msg = FeedbackMessage(
        pronunciation_score=scores.get("pronunciation_score"),
        grammar_score=scores.get("grammar_score", 0),
        relevance_score=scores.get("relevance_score", 0),
        overall_score=scores.get("overall_score", 0)
    )
    await websocket.send_json(feedback_msg.model_dump())

    if show_feedback:
        feedback_sections_list = []
        try:
            from app.roleplaying.services.dependencies.feedback import get_feedback_orchestrator

            feedback_orchestrator = get_feedback_orchestrator()

            pronunciation = feedback_result.get("pronunciation")
            grammar = feedback_result.get("grammar")
            relevance = feedback_result.get("relevance")
            pronunciation_score = feedback_result.get("pronunciation_score")
            grammar_score = feedback_result.get("grammar_score")
            relevance_score = feedback_result.get("relevance_score")
            user_text = feedback_result.get("user_text", "")
            conversation_history = feedback_result.get("conversation_history", [])
            scenario_context = feedback_result.get("scenario_context", {})
            audio_data = feedback_result.get("audio_data")

            section_count = 0
            async for item in feedback_orchestrator._build_feedback_sections_stream(
                user_text=user_text,
                conversation_history=conversation_history,
                scenario_context=scenario_context,
                pronunciation=pronunciation,
                grammar=grammar,
                relevance=relevance,
                pronunciation_score=pronunciation_score,
                grammar_score=grammar_score,
                relevance_score=relevance_score,
                audio_data=audio_data
            ):
                if item["type"] == "feedback_token":
                    token_msg = FeedbackStreamingMessage(
                        chunk=item["token"]
                    )
                    await websocket.send_json(token_msg.model_dump())

                elif item["type"] == "feedback_section":
                    section_score = item["score"]

                    sections_msg = FeedbackSectionsMessage(sections=[{
                        "type": item["section_type"],
                        "feedback_en": item["feedback_en"],
                        "feedback_ko": item["feedback_ko"],
                        "score": section_score
                    }])
                    await websocket.send_json(sections_msg.model_dump())
                    feedback_sections_list.append({
                        "type": item["section_type"],
                        "feedback_en": item["feedback_en"],
                        "feedback_ko": item["feedback_ko"],
                        "score": section_score
                    })
                    section_count += 1

            if feedback_sections_list:
                feedback_result["feedback_sections"] = feedback_sections_list

        except Exception as e:
            logger.error(f"Failed to stream feedback sections: {e}", exc_info=True)
    else:
        if isinstance(feedback_result, dict):
            feedback_result["feedback_sections"] = []

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
            # 재시도 질문 전송 (영문)
            await websocket.send_json(
                AiTextMessage(
                    text=session_state.current_question_text,
                    is_fixed_question=False,
                    is_retry_question=True # 프론트엔드에서 TTS 재생 타이밍 조절을 위해 추가
                ).model_dump()
            )
            
            # 재시도 질문의 한글 번역 생성 및 TTS 생성을 병렬로 처리
            translate_task = asyncio.create_task(_translate_question_to_korean(session_state.current_question_text))
            tts_task = asyncio.create_task(
                _send_tts_audio_and_visemes(websocket, session_state.current_question_text, context="RETRY", session_id=session_id)
            )
            
            results = await asyncio.gather(translate_task, tts_task, return_exceptions=True)
            question_ko = results[0] if not isinstance(results[0], Exception) else session_state.current_question_text
            
            if question_ko and question_ko != session_state.current_question_text:
                try:
                    await websocket.send_json(
                        AiTextKoreanMessage(text_ko=question_ko, is_fixed_question=False).model_dump()
                    )
                except Exception as e:
                    logger.warning(f"Failed to send Korean translation for retry: {e}")
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

        if feedback_result:
            needs_correction = feedback_result.get("needs_correction", False)
            retry_count = session_state.current_question_retry_count if (session_state and needs_correction) else 0

            scores = feedback_result.get("scores", {})
            if not scores:
                logger.warning(f"Feedback result has no scores: {feedback_result}")

            feedback_sections = feedback_result.get("feedback_sections")

            save_kwargs.update({
                "pronunciation_score": scores.get("pronunciation_score"),
                "grammar_score": scores.get("grammar_score"),
                "relevance_score": scores.get("relevance_score"),
                "overall_score": scores.get("overall_score"),
                "needs_correction": needs_correction,  # Boolean (변환은 spring2_client에서)
                "retry_count": retry_count,
                "primary_issue": feedback_result.get("primary_issue", "none"),
                "feedback_sections": feedback_sections,  # ✅ 구조화된 피드백 (영문 + 한글)
            })
        else:
            save_kwargs.update({
                "pronunciation_score": None,
                "grammar_score": None,
                "relevance_score": None,
                "overall_score": None,
                "needs_correction": False,  # ✅ Boolean False (spring2_client에서 0으로 변환)
                "retry_count": 0,  # ✅ 0으로 저장 (재시도 필요 없음)
                "primary_issue": "none",  # ✅ 명시적으로 "none"
                "feedback_sections": [],
            })

        result = await spring2_client.save_utterance(**save_kwargs)
        return result

    except Exception as e:
        logger.error(f"Failed to save utterance: session={session_id}, error={e}", exc_info=True)
        return None


# ========================================
# AI 질문 번역 (한글)
# ========================================


async def _translate_question_to_korean(question_en: str) -> str:
    """
    영문 질문을 한글로 번역

    QuestionTranslatorImpl 싱글톤 인스턴스를 사용하여
    LLM 클라이언트를 재사용하고 성능을 최적화합니다.

    Args:
        question_en: 영문 질문

    Returns:
        한글 번역 (번역 실패 시 영문 반환)
    """
    try:
        from app.roleplaying.services.llm.llm_question_translator import question_translator

        return await question_translator.translate_question(question_en)
    except Exception as e:
        logger.warning(f"Failed to translate question to Korean: {e}")
        return question_en  # Fallback: return English question


async def _generate_recommended_keywords_task(
    question: str,
    session_state
) -> list:
    """
    추천 키워드 생성 (비동기 태스크용)
    """
    if not session_state:
        return []

    try:
        from app.roleplaying.services.llm.llm_keyword_generator import keyword_generator
        
        return await keyword_generator.generate_recommended_keywords(
            question=question,
            user_role=session_state.my_role,
            ai_role=session_state.ai_role,
            scenario_context=f"Subject ID: {session_state.subject_id}",
            slack_message=None,
            conversation_summary="" # 필요시 추가
        )
    except Exception as e:
        logger.error(f"Failed to generate keywords task: {e}")
        return []


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
    question_ko: Optional[str] = None,
    keywords: Optional[list] = None,  # ✅ 이미 생성된 키워드가 있으면 받음
) -> None:
    """
    AI 질문을 Spring 2에 저장 (영문 + 한글 + 추천 키워드 포함)

    흐름:
    1. 추천 키워드 생성 (keywords가 없으면 생성)
    2. 한글 번역 (question_ko가 없으면 생성)
    3. Spring 2에 저장 (save_utterance() API 호출)

    Args:
        session_id: 세션 ID
        question_en: AI 질문 (영문)
        turn_number: 턴 번호
        user_role: 사용자 역할
        ai_role: AI 역할
        scenario_context: 시나리오 배경
        session_state: 세션 상태
        slack_message: 원본 Slack 메시지 (선택사항)
        is_fixed_question: 고정 질문 여부
        question_ko: 한글 번역 (선택사항, 없으면 자동 생성)
        keywords: 추천 키워드 리스트 (선택사항, 없으면 자동 생성)
    """
    try:
        from app.roleplaying.services.llm.llm_keyword_generator import keyword_generator
        
        # 키워드가 전달되지 않았으면 생성
        if keywords is None:
            keywords = await keyword_generator.generate_recommended_keywords(
                question=question_en,
                user_role=user_role,
                ai_role=ai_role,
                scenario_context=scenario_context,
                slack_message=slack_message,
                conversation_summary=""
            )

        # 한글 번역: 매개변수로 전달된 것이 있으면 사용, 없으면 생성
        if not question_ko:
            question_ko = await _translate_question_to_korean(question_en)

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
            question_ko=question_ko,
            recommended_keywords=keywords,
        )

    except Exception as e:
        logger.error(
            f"Failed to save question: session={session_id}, turn={turn_number}, error={e}",
            exc_info=True
        )
        raise
