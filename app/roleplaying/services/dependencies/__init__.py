"""
Dependency Injection Facade
===========================

🔧 목적: 분산된 의존성 정의를 중앙에서 재 export

이 패키지는 FastAPI 의존성 주입(DI) 컨테이너입니다.
SOLID 원칙 중 Dependency Inversion을 구현하며,
서비스 인스턴스를 중앙에서 관리합니다.

📦 구조:
    dependencies/
    ├── llm.py              → LLM 서비스 (OpenAI 기반)
    ├── feedback.py         → 피드백 평가 서비스
    ├── repositories.py     → 데이터 접근 계층 (Redis, DB)
    ├── services.py         → 비즈니스 로직 서비스
    └── __init__.py         → 이 파일 (Facade)

💡 하위 호환성:
    기존 코드는 다음과 같이 import할 수 있습니다:

    # 방법 1: 직접 import (권장)
    from app.roleplaying.services.dependencies import ConversationAnalyzerDep

    # 방법 2: 하위 모듈 import
    from app.roleplaying.services.dependencies.llm import get_conversation_analyzer

🔄 의존성 주입 흐름:

    1. 라우터 함수에서 의존성 타입 사용
       @router.post("/analyze")
       async def analyze(analyzer: ConversationAnalyzerDep):
           ...

    2. FastAPI가 Depends() 감지하여 자동 주입
       → get_conversation_analyzer() 호출
       → ConversationAnalyzerImpl 인스턴스 생성
       → @lru_cache로 캐싱

    3. 함수 파라미터로 주입됨
       analyzer = <싱글톤 인스턴스>
"""

# ============================================
# LLM Service Imports
# ============================================
from app.roleplaying.services.dependencies.llm import (
    get_conversation_analyzer,
    get_scenario_generator,
    get_question_generator,
    get_ai_response_generator,
    get_message_summarizer,
    get_fixed_question_builder,
    get_scenario_enhancer,
    ConversationAnalyzerDep,
    ScenarioGeneratorDep,
    QuestionGeneratorDep,
    AIResponseGeneratorDep,
    MessageSummarizerDep,
    FixedQuestionBuilderDep,
    ScenarioEnhancerDep,
)

# ============================================
# Feedback Service Imports
# ============================================
from app.roleplaying.services.dependencies.feedback import (
    get_pronunciation_evaluator,
    get_grammar_evaluator,
    get_relevance_evaluator,
    get_feedback_judge,
    get_feedback_orchestrator,
    get_feedback_agent_service,
    get_azure_usage_tracker,
    PronunciationEvaluatorDep,
    GrammarEvaluatorDep,
    RelevanceEvaluatorDep,
    FeedbackJudgeDep,
    FeedbackOrchestratorDep,
    FeedbackAgentServiceDep,
)

# ============================================
# Repository Imports
# ============================================
from app.roleplaying.services.dependencies.repositories import (
    get_session_repository,
    get_scenario_repository,
    SessionRepositoryDep,
    ScenarioRepositoryDep,
)

# ============================================
# Business Service Imports
# ============================================
from app.roleplaying.services.dependencies.services import (
    get_ai_tutor_service,
    get_slack_scenario_service,
    get_prompt_based_scenario_service,
    get_session_service,
    AITutorServiceDep,
    SlackScenarioServiceDep,
    PromptBasedScenarioServiceDep,
    SessionServiceDep,
)

__all__ = [
    # LLM Services
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
    # Feedback Services
    "get_pronunciation_evaluator",
    "get_grammar_evaluator",
    "get_relevance_evaluator",
    "get_feedback_judge",
    "get_feedback_orchestrator",
    "get_feedback_agent_service",
    "get_azure_usage_tracker",
    "PronunciationEvaluatorDep",
    "GrammarEvaluatorDep",
    "RelevanceEvaluatorDep",
    "FeedbackJudgeDep",
    "FeedbackOrchestratorDep",
    "FeedbackAgentServiceDep",
    # Repositories
    "get_session_repository",
    "get_scenario_repository",
    "SessionRepositoryDep",
    "ScenarioRepositoryDep",
    # Business Services
    "get_ai_tutor_service",
    "get_slack_scenario_service",
    "get_prompt_based_scenario_service",
    "get_session_service",
    "AITutorServiceDep",
    "SlackScenarioServiceDep",
    "PromptBasedScenarioServiceDep",
    "SessionServiceDep",
]
