"""
Feedback Service Dependencies
(PronunciationEvaluator, GrammarEvaluator, RelevanceEvaluator, FeedbackJudge, FeedbackOrchestrator, AzureUsageTracker)
==================================================================================================================

사용자 발언 평가 및 피드백 생성 서비스 의존성 주입 (Dependency Injection)

주요 서비스:
    - PronunciationEvaluator: Azure Speech Services 기반 발음 평가
    - GrammarEvaluator: LLM 기반 문법 평가
    - RelevanceEvaluator: LLM 기반 맥락 관련성 평가
    - FeedbackJudge: 평가 결과 판단 (우선순위 결정)
    - FeedbackOrchestrator: 모든 평가 조율 및 통합 (최종 피드백 생성)
    - AzureUsageTracker: Azure API 사용량 추적 (비용 관리)

설계:
    - 평가 서비스들은 싱글톤 (@lru_cache)
    - FeedbackOrchestrator가 모든 평가기 조합
    - Azure 서비스는 별도 추적 (비용 최적화)
    - LLM 평가는 설정값으로 공급자 선택 가능
"""

from functools import lru_cache
from typing import Annotated, TYPE_CHECKING

from fastapi import Depends
from app.config import settings

if TYPE_CHECKING:
    from app.roleplaying.services.service_interfaces import (
        PronunciationEvaluator,
        GrammarEvaluator,
        RelevanceEvaluator,
        FeedbackJudge,
        FeedbackOrchestrator,
    )


# ============================================
# Feedback Service Factory Functions
# ============================================

@lru_cache(maxsize=1)
def get_pronunciation_evaluator() -> "PronunciationEvaluator":
    """발음 평가기 의존성 주입

    역할:
        - Azure Speech Services API로 점수 수집
        - LLM으로 점수 기반 피드백 생성
        - 발음 평가 (점수 + 피드백)

    Returns:
        PronunciationEvaluator 인스턴스 (싱글톤)

    Note:
        Azure Speech Services + OpenAI LLM 조합
    """
    from app.roleplaying.services.feedback.azure_speech_service import AzureSpeechService
    from app.roleplaying.services.feedback.feedback_service import PronunciationEvaluatorImpl

    azure_service = AzureSpeechService()

    return PronunciationEvaluatorImpl(
        azure_service=azure_service,
        provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_grammar_evaluator() -> "GrammarEvaluator":
    """문법 평가기 의존성 주입

    역할:
        - 사용자 발언의 문법 검토
        - 문법 오류 식별 및 설명

    Returns:
        GrammarEvaluator 인스턴스 (싱글톤)

    Note:
        LLM 공급자는 settings.FEEDBACK_LLM_PROVIDER로 선택
        (기본: OpenAI, 확장 가능)
    """
    from app.roleplaying.services.feedback.feedback_service import GrammarEvaluatorImpl

    return GrammarEvaluatorImpl(
        provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_relevance_evaluator() -> "RelevanceEvaluator":
    """맥락 평가기 의존성 주입

    역할:
        - 사용자 답변의 맥락 관련성 평가
        - 역할극 상황에 얼마나 적절한지 판단

    Returns:
        RelevanceEvaluator 인스턴스 (싱글톤)

    Note:
        LLM 공급자는 settings.FEEDBACK_LLM_PROVIDER로 선택
    """
    from app.roleplaying.services.feedback.feedback_service import RelevanceEvaluatorImpl

    return RelevanceEvaluatorImpl(
        provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_feedback_judge() -> "FeedbackJudge":
    """피드백 판단기 의존성 주입

    역할:
        - 평가 결과 종합
        - 피드백 생성 필요 여부 판단
        - 우선순위 결정 (발음 > 문법 > 맥락)

    Returns:
        FeedbackJudge 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.feedback.feedback_service import FeedbackJudgeImpl

    return FeedbackJudgeImpl()


@lru_cache(maxsize=1)
def get_feedback_orchestrator() -> "FeedbackOrchestrator":
    """피드백 조율기 의존성 주입

    역할:
        - 모든 평가 서비스를 조합하여 실행
        - 평가 결과 통합 및 우선순위 결정
        - 최종 피드백 생성

    Returns:
        FeedbackOrchestrator 인스턴스 (싱글톤)

    Note:
        내부적으로 다음 서비스들 사용:
        - GrammarEvaluator: 문법 평가
        - RelevanceEvaluator: 맥락 평가
        - PronunciationEvaluator: 발음 평가
        - FeedbackJudge: 판단
        - AzureUsageTracker: 사용량 추적
    """
    from app.roleplaying.services.feedback.feedback_service import FeedbackOrchestratorImpl

    return FeedbackOrchestratorImpl(
        grammar_evaluator=get_grammar_evaluator(),
        relevance_evaluator=get_relevance_evaluator(),
        pronunciation_evaluator=get_pronunciation_evaluator(),
        feedback_judge=get_feedback_judge(),
        azure_tracker=get_azure_usage_tracker()
    )


@lru_cache(maxsize=1)
def get_azure_usage_tracker():
    """Azure 사용량 추적기 의존성 주입

    역할:
        - Azure Speech Services API 호출 추적
        - 비용 계산 및 모니터링
        - 사용량 제한 관리

    Returns:
        AzureUsageTracker 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.utils.azure_usage_tracker import AzureUsageTracker

    return AzureUsageTracker()


@lru_cache(maxsize=1)
def get_feedback_decision_agent() -> "FeedbackDecisionAgent":
    """ReAct 기반 피드백 판단 에이전트 의존성 주입

    역할:
        - LLM의 ReAct 패턴을 통한 피드백/질문 판단
        - 평가 결과 + 재시도 상황 종합 분석
        - 사용자 학습 효율성 고려

    Returns:
        FeedbackDecisionAgent 인스턴스 (싱글톤)

    Note:
        - Agent 실패 시 자동으로 기존 FeedbackJudge 로직으로 Fallback
        - Production Safety 보장
    """
    from app.roleplaying.services.feedback.feedback_decision_agent import (
        FeedbackDecisionAgentImpl,
    )

    return FeedbackDecisionAgentImpl(
        feedback_orchestrator=get_feedback_orchestrator(),
        llm_provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3,  # 판단 용 - 낮을수록 일관성 있음
    )


# ============================================
# Type Aliases for FastAPI Depends
# ============================================

PronunciationEvaluatorDep = Annotated[
    "PronunciationEvaluator",
    Depends(get_pronunciation_evaluator)
]
"""발음 평가기 의존성 타입 - Azure Speech Services 기반"""

GrammarEvaluatorDep = Annotated[
    "GrammarEvaluator",
    Depends(get_grammar_evaluator)
]
"""문법 평가기 의존성 타입 - LLM 기반"""

RelevanceEvaluatorDep = Annotated[
    "RelevanceEvaluator",
    Depends(get_relevance_evaluator)
]
"""맥락 평가기 의존성 타입 - LLM 기반 관련성 평가"""

FeedbackJudgeDep = Annotated[
    "FeedbackJudge",
    Depends(get_feedback_judge)
]
"""피드백 판단기 의존성 타입 - 평가 결과 종합"""

FeedbackOrchestratorDep = Annotated[
    "FeedbackOrchestrator",
    Depends(get_feedback_orchestrator)
]
"""피드백 조율기 의존성 타입 - 모든 평가 통합"""

FeedbackDecisionAgentDep = Annotated[
    "FeedbackDecisionAgent",
    Depends(get_feedback_decision_agent)
]
"""ReAct 기반 피드백 판단 에이전트 의존성 타입 - LLM의 ReAct 패턴으로 피드백/질문 판단"""

__all__ = [
    "get_pronunciation_evaluator",
    "get_grammar_evaluator",
    "get_relevance_evaluator",
    "get_feedback_judge",
    "get_feedback_orchestrator",
    "get_azure_usage_tracker",
    "get_feedback_decision_agent",
    "PronunciationEvaluatorDep",
    "GrammarEvaluatorDep",
    "RelevanceEvaluatorDep",
    "FeedbackJudgeDep",
    "FeedbackOrchestratorDep",
    "FeedbackDecisionAgentDep",
]
