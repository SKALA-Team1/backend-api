"""
Feedback Service Refactored (SOLID 준수)
==========================================
기존 FeedbackAgentService를 4개의 단일 책임 클래스로 분리했습니다.

변경 이유:
- SRP 위반: 기존 FeedbackAgentService는 300+ 라인, 평가와 판단 혼재
- 3가지 책임 혼재: 문법 평가, 맥락 평가, 피드백 판단, 조율
- 변경 영향도 증가, 테스트 어려움

솔루션:
- 각 책임을 별도 클래스로 분리
- 같은 인터페이스로 통합 (GrammarEvaluator, RelevanceEvaluator 등)
- 테스트 가능, 재사용 가능한 구조

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
from app.roleplaying.services.llm_providers import create_llm_provider
from app.roleplaying.services.interfaces import (
    PronunciationEvaluator,
    GrammarEvaluator,
    RelevanceEvaluator,
    FeedbackJudge,
    FeedbackOrchestrator
)
from app.roleplaying.prompts.constants import (
    GRAMMAR_EVALUATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
)
from app.roleplaying.services.utils import (
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
        provider: str = None,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        문법 평가기 초기화

        Args:
            provider: LLM 프로바이더 ("openai" 또는 "ollama")
            api_key: OpenAI API 키 (OpenAI 사용 시)
            model_name: 모델명
            temperature: 창의성 레벨 (낮을수록 일관성 있음)
        """
        self.provider = provider or settings.FEEDBACK_LLM_PROVIDER
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.provider == "openai" else "ollama",
            api_key=self.api_key if self.provider == "openai" else None,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL if self.provider != "openai" else None,
            temperature=self.temperature
        )

        logger.info(f"GrammarEvaluatorImpl initialized with {self.provider} provider")

    async def evaluate_grammar(self, user_text: str) -> Dict[str, Any]:
        """
        문법 평가

        Args:
            user_text: 사용자 발화 텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str
            }
        """
        prompt = GRAMMAR_EVALUATION_PROMPT.format(user_text=user_text)

        try:
            logger.info("🟢 [문법 평가] LLM 호출 중...")

            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)

            # JSON 객체 추출 시도
            result = extract_json_from_response(response_text)
            if result:
                score = normalize_score(result.get("score", 70))
                logger.info(f"✅ [문법 평가 완료] {score}점")
                return {
                    "score": score,
                    "feedback": result.get("feedback", "")
                }
            else:
                # 점수만 추출
                score = normalize_score_from_string(response_text)
                logger.info(f"✅ [문법 평가 완료 (파싱)] {score}점")
                return {"score": score, "feedback": response_text[:100]}

        except Exception as e:
            logger.error(f"Grammar evaluation failed: {e}")
            return {"score": 70, "feedback": "문법 검사 중 오류 발생"}


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
        provider: str = None,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        맥락 평가기 초기화

        Args:
            provider: LLM 프로바이더
            api_key: OpenAI API 키 (OpenAI 사용 시)
            model_name: 모델명
            temperature: 창의성 레벨
        """
        self.provider = provider or settings.FEEDBACK_LLM_PROVIDER
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.provider == "openai" else "ollama",
            api_key=self.api_key if self.provider == "openai" else None,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL if self.provider != "openai" else None,
            temperature=self.temperature
        )

        logger.info(f"RelevanceEvaluatorImpl initialized with {self.provider} provider")

    async def evaluate_relevance(
        self,
        user_text: str,
        conversation_history: list,
        scenario_context: dict
    ) -> Dict[str, Any]:
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

            # JSON 객체 추출 시도
            result = extract_json_from_response(response_text)
            if result:
                score = normalize_score(result.get("score", 70))
                logger.info(f"✅ [맥락 평가 완료] {score}점")
                return {
                    "score": score,
                    "feedback": result.get("feedback", "")
                }
            else:
                # 점수만 추출
                score = normalize_score_from_string(response_text)
                logger.info(f"✅ [맥락 평가 완료 (파싱)] {score}점")
                return {"score": score, "feedback": response_text[:100]}

        except Exception as e:
            logger.error(f"Relevance evaluation failed: {e}")
            return {"score": 70, "feedback": "맥락 평가 중 오류 발생"}

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
# FeedbackJudgeImpl
# ============================================

class FeedbackJudgeImpl:
    """피드백 판단만 담당하는 클래스

    평가 결과를 바탕으로 교정 필요 여부를 판단합니다.
    책임: 교정 필요 여부 판단만
    """

    def judge_correction_needed(
        self,
        pronunciation_score: float,
        grammar_score: float,
        relevance_score: float,
        retry_count: int
    ) -> tuple[bool, str]:
        """
        교정 필요 여부 판단

        Args:
            pronunciation_score: 발음 점수 (0-100)
            grammar_score: 문법 점수 (0-100)
            relevance_score: 맥락 점수 (0-100)
            retry_count: 현재 재시도 횟수

        Returns:
            (needs_correction: bool, primary_issue: str)
            primary_issue: "pronunciation", "grammar", "relevance", "max_retries_exceeded", "none"
        """
        # 재시도 초과 시 강제 통과
        if retry_count >= settings.FEEDBACK_MAX_RETRY_PER_QUESTION:
            logger.info(f"Max retries exceeded ({retry_count}), forcing pass")
            return False, "max_retries_exceeded"

        # 기준값
        pron_threshold = settings.FEEDBACK_PRONUNCIATION_THRESHOLD
        gram_threshold = settings.FEEDBACK_GRAMMAR_THRESHOLD
        relev_threshold = settings.FEEDBACK_RELEVANCE_THRESHOLD

        # 교정 필요 조건 판단
        primary_issue = None

        if pronunciation_score < pron_threshold and pronunciation_score > 0:
            primary_issue = "pronunciation"
        elif grammar_score < gram_threshold:
            primary_issue = "grammar"
        elif relevance_score < relev_threshold:
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

        logger.info("FeedbackOrchestratorImpl initialized")

    async def evaluate_response_fast(
        self,
        user_text: str,
        audio_data: Optional[bytes],
        conversation_history: list,
        scenario_context: dict,
        retry_count: int
    ) -> Dict[str, Any]:
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
                    "pronunciation_score": int,
                    "grammar_score": int,
                    "relevance_score": int,
                    "overall_score": int
                },
                "feedback_text": str,
                "retry_count": int
            }
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"🎯 [피드백 평가 시작] 사용자 텍스트: '{user_text}'")

            # 병렬 평가
            eval_start = time.time()
            logger.info("📊 [병렬 평가 시작] 발음, 문법, 맥락 평가 중...")

            pronunciation, grammar, relevance = await asyncio.gather(
                self.pronunciation_evaluator.evaluate_pronunciation(audio_data, user_text),
                self.grammar_evaluator.evaluate_grammar(user_text),
                self.relevance_evaluator.evaluate_relevance(
                    user_text, conversation_history, scenario_context
                )
            )

            eval_time = time.time() - eval_start
            logger.info(f"✅ [병렬 평가 완료] 소요 시간: {eval_time:.2f}초")
            logger.info(f"  - 발음: {pronunciation.get('score', '?')}점")
            logger.info(f"  - 문법: {grammar.get('score', '?')}점")
            logger.info(f"  - 맥락: {relevance.get('score', '?')}점")

            # 평가 점수 정규화 (0-100)
            pronunciation_score = normalize_score(pronunciation.get("score", 70))
            grammar_score = normalize_score(grammar.get("score", 70))
            relevance_score = normalize_score(relevance.get("score", 70))

            # 종합 점수 (평균)
            overall_score = int((pronunciation_score + grammar_score + relevance_score) / 3)

            # 교정 필요 여부 판단
            needs_correction, primary_issue = self.feedback_judge.judge_correction_needed(
                pronunciation_score,
                grammar_score,
                relevance_score,
                retry_count
            )

            # 피드백 텍스트 생성
            feedback_start = time.time()
            feedback_text = await self._generate_feedback_text(
                user_text,
                pronunciation,
                grammar,
                relevance,
                needs_correction
            )
            feedback_time = time.time() - feedback_start
            logger.info(f"💬 [피드백 텍스트 생성 완료] 소요 시간: {feedback_time:.2f}초")

            total_time = time.time() - start_time
            logger.info(f"🎉 [피드백 평가 전체 완료] 총 소요 시간: {total_time:.2f}초")
            logger.info(f"   종합 점수: {overall_score}점 | 교정 필요: {needs_correction}")

            return {
                "needs_correction": needs_correction,
                "primary_issue": primary_issue,
                "scores": {
                    "pronunciation_score": int(pronunciation_score),
                    "grammar_score": int(grammar_score),
                    "relevance_score": int(relevance_score),
                    "overall_score": overall_score
                },
                "feedback_text": feedback_text,
                "retry_count": retry_count
            }

        except Exception as e:
            logger.error(f"Response evaluation failed: {e}", exc_info=True)
            # Fallback: 교정 없이 진행
            return {
                "needs_correction": False,
                "primary_issue": "error",
                "scores": {
                    "pronunciation_score": 70,
                    "grammar_score": 70,
                    "relevance_score": 70,
                    "overall_score": 70
                },
                "feedback_text": "평가 중 오류가 발생했습니다. 다음 질문으로 진행합니다.",
                "retry_count": retry_count
            }

    async def _generate_feedback_text(
        self,
        user_text: str,
        pronunciation: Dict,
        grammar: Dict,
        relevance: Dict,
        needs_correction: bool
    ) -> str:
        """피드백 텍스트 생성"""
        try:
            feedback_parts = []

            # 발음 피드백
            if pronunciation.get("feedback"):
                feedback_parts.append(f"발음: {pronunciation['feedback']}")

            # 문법 피드백
            if grammar.get("feedback"):
                feedback_parts.append(f"문법: {grammar['feedback']}")

            # 맥락 피드백
            if relevance.get("feedback"):
                feedback_parts.append(f"맥락: {relevance['feedback']}")

            # 최종 메시지
            if needs_correction:
                feedback_text = " | ".join(feedback_parts)
                feedback_text += "\n다시 한 번 시도해주세요."
            else:
                feedback_text = "좋습니다! 계속 진행하겠습니다."

            return feedback_text

        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return "평가를 완료했습니다."
