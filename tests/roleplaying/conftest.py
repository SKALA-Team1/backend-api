"""
Pytest Configuration and Shared Fixtures
=========================================
롤플레잉 서비스 테스트용 공통 fixtures.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.roleplaying.schemas import ScenarioDetail


# ============================================
# LLM Provider Fixtures
# ============================================

@pytest.fixture
def mock_openai_llm():
    """Mock OpenAI LLM"""
    llm = AsyncMock()
    llm.invoke = AsyncMock(return_value="Mock OpenAI response")
    return llm


@pytest.fixture
def mock_ollama_llm():
    """Mock Ollama LLM"""
    llm = AsyncMock()
    llm.invoke = AsyncMock(return_value="Mock Ollama response")
    return llm


@pytest.fixture
def mock_llm_provider():
    """Mock LLM Provider"""
    provider = AsyncMock()
    provider.invoke = AsyncMock(return_value="Mock LLM response")
    return provider


# ============================================
# Service Fixtures
# ============================================

@pytest.fixture
def mock_session_repository():
    """Mock SessionRepository"""
    repo = AsyncMock()
    repo.save_session = AsyncMock()
    repo.get_session = AsyncMock(return_value={"userId": 1, "role": "user"})
    repo.delete_session = AsyncMock()
    repo.close = AsyncMock()
    return repo


@pytest.fixture
def mock_scenario_repository():
    """Mock ScenarioRepository"""
    repo = AsyncMock()
    scenario = ScenarioDetail(
        scenarioId=1,
        subjectId=1,
        myRole="Software Engineer",
        aiRole="Tech Lead",
        title="API Design Discussion",
        topicType="detail",
        fixedQuestions=["Question 1", "Question 2", "Question 3"]
    )
    repo.get_scenario = AsyncMock(return_value=scenario)
    repo.get_user_scenarios = AsyncMock(return_value=[scenario])
    return repo


@pytest.fixture
def mock_grammar_evaluator():
    """Mock GrammarEvaluator"""
    evaluator = AsyncMock()
    evaluator.evaluate_grammar = AsyncMock(
        return_value={"score": 85, "feedback": "Good grammar"}
    )
    return evaluator


@pytest.fixture
def mock_relevance_evaluator():
    """Mock RelevanceEvaluator"""
    evaluator = AsyncMock()
    evaluator.evaluate_relevance = AsyncMock(
        return_value={"score": 90, "feedback": "Very relevant"}
    )
    return evaluator


@pytest.fixture
def mock_pronunciation_evaluator():
    """Mock PronunciationEvaluator"""
    evaluator = AsyncMock()
    evaluator.evaluate_pronunciation = AsyncMock(
        return_value={"score": 80, "feedback": "Clear pronunciation"}
    )
    return evaluator


@pytest.fixture
def mock_feedback_judge():
    """Mock FeedbackJudge"""
    judge = MagicMock()
    judge.judge_correction_needed = MagicMock(
        return_value=(False, "none")
    )
    return judge


# ============================================
# Database Fixtures
# ============================================

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy Session"""
    db = MagicMock()
    db.execute = MagicMock()
    return db


@pytest.fixture
def mock_redis_client():
    """Mock Redis Client"""
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value='{"userId": 1, "role": "user"}')
    redis_client.setex = AsyncMock()
    redis_client.delete = AsyncMock()
    redis_client.close = AsyncMock()
    return redis_client


# ============================================
# Sample Data Fixtures
# ============================================

@pytest.fixture
def sample_conversation_messages():
    """Sample conversation messages"""
    return [
        {
            "senderName": "User",
            "text": "How do I optimize API performance?",
            "myMessage": True
        },
        {
            "senderName": "Tech Lead",
            "text": "We should look at caching strategies.",
            "myMessage": False
        },
        {
            "senderName": "User",
            "text": "What about Redis?",
            "myMessage": True
        }
    ]


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history"""
    return [
        {"speaker": "User", "text": "Hello, I need help with my project."},
        {"speaker": "AI", "text": "Sure, I'd be happy to help. Tell me more."},
        {"speaker": "User", "text": "We have performance issues."},
        {"speaker": "AI", "text": "Let's diagnose the problem together."}
    ]


@pytest.fixture
def sample_scenario_context():
    """Sample scenario context"""
    return {
        "my_role": "Software Engineer",
        "ai_role": "Tech Lead",
        "current_question": "What strategies would you recommend?",
        "subject_id": 1
    }


@pytest.fixture
def sample_scenario_detail():
    """Sample ScenarioDetail"""
    return ScenarioDetail(
        scenarioId=1,
        subjectId=1,
        myRole="Backend Engineer",
        aiRole="Tech Lead",
        title="API Optimization Strategies",
        topicType="detail",
        fixedQuestions=[
            "How would you approach this problem?",
            "What tools would you use?",
            "What's your timeline?"
        ]
    )


# ============================================
# Async Test Support
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================
# Settings Fixtures
# ============================================

@pytest.fixture
def mock_settings(monkeypatch):
    """Mock app.config.settings"""
    from app.config import settings as real_settings

    mock_settings = MagicMock()
    mock_settings.openai_api_key = "test-key"
    mock_settings.OPENAI_MODEL_QUESTION_GENERATION = "gpt-4"
    mock_settings.OPENAI_MODEL_AI_RESPONSE = "gpt-4"
    mock_settings.OPENAI_MODEL_FEEDBACK = "gpt-3.5-turbo"
    mock_settings.FEEDBACK_LLM_PROVIDER = "openai"
    mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
    mock_settings.OLLAMA_MODEL = "llama2"
    mock_settings.REDIS_URL = "redis://localhost:6379"
    mock_settings.FEEDBACK_PRONUNCIATION_THRESHOLD = 70
    mock_settings.FEEDBACK_GRAMMAR_THRESHOLD = 70
    mock_settings.FEEDBACK_RELEVANCE_THRESHOLD = 70
    mock_settings.FEEDBACK_MAX_RETRY_PER_QUESTION = 3

    return mock_settings
