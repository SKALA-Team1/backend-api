"""
Dependency Injection Helpers
=============================
FastAPI Depends를 활용한 의존성 주입 헬퍼 함수.

사용 방식:
- FastAPI 라우터에서 함수 파라미터로 타입을 지정하면 자동으로 의존성 주입
- @lru_cache()로 싱글톤 패턴 유지
- 타입 안전성과 테스트 용이성 확보

예시:
    @router.post("/analyze")
    async def analyze(
        request: AnalysisRequest,
        analyzer: ConversationAnalyzerDep
    ):
        result = await analyzer.analyze_situation(...)
"""

from functools import lru_cache
from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

from app.config import settings

if TYPE_CHECKING:
    from app.roleplaying.services.interfaces import (
        ConversationAnalyzer,
        ScenarioGenerator,
        QuestionGenerator,
        AIResponseGenerator,
        PronunciationEvaluator,
        GrammarEvaluator,
        RelevanceEvaluator,
        FeedbackJudge,
        FeedbackOrchestrator,
        SessionRepository,
        ScenarioRepository,
        MessageSummarizer,
        FixedQuestionBuilder,
        ScenarioEnhancer,
    )


# ============================================
# LLM Service Dependencies
# ============================================

@lru_cache(maxsize=1)
def get_conversation_analyzer() -> "ConversationAnalyzer":
    """대화 분석기 의존성 주입

    Returns:
        ConversationAnalyzer 인스턴스 (싱글톤)

    Example:
        @router.post("/analyze")
        async def analyze(
            request: AnalysisRequest,
            analyzer: Annotated[ConversationAnalyzer, Depends(get_conversation_analyzer)]
        ):
            situation = await analyzer.analyze_situation(...)
    """
    from app.roleplaying.services.llm_service_refactored import ConversationAnalyzerImpl

    return ConversationAnalyzerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_scenario_generator() -> "ScenarioGenerator":
    """시나리오 생성기 의존성 주입

    Returns:
        ScenarioGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import ScenarioGeneratorImpl

    return ScenarioGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7
    )


@lru_cache(maxsize=1)
def get_question_generator() -> "QuestionGenerator":
    """질문 생성기 의존성 주입

    Returns:
        QuestionGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import QuestionGeneratorImpl

    return QuestionGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7
    )


@lru_cache(maxsize=1)
def get_ai_response_generator() -> "AIResponseGenerator":
    """AI 응답 생성기 의존성 주입

    Returns:
        AIResponseGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import AIResponseGeneratorImpl

    return AIResponseGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_AI_RESPONSE,
        temperature=0.7
    )


# ============================================
# Repository Dependencies
# ============================================

def get_session_repository() -> "SessionRepository":
    """세션 저장소 의존성 주입

    Returns:
        SessionRepository 인스턴스 (싱글톤은 아님, 매 요청마다 새로 생성)

    Note:
        Redis 연결은 클라이언트 내부에서 관리되며,
        풀링을 통해 효율적으로 관리됩니다.
    """
    from app.roleplaying.services.repositories import RedisSessionRepository

    return RedisSessionRepository(redis_url=settings.REDIS_URL)


def get_scenario_repository() -> "ScenarioRepository":
    """시나리오 저장소 의존성 주입

    Returns:
        ScenarioRepository 인스턴스

    Note:
        DB 세션은 FastAPI Depends(get_db)에서 주입되어야 합니다.
    """
    from app.roleplaying.services.repositories import DatabaseScenarioRepository

    return DatabaseScenarioRepository()


# ============================================
# Session Service Dependencies
# ============================================

def get_ai_tutor_service(
    question_generator: "QuestionGenerator" = Depends(get_question_generator)
):
    """AI 튜터 서비스 의존성 주입

    Returns:
        AITutorService 인스턴스

    Example:
        @router.post("/ask")
        async def ask_question(
            ai_tutor: AITutorServiceDep
        ):
            response, is_fixed = await ai_tutor.generate_reply(session_state, user_text)
    """
    from app.roleplaying.services.ai_tutor_service import AITutorService

    return AITutorService(question_generator=question_generator)


@lru_cache(maxsize=1)
def get_message_summarizer() -> "MessageSummarizer":
    """메시지 요약기 의존성 주입

    Returns:
        MessageSummarizer 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import MessageSummarizerImpl

    return MessageSummarizerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_fixed_question_builder() -> "FixedQuestionBuilder":
    """고정 질문 생성기 의존성 주입

    Returns:
        FixedQuestionBuilder 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import FixedQuestionBuilderImpl

    return FixedQuestionBuilderImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7
    )


def get_slack_scenario_service(
    analyzer: "ConversationAnalyzer" = Depends(get_conversation_analyzer),
    generator: "ScenarioGenerator" = Depends(get_scenario_generator),
    summarizer: "MessageSummarizer" = Depends(get_message_summarizer),
    question_builder: "FixedQuestionBuilder" = Depends(get_fixed_question_builder)
):
    """Slack 시나리오 생성 서비스 의존성 주입

    Returns:
        SlackScenarioService 인스턴스

    Note:
        Phase 3에서 LLMService 제거 완료
        ConversationAnalyzer + ScenarioGenerator 사용
    """
    from app.roleplaying.services.slack_scenario_service import SlackScenarioService

    return SlackScenarioService(
        analyzer=analyzer,
        generator=generator,
        summarizer=summarizer,
        question_builder=question_builder
    )


@lru_cache(maxsize=1)
def get_scenario_enhancer() -> "ScenarioEnhancer":
    """시나리오 강화기 의존성 주입

    Returns:
        ScenarioEnhancer 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import ScenarioEnhancerImpl

    return ScenarioEnhancerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7
    )


def get_prompt_based_scenario_service(
    enhancer: "ScenarioEnhancer" = Depends(get_scenario_enhancer)
):
    """프롬프트 기반 시나리오 생성 서비스 의존성 주입

    Returns:
        PromptBasedScenarioService 인스턴스

    Note:
        Phase 3에서 LLMService 제거 완료
        ScenarioEnhancer 사용
    """
    from app.roleplaying.services.prompt_based_generator_service import PromptBasedScenarioService

    return PromptBasedScenarioService(enhancer=enhancer)


def get_session_service(
    session_repo: "SessionRepository" = Depends(get_session_repository),
    scenario_repo: "ScenarioRepository" = Depends(get_scenario_repository)
):
    """세션 서비스 의존성 주입

    Returns:
        SessionServiceImpl 인스턴스

    Example:
        @router.post("/sessions/setup")
        async def setup_session(
            request: InternalSessionSetupRequest,
            session_service: SessionServiceDep
        ):
            session_id, scenario, expires_at = await session_service.setup_session(...)
    """
    from app.roleplaying.services.session_service_refactored import SessionServiceImpl

    return SessionServiceImpl(
        session_repository=session_repo,
        scenario_repository=scenario_repo
    )


# ============================================
# Feedback Service Dependencies
# ============================================

@lru_cache(maxsize=1)
def get_pronunciation_evaluator() -> "PronunciationEvaluator":
    """발음 평가기 의존성 주입

    Returns:
        PronunciationEvaluator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.azure_speech_service import AzureSpeechService

    return AzureSpeechService()


@lru_cache(maxsize=1)
def get_grammar_evaluator() -> "GrammarEvaluator":
    """문법 평가기 의존성 주입

    Returns:
        GrammarEvaluator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.feedback_service_refactored import GrammarEvaluatorImpl

    return GrammarEvaluatorImpl(
        provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_relevance_evaluator() -> "RelevanceEvaluator":
    """맥락 평가기 의존성 주입

    Returns:
        RelevanceEvaluator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.feedback_service_refactored import RelevanceEvaluatorImpl

    return RelevanceEvaluatorImpl(
        provider=settings.FEEDBACK_LLM_PROVIDER,
        api_key=settings.openai_api_key if settings.FEEDBACK_LLM_PROVIDER == "openai" else None,
        model_name=settings.OPENAI_MODEL_FEEDBACK,
        temperature=0.3
    )


@lru_cache(maxsize=1)
def get_feedback_judge() -> "FeedbackJudge":
    """피드백 판단기 의존성 주입

    Returns:
        FeedbackJudge 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.feedback_service_refactored import FeedbackJudgeImpl

    return FeedbackJudgeImpl()


@lru_cache(maxsize=1)
def get_feedback_orchestrator() -> "FeedbackOrchestrator":
    """피드백 조율기 의존성 주입

    Returns:
        FeedbackOrchestrator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.feedback_service_refactored import FeedbackOrchestratorImpl

    return FeedbackOrchestratorImpl(
        grammar_evaluator=get_grammar_evaluator(),
        relevance_evaluator=get_relevance_evaluator(),
        pronunciation_evaluator=get_pronunciation_evaluator(),
        feedback_judge=get_feedback_judge(),
        azure_tracker=get_azure_usage_tracker()
    )


def get_feedback_agent_service(
    orchestrator: "FeedbackOrchestrator" = Depends(get_feedback_orchestrator)
):
    """피드백 에이전트 서비스 의존성 주입

    Returns:
        FeedbackAgentService 인스턴스

    Note:
        FeedbackAgentService는 아직 레거시 호환성을 위해 유지됩니다.
        새 코드는 get_feedback_orchestrator()를 직접 사용하세요.
    """
    from app.roleplaying.services.feedback_agent_service import FeedbackAgentService

    return FeedbackAgentService(feedback_orchestrator=orchestrator)


@lru_cache(maxsize=1)
def get_azure_usage_tracker():
    """Azure 사용량 추적기 의존성 주입

    Returns:
        AzureUsageTracker 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.azure_usage_tracker import AzureUsageTracker

    return AzureUsageTracker()


# ============================================
# Type Aliases for FastAPI Depends
# ============================================

ConversationAnalyzerDep = Annotated[
    "ConversationAnalyzer",
    Depends(get_conversation_analyzer)
]
"""
대화 분석기 의존성 타입

Usage:
    async def endpoint(analyzer: ConversationAnalyzerDep):
        situation = await analyzer.analyze_situation(...)
"""

ScenarioGeneratorDep = Annotated[
    "ScenarioGenerator",
    Depends(get_scenario_generator)
]
"""시나리오 생성기 의존성 타입"""

QuestionGeneratorDep = Annotated[
    "QuestionGenerator",
    Depends(get_question_generator)
]
"""질문 생성기 의존성 타입"""

AIResponseGeneratorDep = Annotated[
    "AIResponseGenerator",
    Depends(get_ai_response_generator)
]
"""AI 응답 생성기 의존성 타입"""

PronunciationEvaluatorDep = Annotated[
    "PronunciationEvaluator",
    Depends(get_pronunciation_evaluator)
]
"""발음 평가기 의존성 타입"""

GrammarEvaluatorDep = Annotated[
    "GrammarEvaluator",
    Depends(get_grammar_evaluator)
]
"""문법 평가기 의존성 타입"""

RelevanceEvaluatorDep = Annotated[
    "RelevanceEvaluator",
    Depends(get_relevance_evaluator)
]
"""맥락 평가기 의존성 타입"""

FeedbackJudgeDep = Annotated[
    "FeedbackJudge",
    Depends(get_feedback_judge)
]
"""피드백 판단기 의존성 타입"""

FeedbackOrchestratorDep = Annotated[
    "FeedbackOrchestrator",
    Depends(get_feedback_orchestrator)
]
"""피드백 조율기 의존성 타입"""

SessionRepositoryDep = Annotated[
    "SessionRepository",
    Depends(get_session_repository)
]
"""세션 저장소 의존성 타입"""

ScenarioRepositoryDep = Annotated[
    "ScenarioRepository",
    Depends(get_scenario_repository)
]
"""시나리오 저장소 의존성 타입"""

AITutorServiceDep = Annotated[
    "AITutorService",
    Depends(get_ai_tutor_service)
]
"""AI 튜터 서비스 의존성 타입"""

SlackScenarioServiceDep = Annotated[
    "SlackScenarioService",
    Depends(get_slack_scenario_service)
]
"""Slack 시나리오 생성 서비스 의존성 타입"""

PromptBasedScenarioServiceDep = Annotated[
    "PromptBasedScenarioService",
    Depends(get_prompt_based_scenario_service)
]
"""프롬프트 기반 시나리오 생성 서비스 의존성 타입"""

FeedbackAgentServiceDep = Annotated[
    "FeedbackAgentService",
    Depends(get_feedback_agent_service)
]
"""피드백 에이전트 서비스 의존성 타입"""

FeedbackOrchestratorDep = Annotated[
    "FeedbackOrchestrator",
    Depends(get_feedback_orchestrator)
]
"""피드백 조율기 의존성 타입"""

SessionServiceDep = Annotated[
    "SessionServiceImpl",
    Depends(get_session_service)
]
"""세션 서비스 의존성 타입"""
