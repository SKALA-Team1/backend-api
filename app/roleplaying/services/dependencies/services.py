"""
Business Service Dependencies
(AITutorService, SlackScenarioService, PromptBasedScenarioService, SessionService)
==================================================================================

비즈니스 로직 서비스 의존성 주입 (Dependency Injection)

주요 서비스:
    - AITutorService: 역할극 대화 진행 및 자동 질문 생성
    - SlackScenarioService: Slack 대화 분석 및 시나리오 생성
    - PromptBasedScenarioService: 사용자 프롬프트 기반 시나리오 생성
    - SessionService: WebSocket 세션 생성 및 초기화

설계:
    - 각 서비스는 요청별로 새로운 인스턴스 생성 (Request-scoped)
    - 생성자에서 의존성 자동 주입 (LLM, Repository 등)
    - FastAPI의 Depends() 체인으로 재귀적 의존성 해결

사용 예:
    from app.roleplaying.services.dependencies.services import (
        AITutorServiceDep,
        SessionServiceDep
    )

    @router.post("/sessions/initialize")
    async def initialize_session(
        request: SessionSetupRequest,
        session_service: SessionServiceDep
    ):
        session_id, scenario = await session_service.setup_session(...)
        return {"session_id": session_id}
"""

from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

from app.roleplaying.services.dependencies.llm import (
    get_question_generator,
    get_conversation_analyzer,
    get_scenario_generator,
    get_message_summarizer,
    get_fixed_question_builder,
    get_scenario_enhancer,
)
from app.roleplaying.services.dependencies.repositories import (
    get_session_repository,
    get_scenario_repository,
)

if TYPE_CHECKING:
    from app.roleplaying.services.interfaces import (
        QuestionGenerator,
        ConversationAnalyzer,
        ScenarioGenerator,
        MessageSummarizer,
        FixedQuestionBuilder,
        ScenarioEnhancer,
        SessionRepository,
        ScenarioRepository,
    )


# ============================================
# Business Service Factory Functions
# ============================================

def get_ai_tutor_service(
    question_generator: "QuestionGenerator" = Depends(get_question_generator)
):
    """AI 튜터 서비스 의존성 주입

    🎓 역할:
        - 역할극 대화 진행
        - 자동 질문 생성 (턴 2, 3, 5, 6, 8, 9)
        - 고정 질문 확인 (턴 1, 4, 7)

    Returns:
        AITutorService 인스턴스 (Request-scoped)

    Example:
        @router.post("/sessions/{session_id}/reply")
        async def get_ai_reply(
            session_id: str,
            user_text: str,
            ai_tutor: AITutorServiceDep
        ):
            response, is_fixed = await ai_tutor.generate_reply(
                session_state=session,
                user_text=user_text
            )
            return {"response": response}
    """
    from app.roleplaying.services.ai_tutor_service import AITutorService

    return AITutorService(question_generator=question_generator)


def get_slack_scenario_service(
    analyzer: "ConversationAnalyzer" = Depends(get_conversation_analyzer),
    generator: "ScenarioGenerator" = Depends(get_scenario_generator),
    summarizer: "MessageSummarizer" = Depends(get_message_summarizer),
    question_builder: "FixedQuestionBuilder" = Depends(get_fixed_question_builder)
):
    """Slack 시나리오 생성 서비스 의존성 주입

    💬 역할:
        - Slack 스레드 분석 및 주요 토론 내용 추출
        - 토론 내용에서 역할극 시나리오 자동 생성
        - 고정 질문 3개 생성

    Returns:
        SlackScenarioService 인스턴스 (Request-scoped)

    Note:
        내부적으로 다음 서비스들을 사용합니다:
        - ConversationAnalyzer: Slack 대화 분석
        - ScenarioGenerator: 시나리오 생성
        - MessageSummarizer: 대화 요약
        - FixedQuestionBuilder: 고정 질문 생성

    Example:
        @router.post("/scenarios/from-slack")
        async def create_from_slack(
            request: SlackScenarioRequest,
            slack_service: SlackScenarioServiceDep
        ):
            scenario = await slack_service.generate_from_slack_thread(
                thread_messages=request.messages,
                user_id=request.user_id
            )
            return scenario
    """
    from app.roleplaying.services.slack_scenario_service import SlackScenarioService

    return SlackScenarioService(
        analyzer=analyzer,
        generator=generator,
        summarizer=summarizer,
        question_builder=question_builder
    )


def get_prompt_based_scenario_service(
    enhancer: "ScenarioEnhancer" = Depends(get_scenario_enhancer)
):
    """프롬프트 기반 시나리오 생성 서비스 의존성 주입

    ✍️ 역할:
        - 사용자 프롬프트(역할, 상황)에서 시나리오 생성
        - 시나리오 상황 구체화
        - 제목 및 고정 질문 자동 생성

    Returns:
        PromptBasedScenarioService 인스턴스 (Request-scoped)

    Note:
        내부적으로 다음 서비스를 사용합니다:
        - ScenarioEnhancer: 시나리오 강화

    Example:
        @router.post("/scenarios/from-prompt")
        async def create_from_prompt(
            request: PromptScenarioRequest,
            prompt_service: PromptBasedScenarioServiceDep
        ):
            scenario = await prompt_service.generate_from_prompt(
                user_id=request.user_id,
                my_role=request.my_role,
                ai_role=request.ai_role,
                situation=request.situation
            )
            return scenario
    """
    from app.roleplaying.services.prompt_based_generator_service import PromptBasedScenarioService

    return PromptBasedScenarioService(enhancer=enhancer)


def get_session_service(
    session_repo: "SessionRepository" = Depends(get_session_repository),
    scenario_repo: "ScenarioRepository" = Depends(get_scenario_repository)
):
    """세션 서비스 의존성 주입

    🔐 역할:
        - WebSocket 세션 생성 및 초기화
        - 세션 설정(역할, 시나리오) 저장
        - 세션 만료 관리

    Returns:
        SessionServiceImpl 인스턴스 (Request-scoped)

    Note:
        내부적으로 다음 저장소들을 사용합니다:
        - SessionRepository: Redis 세션 저장
        - ScenarioRepository: 시나리오 조회

    Example:
        @router.post("/sessions/setup")
        async def setup_session(
            request: InternalSessionSetupRequest,
            session_service: SessionServiceDep
        ):
            session_id, scenario, expires_at = await session_service.setup_session(
                user_id=request.user_id,
                subject_id=request.subject_id,
                ...
            )
            return {
                "session_id": session_id,
                "scenario": scenario,
                "expires_at": expires_at
            }
    """
    from app.roleplaying.services.session_service_refactored import SessionServiceImpl

    return SessionServiceImpl(
        session_repository=session_repo,
        scenario_repository=scenario_repo
    )


# ============================================
# Type Aliases for FastAPI Depends
# ============================================

AITutorServiceDep = Annotated[
    "AITutorService",
    Depends(get_ai_tutor_service)
]
"""AI 튜터 서비스 의존성 타입 - 대화 진행 및 질문 생성"""

SlackScenarioServiceDep = Annotated[
    "SlackScenarioService",
    Depends(get_slack_scenario_service)
]
"""Slack 시나리오 생성 서비스 의존성 타입 - Slack 대화 분석"""

PromptBasedScenarioServiceDep = Annotated[
    "PromptBasedScenarioService",
    Depends(get_prompt_based_scenario_service)
]
"""프롬프트 기반 시나리오 생성 서비스 의존성 타입 - 사용자 입력 분석"""

SessionServiceDep = Annotated[
    "SessionServiceImpl",
    Depends(get_session_service)
]
"""세션 서비스 의존성 타입 - 세션 생성 및 관리"""

__all__ = [
    "get_ai_tutor_service",
    "get_slack_scenario_service",
    "get_prompt_based_scenario_service",
    "get_session_service",
    "AITutorServiceDep",
    "SlackScenarioServiceDep",
    "PromptBasedScenarioServiceDep",
    "SessionServiceDep",
]
