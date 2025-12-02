"""
LLM Service Dependencies
========================

🔧 역할: OpenAI 기반 LLM 서비스 의존성 관리

서비스 목록:
    - ConversationAnalyzer: Slack 대화 분석 (토론 내용 추출)
    - ScenarioGenerator: 시나리오 생성 (역할극 상황 생성)
    - QuestionGenerator: 질문 생성 (다음 턴 질문)
    - AIResponseGenerator: AI 응답 생성 (AI 발언)
    - MessageSummarizer: 메시지 요약 (대화 요약)
    - FixedQuestionBuilder: 고정 질문 생성 (턴 1, 4, 7 질문)
    - ScenarioEnhancer: 시나리오 강화 (상황 구체화, 제목 생성)

📋 설계:
    - 모든 서비스는 싱글톤 (@lru_cache)
    - OpenAI API 키와 모델명 설정값 주입
    - Temperature 설정으로 창의성/안정성 조절

💡 사용 방법:

    from app.roleplaying.services.dependencies.llm import (
        ConversationAnalyzerDep,
        ScenarioGeneratorDep
    )

    @router.post("/analyze")
    async def analyze(
        analyzer: ConversationAnalyzerDep
    ):
        situation = await analyzer.analyze_situation(...)
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
        MessageSummarizer,
        FixedQuestionBuilder,
        ScenarioEnhancer,
    )


# ============================================
# LLM Service Factory Functions
# ============================================

@lru_cache(maxsize=1)
def get_conversation_analyzer() -> "ConversationAnalyzer":
    """대화 분석기 의존성 주입

    🔍 역할:
        - Slack 대화 스레드 분석
        - 주요 토론 내용 추출
        - 역할극 시나리오 제안

    Returns:
        ConversationAnalyzer 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import ConversationAnalyzerImpl

    return ConversationAnalyzerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.3  # ❄️ 낮은 창의성 (분석 작업용)
    )


@lru_cache(maxsize=1)
def get_scenario_generator() -> "ScenarioGenerator":
    """시나리오 생성기 의존성 주입

    🎬 역할:
        - 사용자 입력(역할, 상황)에서 시나리오 생성
        - Slack 대화에서 역할극 시나리오 제안

    Returns:
        ScenarioGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import ScenarioGeneratorImpl

    return ScenarioGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7  # 🔥 높은 창의성 (생성 작업용)
    )


@lru_cache(maxsize=1)
def get_question_generator() -> "QuestionGenerator":
    """질문 생성기 의존성 주입

    ❓ 역할:
        - 사용자 답변에 대한 후속 질문 생성
        - 역할극 진행을 위한 다음 질문

    Returns:
        QuestionGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import QuestionGeneratorImpl

    return QuestionGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7  # 🔥 높은 창의성 (질문 다양성)
    )


@lru_cache(maxsize=1)
def get_ai_response_generator() -> "AIResponseGenerator":
    """AI 응답 생성기 의존성 주입

    🤖 역할:
        - 사용자 발언에 대한 AI 캐릭터 응답 생성
        - 역할 유지하며 자연스러운 대화 진행

    Returns:
        AIResponseGenerator 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import AIResponseGeneratorImpl

    return AIResponseGeneratorImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_AI_RESPONSE,  # 더 강력한 모델
        temperature=0.7  # 🔥 높은 창의성 (대화 자연성)
    )


@lru_cache(maxsize=1)
def get_message_summarizer() -> "MessageSummarizer":
    """메시지 요약기 의존성 주입

    📝 역할:
        - 대화 히스토리 요약
        - Context window 압축 (비용 절감)

    Returns:
        MessageSummarizer 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import MessageSummarizerImpl

    return MessageSummarizerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.3  # ❄️ 낮은 창의성 (정보 보존)
    )


@lru_cache(maxsize=1)
def get_fixed_question_builder() -> "FixedQuestionBuilder":
    """고정 질문 생성기 의존성 주입

    🎯 역할:
        - 턴 1, 4, 7에서 사용할 고정 질문 생성
        - 시나리오별로 사전 정의된 전략적 질문

    Returns:
        FixedQuestionBuilder 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import FixedQuestionBuilderImpl

    return FixedQuestionBuilderImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7  # 🔥 높은 창의성 (다양한 질문)
    )


@lru_cache(maxsize=1)
def get_scenario_enhancer() -> "ScenarioEnhancer":
    """시나리오 강화기 의존성 주입

    ✨ 역할:
        - 사용자 프롬프트에서 시나리오 구체화
        - 제목 생성 및 고정 질문 생성

    Returns:
        ScenarioEnhancer 인스턴스 (싱글톤)
    """
    from app.roleplaying.services.llm_service_refactored import ScenarioEnhancerImpl

    return ScenarioEnhancerImpl(
        api_key=settings.openai_api_key,
        model_name=settings.OPENAI_MODEL_QUESTION_GENERATION,
        temperature=0.7  # 🔥 높은 창의성 (생성 작업)
    )


# ============================================
# Type Aliases for FastAPI Depends
# ============================================

ConversationAnalyzerDep = Annotated[
    "ConversationAnalyzer",
    Depends(get_conversation_analyzer)
]
"""대화 분석기 의존성 타입 - Slack 대화 분석용"""

ScenarioGeneratorDep = Annotated[
    "ScenarioGenerator",
    Depends(get_scenario_generator)
]
"""시나리오 생성기 의존성 타입 - 역할극 시나리오 생성용"""

QuestionGeneratorDep = Annotated[
    "QuestionGenerator",
    Depends(get_question_generator)
]
"""질문 생성기 의존성 타입 - 후속 질문 생성용"""

AIResponseGeneratorDep = Annotated[
    "AIResponseGenerator",
    Depends(get_ai_response_generator)
]
"""AI 응답 생성기 의존성 타입 - AI 캐릭터 응답 생성용"""

MessageSummarizerDep = Annotated[
    "MessageSummarizer",
    Depends(get_message_summarizer)
]
"""메시지 요약기 의존성 타입 - 대화 요약용"""

FixedQuestionBuilderDep = Annotated[
    "FixedQuestionBuilder",
    Depends(get_fixed_question_builder)
]
"""고정 질문 생성기 의존성 타입 - 턴 1,4,7 질문 생성용"""

ScenarioEnhancerDep = Annotated[
    "ScenarioEnhancer",
    Depends(get_scenario_enhancer)
]
"""시나리오 강화기 의존성 타입 - 시나리오 구체화/제목/질문 생성용"""

__all__ = [
    "get_conversation_analyzer",
    "get_scenario_generator",
    "get_question_generator",
    "get_ai_response_generator",
    "get_message_summarizer",
    "get_fixed_question_builder",
    "get_scenario_enhancer",
    "ConversationAnalyzerDep",
    "ScenarioGeneratorDep",
    "QuestionGeneratorDep",
    "AIResponseGeneratorDep",
    "MessageSummarizerDep",
    "FixedQuestionBuilderDep",
    "ScenarioEnhancerDep",
]
