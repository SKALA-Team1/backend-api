"""
Pytest Configuration and Shared Fixtures
=========================================
롤플레잉 서비스 테스트용 공통 fixtures.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.roleplaying.api.api_schemas import ScenarioDetail
from app.roleplaying.core.session_models import SessionState, SessionStatus, Turn
from app.roleplaying.handlers.ws_message_models import InitMessage, AiTextMessage


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
    """Sample conversation messages with timestamps"""
    from datetime import datetime
    now = datetime.now(timezone.utc)
    return [
        {
            "senderName": "User",
            "text": "How do I optimize API performance?",
            "myMessage": True,
            "timestamp": now.isoformat()
        },
        {
            "senderName": "Tech Lead",
            "text": "We should look at caching strategies.",
            "myMessage": False,
            "timestamp": now.isoformat()
        },
        {
            "senderName": "User",
            "text": "What about Redis?",
            "myMessage": True,
            "timestamp": now.isoformat()
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


# ============================================
# Session Models Fixtures
# ============================================

@pytest.fixture
def sample_session_state():
    """Sample SessionState"""
    return SessionState(
        session_id="session-123",
        user_id=1,
        subject_id=1,
        my_role="Software Engineer",
        ai_role="Tech Lead",
        fixed_questions=[
            "What is your approach?",
            "What tools would you use?",
            "What's your timeline?"
        ],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )


@pytest.fixture
def sample_turn_user():
    """Sample User Turn"""
    return Turn(
        speaker="user",
        text="I need help with API design",
        timestamp=datetime.now(timezone.utc),
        audio_s3_url="s3://bucket/audio-123.wav"
    )


@pytest.fixture
def sample_turn_ai():
    """Sample AI Turn"""
    return Turn(
        speaker="ai",
        text="What specific aspects concern you?",
        timestamp=datetime.now(timezone.utc),
        is_fixed_question=True
    )


# ============================================
# WebSocket Message Fixtures
# ============================================

@pytest.fixture
def sample_init_message():
    """Sample INIT message"""
    return InitMessage(
        type="INIT",
        userId=1,
        subjectId=1,
        myRole="Software Engineer",
        aiRole="Tech Lead",
        fixedQuestions=[
            "Question 1?",
            "Question 2?",
            "Question 3?"
        ]
    )


@pytest.fixture
def sample_ai_text_message():
    """Sample AI_TEXT message"""
    return AiTextMessage(
        type="AI_TEXT",
        text="This is an AI response",
        is_fixed_question=False
    )


# ============================================
# API Schema Fixtures
# ============================================

@pytest.fixture
def sample_scenario_detail_extended():
    """Extended ScenarioDetail with all fields"""
    return ScenarioDetail(
        scenarioId=1,
        subjectId=1,
        myRole="Senior Backend Engineer",
        aiRole="CTO",
        title="System Architecture Design",
        topicType="detail",
        fixedQuestions=[
            "How would you design this system?",
            "What are the scalability concerns?",
            "How would you handle failures?"
        ]
    )


# ============================================
# Session Manager Fixtures
# ============================================

@pytest.fixture
def session_manager_instance():
    """Fresh SessionManager instance for testing"""
    from app.roleplaying.core.session_manager_base import SessionManager
    return SessionManager()


@pytest.fixture
def fresh_manager(monkeypatch):
    """
    Fresh SessionManager with module-level patching for test isolation.

    This fixture creates a new SessionManager and patches it at the module
    level where it's imported, ensuring all handler functions use the fresh
    instance.
    """
    import sys
    from importlib import reload
    from app.roleplaying.core.session_manager_base import SessionManager

    # Create fresh manager
    manager = SessionManager()

    # Patch the session_manager_base module first
    import app.roleplaying.core.session_manager_base as smb_module
    monkeypatch.setattr(smb_module, 'session_manager', manager)

    # Then reload the handler modules so they re-import the patched session_manager
    import app.roleplaying.core.session_message_handler as msg_module
    import app.roleplaying.core.session_audio_handler as audio_module

    reload(msg_module)
    reload(audio_module)

    # Update sys.modules references
    sys.modules['app.roleplaying.core.session_message_handler'] = msg_module
    sys.modules['app.roleplaying.core.session_audio_handler'] = audio_module

    return manager


# ============================================
# Audio Fixtures
# ============================================

@pytest.fixture
def sample_audio_chunk():
    """Sample audio chunk (WAV format, 16kHz, 16-bit, mono)"""
    # Simulate 64ms of audio (1024 bytes)
    return b'\x00' * 1024


@pytest.fixture
def sample_audio_full():
    """Sample full audio buffer (10 chunks)"""
    return b'\x00' * 10240


# ============================================
# Async Test Support
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def async_test_helper():
    """Helper for async tests"""
    pass
