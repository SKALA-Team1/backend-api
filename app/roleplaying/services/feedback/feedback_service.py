"""
Feedback Service Refactored

구조:
    GrammarEvaluatorImpl         → 문법 평가만 담당
    RelevanceEvaluatorImpl       → 맥락 평가만 담당
    FeedbackJudgeImpl            → 교정 필요 여부 판단만 담당
    FeedbackOrchestratorImpl     → 전체 평가 조율만 담당
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any

from app.config import settings
from app.roleplaying.services.llm.llm_provider_factory import create_llm_provider
from app.roleplaying.services.service_interfaces import (
    PronunciationEvaluator,
    GrammarEvaluator,
    RelevanceEvaluator,
    FeedbackJudge,
    FeedbackOrchestrator
)
from app.roleplaying.prompts.constants import (
    GRAMMAR_EVALUATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    PRONUNCIATION_FEEDBACK_PROMPT,
)
from app.roleplaying.services.utils.service_utils import (
    extract_json_from_response,
    normalize_score,
    normalize_score_from_string,
)

logger = logging.getLogger(__name__)


# ============================================
# GrammarEvaluatorImpl
# ============================================

class GrammarEvaluatorImpl:
    """문법 평가만 담당하는 클래스

    LLM을 사용하여 사용자의 문법을 평가합니다.
    책임: 문법 평가만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        문법 평가기 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델명
            temperature: 창의성 레벨 (낮을수록 일관성 있음)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature
        )

        logger.info(f"GrammarEvaluatorImpl initialized with OpenAI provider")

    async def evaluate_grammar(self, user_text: str) -> Optional[Dict[str, Any]]:
        """
        문법 평가

        Args:
            user_text: 사용자 발화 텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str
            }
            또는 None
        """
        prompt = GRAMMAR_EVALUATION_PROMPT.format(user_text=user_text)

        try:
            logger.info("🟢 [문법 평가] LLM 호출 중...")

            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)
            logger.info(f"🔍 [문법 평가 LLM 응답] {response_text[:200]}...")

            # JSON 객체 추출 시도
            result = extract_json_from_response(response_text)
            logger.info(f"📌 [JSON 추출 결과] {result}")  # ← 직접 추출 결과 로깅
            if result:
                score = normalize_score(result.get("score"))
                feedback = result.get("feedback", "")
                if score is None:
                    logger.warning("Grammar evaluation returned no score")
                    return None
                logger.info(f"✅ [문법 평가 완료] {score}점 | feedback: {feedback[:50] if feedback else '(없음)'}")
                return_value = {
                    "score": score,
                    "feedback": feedback
                }
                logger.info(f"📤 [문법 평가 반환값] {return_value}")  # ← 반환값 로깅
                return return_value
            else:
                # 점수만 추출 시도
                score = normalize_score_from_string(response_text)
                if score is None:
                    logger.warning(f"Failed to parse grammar score from: {response_text}")
                    return None
                logger.info(f"✅ [문법 평가 완료 (파싱)] {score}점")
                return {"score": score, "feedback": response_text}

        except Exception as e:
            logger.error(f"Grammar evaluation failed: {e}")
            return None

    async def evaluate_grammar_stream(self, user_text: str):
        """
        문법 평가 (토큰 단위 스트리밍)

        Args:
            user_text: 사용자 발화 텍스트

        Yields:
            각 토큰 문자열
        """
        prompt = GRAMMAR_EVALUATION_PROMPT.format(user_text=user_text)

        try:
            logger.info("🟢 [문법 평가 스트리밍] LLM 스트리밍 중...")

            async for token in self.llm.stream(prompt):
                if token:  # 빈 토큰 제외
                    yield token
                    logger.debug(f"📤 [문법 평가 토큰] {repr(token)}")

        except Exception as e:
            logger.error(f"Grammar evaluation streaming failed: {e}")
            yield ""  # Fallback: 빈 응답


# ============================================
# RelevanceEvaluatorImpl
# ============================================

class RelevanceEvaluatorImpl:
    """맥락 평가만 담당하는 클래스

    대화 맥락과의 관련성을 평가합니다.
    책임: 맥락 평가만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        맥락 평가기 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델명
            temperature: 창의성 레벨
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature
        )

        logger.info(f"RelevanceEvaluatorImpl initialized with OpenAI provider")

    async def evaluate_relevance(
        self,
        user_text: str,
        conversation_history: list,
        scenario_context: dict
    ) -> Optional[Dict[str, Any]]:
        """
        맥락 평가

        Args:
            user_text: 사용자 발화 텍스트
            conversation_history: 대화 히스토리
            scenario_context: 시나리오 컨텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str
            }
            또는 None
        """
        context = self._build_conversation_context(conversation_history, scenario_context)

        prompt = RELEVANCE_EVALUATION_PROMPT.format(
            context=context,
            user_text=user_text
        )

        try:
            logger.info("🔴 [맥락 평가] LLM 호출 중...")

            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)
            logger.info(f"🔍 [맥락 평가 LLM 응답] {response_text[:200]}...")

            # JSON 객체 추출 시도
            result = extract_json_from_response(response_text)
            logger.info(f"📌 [JSON 추출 결과] {result}")  # ← 직접 추출 결과 로깅
            if result:
                score = normalize_score(result.get("score"))
                feedback = result.get("feedback", "")
                if score is None:
                    logger.warning("Relevance evaluation returned no score")
                    return None
                logger.info(f"✅ [맥락 평가 완료] {score}점 | feedback: {feedback[:50] if feedback else '(없음)'}")
                return_value = {
                    "score": score,
                    "feedback": feedback
                }
                logger.info(f"📤 [맥락 평가 반환값] {return_value}")  # ← 반환값 로깅
                return return_value
            else:
                # 점수만 추출 시도
                score = normalize_score_from_string(response_text)
                if score is None:
                    logger.warning(f"Failed to parse relevance score from: {response_text}")
                    return None
                logger.info(f"✅ [맥락 평가 완료 (파싱)] {score}점")
                return {"score": score, "feedback": response_text}

        except Exception as e:
            logger.error(f"Relevance evaluation failed: {e}")
            return None

    async def evaluate_relevance_stream(
        self,
        user_text: str,
        conversation_history: list,
        scenario_context: dict
    ):
        """
        맥락 평가 (토큰 단위 스트리밍)

        Args:
            user_text: 사용자 발화 텍스트
            conversation_history: 대화 히스토리
            scenario_context: 시나리오 컨텍스트

        Yields:
            각 토큰 문자열
        """
        context = self._build_conversation_context(conversation_history, scenario_context)

        prompt = RELEVANCE_EVALUATION_PROMPT.format(
            context=context,
            user_text=user_text
        )

        try:
            logger.info("🔴 [맥락 평가 스트리밍] LLM 스트리밍 중...")

            async for token in self.llm.stream(prompt):
                if token:  # 빈 토큰 제외
                    yield token
                    logger.debug(f"📤 [맥락 평가 토큰] {repr(token)}")

        except Exception as e:
            logger.error(f"Relevance evaluation streaming failed: {e}")
            yield ""  # Fallback: 빈 응답

    def _build_conversation_context(self, history: list, scenario: dict) -> str:
        """대화 컨텍스트 구성"""
        context_parts = []

        # 시나리오 정보
        if scenario:
            context_parts.append(f"역할: {scenario.get('my_role', '')} vs {scenario.get('ai_role', '')}")
            context_parts.append(f"현재 질문: {scenario.get('current_question', '')}")

        # 최근 대화 히스토리 (최대 3턴)
        if history:
            context_parts.append("\n최근 대화:")
            for turn in history[-6:]:  # 최근 3턴 (사용자 + AI 쌍)
                if hasattr(turn, 'speaker'):  # Turn dataclass
                    speaker = turn.speaker
                    text = turn.text if turn.text else ""
                else:  # dict
                    speaker = turn.get("speaker", "")
                    text = turn.get("text", "")
                context_parts.append(f"{speaker}: {text}")

        return "\n".join(context_parts)


# ============================================
# PronunciationEvaluatorImpl
# ============================================

class PronunciationEvaluatorImpl:
    """발음 평가를 담당하는 클래스 (점수 기반 피드백 생성)

    Azure Speech Service에서 점수를 받고,
    LLM을 사용하여 피드백 텍스트를 생성합니다.
    책임: 발음 평가 (점수 + 피드백)
    """

    def __init__(
        self,
        azure_service,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        발음 평가기 초기화

        Args:
            azure_service: Azure Speech Service 인스턴스
            api_key: OpenAI API 키
            model_name: 모델명
            temperature: 창의성 레벨 (낮을수록 일관성)
        """
        self.azure_service = azure_service
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature
        )

        logger.info(f"PronunciationEvaluatorImpl initialized with OpenAI provider")

    async def evaluate_pronunciation(
        self,
        audio_data: Optional[bytes],
        user_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        발음 평가 (Azure 점수 + LLM 피드백)

        Args:
            audio_data: WAV 형식 오디오 데이터
            user_text: 사용자 발화 텍스트

        Returns:
            {
                "success": bool,
                "score": int (0-100),
                "feedback": str,
                "pronunciation_score": float,
                "accuracy_score": float,
                "fluency_score": float,
                "completeness_score": float,
                "words": [...]
            }
            또는 None
        """
        if not audio_data:
            logger.warning("No audio data provided for pronunciation evaluation")
            return None

        try:
            logger.info("🔵 [발음 평가] Azure Speech 호출 중...")

            # Step 1: Azure에서 점수 수집
            azure_result = await self.azure_service.assess_pronunciation(
                audio_data=audio_data,
                reference_text=user_text,
                language="en-US"
            )

            if not azure_result or not azure_result.get("success"):
                logger.warning(f"Azure pronunciation assessment failed: {azure_result.get('error_message')}")
                return None

            pronunciation_score = azure_result.get("pronunciation_score", 0)
            accuracy_score = azure_result.get("accuracy_score", 0)
            fluency_score = azure_result.get("fluency_score", 0)
            completeness_score = azure_result.get("completeness_score", 0)
            words = azure_result.get("words", [])

            logger.info(f"✅ [Azure 발음 평가 완료] 점수: {pronunciation_score}")

            # Step 2: LLM으로 피드백 생성
            error_words = [
                w.get("word", "")
                for w in words
                if w.get("error_type") and w.get("accuracy_score", 100) < 80
            ]
            error_words_str = ", ".join(error_words[:5]) if error_words else "None"

            prompt = PRONUNCIATION_FEEDBACK_PROMPT.format(
                user_text=user_text,
                pronunciation_score=pronunciation_score,
                accuracy_score=accuracy_score,
                fluency_score=fluency_score,
                completeness_score=completeness_score,
                error_words=error_words_str
            )

            logger.info("🔵 [발음 피드백] LLM 호출 중...")

            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)

            # JSON 객체 추출 시도
            result = extract_json_from_response(response_text)
            if result:
                feedback_score = normalize_score(result.get("score"))
                if feedback_score is None:
                    logger.warning("Pronunciation feedback generation returned no score")
                    # Fallback: Azure 점수 사용
                    feedback_score = int(pronunciation_score)

                feedback_text = result.get("feedback", "")
                logger.info(f"✅ [발음 피드백 생성 완료] {feedback_score}점")

                return {
                    "success": True,
                    "score": feedback_score,
                    "feedback": feedback_text,
                    "pronunciation_score": pronunciation_score,
                    "accuracy_score": accuracy_score,
                    "fluency_score": fluency_score,
                    "completeness_score": completeness_score,
                    "words": words
                }
            else:
                # 피드백만 추출 시도
                logger.info(f"✅ [발음 피드백 생성 완료 (파싱)] {int(pronunciation_score)}점")
                return {
                    "success": True,
                    "score": int(pronunciation_score),
                    "feedback": response_text,
                    "pronunciation_score": pronunciation_score,
                    "accuracy_score": accuracy_score,
                    "fluency_score": fluency_score,
                    "completeness_score": completeness_score,
                    "words": words
                }

        except Exception as e:
            logger.error(f"Pronunciation evaluation failed: {e}", exc_info=True)
            return None

    async def evaluate_pronunciation_stream(
        self,
        audio_data: Optional[bytes],
        user_text: str
    ):
        """
        발음 평가 피드백 생성 (토큰 단위 스트리밍, Azure 점수 포함)

        Args:
            audio_data: WAV 형식 오디오 데이터
            user_text: 사용자 발화 텍스트

        Yields:
            각 토큰 문자열
        """
        if not audio_data:
            logger.warning("No audio data provided for pronunciation evaluation streaming")
            yield ""
            return

        try:
            logger.info("🔵 [발음 평가 스트리밍] Azure Speech 호출 중...")

            # Step 1: Azure에서 점수 수집
            azure_result = await self.azure_service.assess_pronunciation(
                audio_data=audio_data,
                reference_text=user_text,
                language="en-US"
            )

            if not azure_result or not azure_result.get("success"):
                logger.warning(f"Azure pronunciation assessment failed: {azure_result.get('error_message')}")
                yield ""
                return

            pronunciation_score = azure_result.get("pronunciation_score", 0)
            accuracy_score = azure_result.get("accuracy_score", 0)
            fluency_score = azure_result.get("fluency_score", 0)
            completeness_score = azure_result.get("completeness_score", 0)
            words = azure_result.get("words", [])

            logger.info(f"✅ [Azure 발음 평가 완료] 점수: {pronunciation_score}")

            # Step 2: LLM으로 피드백 생성 (스트리밍)
            error_words = [
                w.get("word", "")
                for w in words
                if w.get("error_type") and w.get("accuracy_score", 100) < 80
            ]
            error_words_str = ", ".join(error_words[:5]) if error_words else "None"

            prompt = PRONUNCIATION_FEEDBACK_PROMPT.format(
                user_text=user_text,
                pronunciation_score=pronunciation_score,
                accuracy_score=accuracy_score,
                fluency_score=fluency_score,
                completeness_score=completeness_score,
                error_words=error_words_str
            )

            logger.info("🔵 [발음 피드백 스트리밍] LLM 스트리밍 중...")

            async for token in self.llm.stream(prompt):
                if token:  # 빈 토큰 제외
                    yield token
                    logger.debug(f"📤 [발음 피드백 토큰] {repr(token)}")

        except Exception as e:
            logger.error(f"Pronunciation evaluation streaming failed: {e}", exc_info=True)
            yield ""  # Fallback: 빈 응답


# ============================================
# FeedbackJudgeImpl
# ============================================

class FeedbackJudgeImpl:
    """피드백 판단만 담당하는 클래스

    평가 결과를 바탕으로 교정 필요 여부를 판단합니다.
    책임: 교정 필요 여부 판단만
    """

    def judge_correction_needed(
        self,
        pronunciation_score: Optional[float],
        grammar_score: Optional[float],
        relevance_score: Optional[float],
        retry_count: int
    ) -> tuple[bool, str]:
        """
        교정 필요 여부 판단

        Args:
            pronunciation_score: 발음 점수 (0-100 또는 None - 평가 실패)
            grammar_score: 문법 점수 (0-100 또는 None - 평가 실패)
            relevance_score: 맥락 점수 (0-100 또는 None - 평가 실패)
            retry_count: 현재 재시도 횟수

        Returns:
            (needs_correction: bool, primary_issue: str)
            primary_issue: "pronunciation", "grammar", "relevance", "max_retries_exceeded", "evaluation_failed", "none"
        """
        # 평가 실패 시: 모든 점수가 None이면 교정 불필요 (feedback 없이 진행)
        if pronunciation_score is None and grammar_score is None and relevance_score is None:
            logger.warning("All evaluations failed, proceeding without correction")
            return False, "evaluation_failed"

        # 재시도 초과 시 강제 통과
        if retry_count >= settings.FEEDBACK_MAX_RETRY_PER_QUESTION:
            logger.info(f"Max retries exceeded ({retry_count}), forcing pass")
            return False, "max_retries_exceeded"

        # 기준값
        pron_threshold = settings.FEEDBACK_PRONUNCIATION_THRESHOLD
        gram_threshold = settings.FEEDBACK_GRAMMAR_THRESHOLD
        relev_threshold = settings.FEEDBACK_RELEVANCE_THRESHOLD

        # 교정 필요 조건 판단 (None은 스킵)
        primary_issue = None

        if pronunciation_score is not None and pronunciation_score < pron_threshold and pronunciation_score > 0:
            primary_issue = "pronunciation"
        elif grammar_score is not None and grammar_score < gram_threshold:
            primary_issue = "grammar"
        elif relevance_score is not None and relevance_score < relev_threshold:
            primary_issue = "relevance"

        needs_correction = primary_issue is not None
        logger.info(
            f"Correction judgment: needs={needs_correction}, "
            f"issue={primary_issue or 'none'}"
        )
        return needs_correction, primary_issue or "none"


# ============================================
# FeedbackOrchestratorImpl
# ============================================

class FeedbackOrchestratorImpl:
    """피드백 조율만 담당하는 클래스

    전체 평가 프로세스를 조율합니다.
    책임: 평가 프로세스 조율만
    """

    def __init__(
        self,
        grammar_evaluator: GrammarEvaluator,
        relevance_evaluator: RelevanceEvaluator,
        pronunciation_evaluator: PronunciationEvaluator,
        feedback_judge: FeedbackJudge,
        azure_tracker=None
    ):
        """
        피드백 조율기 초기화

        Args:
            grammar_evaluator: 문법 평가 구현체
            relevance_evaluator: 맥락 평가 구현체
            pronunciation_evaluator: 발음 평가 구현체 (Azure)
            feedback_judge: 피드백 판단 구현체
            azure_tracker: Azure 사용량 추적 (선택사항)
        """
        self.grammar_evaluator = grammar_evaluator
        self.relevance_evaluator = relevance_evaluator
        self.pronunciation_evaluator = pronunciation_evaluator
        self.feedback_judge = feedback_judge
        self.azure_tracker = azure_tracker

        # 피드백 번역용 LLM (grammar_evaluator의 llm 사용)
        self.llm = grammar_evaluator.llm if hasattr(grammar_evaluator, 'llm') else None

        logger.info("FeedbackOrchestratorImpl initialized")

    async def evaluate_response_fast(
        self,
        user_text: str,
        audio_data: Optional[bytes],
        conversation_history: list,
        scenario_context: dict,
        retry_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        빠른 응답 평가 (병렬 처리)

        Args:
            user_text: 사용자 STT 결과 텍스트
            audio_data: 사용자 오디오 데이터 (선택사항)
            conversation_history: 대화 히스토리
            scenario_context: 시나리오 컨텍스트
            retry_count: 현재 질문 재시도 횟수

        Returns:
            {
                "needs_correction": bool,
                "primary_issue": str,
                "scores": {
                    "pronunciation_score": int | None,
                    "grammar_score": int | None,
                    "relevance_score": int | None,
                    "overall_score": int | None
                },
                "feedback_text": str,
                "retry_count": int
            }
            또는 None
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"🎯 [피드백 평가 시작] 사용자 텍스트: '{user_text}'")

            # 병렬 평가
            eval_start = time.time()
            logger.info("📊 [병렬 평가 시작] 발음, 문법, 맥락 평가 중...")

            if audio_data:
                pronunciation, grammar, relevance = await asyncio.gather(
                    self.pronunciation_evaluator.evaluate_pronunciation(audio_data, user_text),
                    self.grammar_evaluator.evaluate_grammar(user_text),
                    self.relevance_evaluator.evaluate_relevance(
                        user_text, conversation_history, scenario_context
                    )
                )
            else:
                logger.debug("Skipping pronunciation evaluation (no audio data)")
                grammar, relevance = await asyncio.gather(
                    self.grammar_evaluator.evaluate_grammar(user_text),
                    self.relevance_evaluator.evaluate_relevance(
                        user_text, conversation_history, scenario_context
                    )
                )
                pronunciation = None

            eval_time = time.time() - eval_start
            logger.info(f"✅ [병렬 평가 완료] 소요 시간: {eval_time:.2f}초")

            # 평가 결과 안전 처리
            pronunciation_score = normalize_score(pronunciation.get("score") if pronunciation else None)
            grammar_score = normalize_score(grammar.get("score") if grammar else None)
            relevance_score = normalize_score(relevance.get("score") if relevance else None)

            logger.info(f"  - 발음: {pronunciation_score if pronunciation_score is not None else '?'}점")
            logger.info(f"  - 문법: {grammar_score if grammar_score is not None else '?'}점")
            logger.info(f"  - 맥락: {relevance_score if relevance_score is not None else '?'}점")

            # 종합 점수 (성공한 항목만으로 평균 계산)
            scores_list = [s for s in [pronunciation_score, grammar_score, relevance_score] if s is not None]
            if scores_list:
                overall_score = int(sum(scores_list) / len(scores_list))
            else:
                overall_score = None  # 모든 평가 실패

            # 교정 필요 여부 판단 (None 점수는 명시적으로 전달)
            needs_correction, primary_issue = self.feedback_judge.judge_correction_needed(
                pronunciation_score,
                grammar_score,
                relevance_score,
                retry_count
            )


            total_time = time.time() - start_time
            logger.info(f"🎉 [피드백 평가 전체 완료] 총 소요 시간: {total_time:.2f}초")
            logger.info(f"   종합 점수: {overall_score}점 | 교정 필요: {needs_correction}")

            # 피드백 섹션 스트리밍은 _common.py에서 별도로 처리
            # 여기서는 점수와 교정 판단 정보만 반환
            return {
                "needs_correction": needs_correction,
                "primary_issue": primary_issue,
                "scores": {
                    "pronunciation_score": int(pronunciation_score) if pronunciation_score is not None else None,
                    "grammar_score": int(grammar_score) if grammar_score is not None else None,
                    "relevance_score": int(relevance_score) if relevance_score is not None else None,
                    "overall_score": int(overall_score) if overall_score is not None else None
                },
                "pronunciation": pronunciation,
                "grammar": grammar,
                "relevance": relevance,
                "pronunciation_score": pronunciation_score,
                "grammar_score": grammar_score,
                "relevance_score": relevance_score,
                "retry_count": retry_count
            }

        except Exception as e:
            logger.error(f"Response evaluation failed: {e}", exc_info=True)
            raise

    async def _generate_feedback_text(
        self,
        user_text: str,
        pronunciation: Optional[Dict],
        grammar: Optional[Dict],
        relevance: Optional[Dict],
        needs_correction: bool,
        max_feedback_length: int = 500
    ) -> str:
        """피드백 텍스트 생성 (None 평가 결과 안전 처리)

        Args:
            max_feedback_length: 최대 피드백 글자수 (기본 500자)
        """
        try:
            feedback_parts = []

            # 발음 피드백 (None 체크)
            if pronunciation and pronunciation.get("feedback"):
                feedback_parts.append(f"발음: {pronunciation['feedback']}")

            # 문법 피드백 (None 체크)
            if grammar and grammar.get("feedback"):
                feedback_parts.append(f"문법: {grammar['feedback']}")

            # 맥락 피드백 (None 체크)
            if relevance and relevance.get("feedback"):
                feedback_parts.append(f"맥락: {relevance['feedback']}")

            # 최종 메시지
            if needs_correction:
                feedback_text = " | ".join(feedback_parts)
                feedback_text += f"다시 한 번 시도해주세요."
            else:
                feedback_text = "좋습니다! 계속 진행하겠습니다."

            # 글자수 제한 (최대 max_feedback_length)
            if len(feedback_text) > max_feedback_length:
                # 마지막 완전한 문장까지만 자르기
                truncated = feedback_text[:max_feedback_length]
                last_period = truncated.rfind('.')
                if last_period > 0:
                    feedback_text = truncated[:last_period + 1]
                else:
                    # 마침표가 없으면 마지막 완전한 단어까지
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        feedback_text = truncated[:last_space] + "..."
                    else:
                        feedback_text = truncated + "..."
                logger.info(f"Feedback truncated to {len(feedback_text)} characters")

            return feedback_text

        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return "평가를 완료했습니다."

    async def _build_feedback_sections_stream(
        self,
        user_text: str,
        conversation_history: list,
        scenario_context: dict,
        pronunciation: Optional[Dict],
        grammar: Optional[Dict],
        relevance: Optional[Dict],
        pronunciation_score: Optional[int],
        grammar_score: Optional[int],
        relevance_score: Optional[int],
        audio_data: Optional[bytes] = None,
    ):
        """
        피드백 섹션(영문 토큰 + 한글 섹션) 스트리밍 생성

        ✅ 영문: 실시간 LLM 스트리밍으로 토큰 단위 전송
        ✅ 한글: 섹션 완성 후 한 번에 번역하여 전송

        Args:
            user_text: 사용자 발화 텍스트 (평가기에 전달)
            conversation_history: 대화 히스토리 (relevance 평가용)
            scenario_context: 시나리오 컨텍스트 (relevance 평가용)
            pronunciation: 발음 평가 결과
            grammar: 문법 평가 결과
            relevance: 맥락 평가 결과
            pronunciation_score: 발음 점수
            grammar_score: 문법 점수
            relevance_score: 맥락 점수
            audio_data: 오디오 데이터 (발음 평가용)

        Yields:
            영문 토큰: {
                "type": "feedback_token",
                "section_type": "pronunciation|grammar|relevance",
                "token": "The"
            }
            한글 섹션: {
                "type": "feedback_section",
                "section_type": "pronunciation|grammar|relevance",
                "feedback_en": "The response...",
                "feedback_ko": "응답이...",
                "score": 75
            }
        """
        section_configs = [
            {
                "section_type": "pronunciation",
                "evaluation": pronunciation,
                "score": pronunciation_score,
                "fallback": "Pronunciation feedback is unavailable.",
                "evaluator": self.pronunciation_evaluator,
                "user_text": user_text,
                "audio_data": audio_data,
                "conversation_history": None,
                "scenario_context": None,
            },
            {
                "section_type": "grammar",
                "evaluation": grammar,
                "score": grammar_score,
                "fallback": "Grammar feedback is unavailable.",
                "evaluator": self.grammar_evaluator,
                "user_text": user_text,
                "audio_data": None,
                "conversation_history": None,
                "scenario_context": None,
            },
            {
                "section_type": "relevance",
                "evaluation": relevance,
                "score": relevance_score,
                "fallback": "Relevance feedback is unavailable.",
                "evaluator": self.relevance_evaluator,
                "user_text": user_text,
                "audio_data": None,
                "conversation_history": conversation_history,
                "scenario_context": scenario_context,
            },
        ]

        try:
            # 각 섹션 순차 처리
            for config in section_configs:
                section_type = config["section_type"]
                logger.info(f"🟢 [{section_type}] 영문 피드백 실시간 스트리밍 중...")

                # Step 1: 실시간 LLM 스트리밍으로 영문 피드백 생성
                english_tokens = []
                async for token in self._stream_section_feedback_en(config):
                    english_tokens.append(token)
                    # 영문 토큰 즉시 yield
                    yield {
                        "type": "feedback_token",
                        "section_type": section_type,
                        "token": token
                    }

                # 영문 전체 텍스트 조합
                english_feedback = "".join(english_tokens).strip()
                if not english_feedback:
                    english_feedback = config["fallback"]

                logger.info(f"✅ [{section_type}] 영문 완료: {english_feedback[:60]}...")

                # Step 2: 영문이 완성되면 한글로 번역
                logger.info(f"🟢 [{section_type}] 한글 번역 중...")
                korean_feedback = await self._translate_feedback(english_feedback)
                korean_feedback = korean_feedback or english_feedback

                logger.info(f"✅ [{section_type}] 한글 완료: {korean_feedback[:60]}...")

                # Step 3: 완성된 섹션 (영문 + 한글) 한 번에 yield
                section_score = config["score"]
                logger.info(f"🔢 [{section_type}] 점수 확인: {section_score} (type={type(section_score).__name__})")

                yield {
                    "type": "feedback_section",
                    "section_type": section_type,
                    "feedback_en": english_feedback,
                    "feedback_ko": korean_feedback,
                    "score": section_score
                }

        except Exception as e:
            logger.error(f"Failed to stream feedback sections: {e}", exc_info=True)

    async def _stream_section_feedback_en(self, config: Dict):
        """
        각 섹션의 영문 피드백을 실시간 LLM 스트리밍으로 생성

        ✅ 변경사항:
        - 이미 평가된 피드백을 재사용하지 않고
        - evaluator의 스트리밍 메서드를 직접 호출하여 실시간 토큰 생성

        Args:
            config: 섹션 설정 (section_type, evaluation, score, evaluator 포함)

        Yields:
            각 토큰 문자열
        """
        section_type = config["section_type"]
        evaluator = config["evaluator"]
        user_text = config.get("user_text", "")

        try:
            logger.info(f"🟢 [{section_type}] evaluator 스트리밍 메서드 호출...")

            # 각 섹션별로 evaluator의 스트리밍 메서드 직접 호출
            if section_type == "pronunciation":
                audio_data = config.get("audio_data")
                if not audio_data:
                    logger.debug(f"No audio data for pronunciation, using fallback")
                    for token in config["fallback"].split():
                        yield token + " "
                    return

                async for token in evaluator.evaluate_pronunciation_stream(audio_data, user_text):
                    if token:
                        yield token

            elif section_type == "grammar":
                async for token in evaluator.evaluate_grammar_stream(user_text):
                    if token:
                        yield token

            elif section_type == "relevance":
                conversation_history = config.get("conversation_history", [])
                scenario_context = config.get("scenario_context", {})
                async for token in evaluator.evaluate_relevance_stream(
                    user_text, conversation_history, scenario_context
                ):
                    if token:
                        yield token

        except Exception as e:
            logger.error(f"Failed to stream {section_type} feedback: {e}", exc_info=True)
            # Fallback: 오류 발생 시 fallback 텍스트 사용
            for token in config["fallback"].split():
                yield token + " "

    async def _translate_feedback(self, feedback_en: str) -> Optional[str]:
        """LLM을 사용하여 영문 피드백을 한글로 번역"""
        try:
            from app.roleplaying.prompts.constants import FEEDBACK_BILINGUAL_PROMPT

            prompt = FEEDBACK_BILINGUAL_PROMPT.format(english_feedback=feedback_en)
            response = await self.llm.invoke(prompt)

            # JSON에서 korean_feedback 추출 시도
            try:
                json_match = re.search(r'\{[^{}]*"korean_feedback"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    korean_feedback = parsed.get("korean_feedback")
                    if korean_feedback and korean_feedback.strip():
                        logger.debug(f"✅ [번역 완료] {feedback_en[:30]}... → {korean_feedback[:30]}...")
                        return korean_feedback
            except Exception as e:
                logger.warning(f"Failed to parse Korean feedback translation: {e}")

            # JSON 파싱 실패 시 전체 응답 사용 (간단한 번역 결과일 수 있음)
            if response and response.strip():
                logger.debug(f"✅ [번역 완료 (파싱)] {feedback_en[:30]}... → {response[:30]}...")
                return response.strip()

            return None

        except Exception as e:
            logger.error(f"Feedback translation failed: {e}")
            return None

    def _build_single_section(
        self,
        section_type: str,
        evaluation: Optional[Dict[str, Any]],
        score: Optional[int],
        fallback: str
    ) -> Dict[str, Any]:
        """개별 섹션 포맷 (영문만 생성, 한글은 비동기로 추가)"""
        feedback_text = ""
        if evaluation and isinstance(evaluation, dict):
            feedback_text = evaluation.get("feedback") or ""
        feedback_text = feedback_text.strip() or fallback

        normalized_score = int(score) if isinstance(score, (int, float)) else None

        return {
            "type": section_type,
            "feedback_en": feedback_text,
            "feedback_ko": "",  # 이후 async 메서드에서 채워짐
            "score": normalized_score,
        }
