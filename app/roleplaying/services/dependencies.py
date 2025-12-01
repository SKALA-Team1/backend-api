"""
Dependency Injection Configuration Module
==========================================

🔧 목적: FastAPI 의존성 주입(DI) 컨테이너 설정 및 싱글톤 인스턴스 관리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 모듈은 SOLID 원칙 중 Dependency Inversion을 구현합니다.
서비스 인스턴스를 중앙에서 관리하고, FastAPI의 Depends()를 통해
라우터에 자동 주입하는 역할을 합니다.

📋 핵심 역할:

    1. 싱글톤 인스턴스 생성 및 캐싱
        - @lru_cache(maxsize=1): 애플리케이션 생명주기 동안 1개만 생성
        - OpenAI LLM 인스턴스, 분석기, 생성기 등

    2. 팩토리 함수 제공
        - get_*_service(): 필요시 새로운 인스턴스 생성
        - get_*_repository(): DB 세션별 새로운 저장소 인스턴스

    3. Annotated 타입 별칭 정의
        - 라우터에서 간편하게 사용
        - 자동 의존성 주입 메커니즘

⚙️ 서비스 계층 구조:

    [LLM 서비스 계층] (Singleton - @lru_cache)
    ├─ ConversationAnalyzer: Slack 대화 분석
    ├─ ScenarioGenerator: 시나리오 생성
    ├─ QuestionGenerator: 질문 생성
    ├─ AIResponseGenerator: AI 응답 생성
    ├─ GrammarEvaluator: 문법 평가
    ├─ RelevanceEvaluator: 맥락 관련성 평가
    ├─ PronunciationEvaluator: 발음 평가 (Azure Speech)
    ├─ FeedbackJudge: 피드백 판정
    ├─ FeedbackOrchestrator: 피드백 조율
    ├─ MessageSummarizer: 메시지 요약
    ├─ FixedQuestionBuilder: 고정 질문 생성
    └─ ScenarioEnhancer: 시나리오 강화

    [저장소 계층] (Request-scoped)
    ├─ SessionRepository: Redis 기반 세션 관리
    └─ ScenarioRepository: DB 기반 시나리오 조회

    [복합 비즈니스 로직 계층] (의존성 자동 주입)
    ├─ AITutorService: 튜터 로직
    ├─ SlackScenarioService: Slack 대화 분석 및 시나리오 생성
    ├─ PromptBasedScenarioService: 사용자 프롬프트 기반 생성
    ├─ SessionService: 세션 설정 및 관리
    └─ FeedbackAgentService: 피드백 생성 및 전송

💡 사용 방법 예시:

    # 방법 1: Annotated 타입 별칭 사용 (권장)
    @router.post("/analyze")
    async def analyze(
        request: AnalysisRequest,
        analyzer: ConversationAnalyzerDep
    ):
        # analyzer는 자동으로 get_conversation_analyzer() 결과가 주입됨
        result = await analyzer.analyze_situation(...)
        return result

    # 방법 2: Depends() 명시적 사용
    @router.post("/setup")
    async def setup(
        request: SessionSetupRequest,
        session_service: SessionService = Depends(get_session_service)
    ):
        ...

    # 방법 3: 복합 서비스 (의존성 자동 재귀)
    # SessionService의 파라미터인 session_repo, scenario_repo도 자동 주입
    @router.post("/initialize")
    async def init(
        service: SessionServiceDep
    ):
        ...

🔄 의존성 주입 작동 흐름:

    1️⃣ 라우터 함수 정의
       @router.post("/analyze")
       async def analyze(analyzer: ConversationAnalyzerDep):
           ...

    2️⃣ FastAPI가 ConversationAnalyzerDep 감지
       → typing.get_args() 분석
       → Depends(get_conversation_analyzer) 발견

    3️⃣ get_conversation_analyzer() 실행
       → ConversationAnalyzerImpl 인스턴스 생성
       → OpenAI API 클라이언트 초기화
       → @lru_cache로 캐싱 (동일 프로세스에서 재사용)

    4️⃣ 인스턴스가 함수 파라미터로 주입됨
       analyzer = <ConversationAnalyzerImpl 인스턴스>

⚠️ 설계 결정 사항:

    [싱글톤 vs 요청별 생성]
    LLM 서비스: Singleton (@lru_cache 사용)
    - 이유: API 비용 절감, 초기 로딩 시간 절약
    - 문제: 상태 변경 금지 (thread-safe 필수)

    저장소: Request-scoped (매번 새로운 인스턴스)
    - 이유: DB 연결/Redis 풀 효율적 관리
    - 이점: 각 요청마다 독립적인 상태 유지

    [설정값 주입 패턴]
    - settings.openai_api_key: 환경변수 (OpenAI 인증)
    - settings.OPENAI_MODEL_*: 모델명 선택 (GPT-4 등)
    - settings.FEEDBACK_LLM_PROVIDER: 피드백 LLM 공급자

    [순환 의존성 방지]
    - 서비스 간 순환 의존 금지 (아키텍처 규칙)
    - 명확한 계층 구조 유지 (의존성 그래프 DAG)

의존성:
    - fastapi.Depends: 의존성 주입 메커니즘
    - functools.lru_cache: 싱글톤 패턴 구현
    - app.config.settings: 환경설정 (API 키, 모델명 등)
    - app.roleplaying.services.*: 모든 서비스 구현체
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
