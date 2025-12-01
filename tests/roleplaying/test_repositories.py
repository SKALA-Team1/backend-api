"""
Repositories Tests
==================
RedisSessionRepository, DatabaseScenarioRepository 테스트.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.roleplaying.services.repositories import (
    RedisSessionRepository,
    DatabaseScenarioRepository
)
from app.roleplaying.schemas import ScenarioDetail


class TestRedisSessionRepository:
    """RedisSessionRepository 테스트"""

    @pytest.mark.asyncio
    async def test_save_session(self):
        """세션 저장"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        repo.redis_client = mock_redis

        expires_at = datetime.utcnow() + timedelta(hours=2)

        await repo.save_session(
            session_id="test-session-123",
            user_id=1,
            expires_at=expires_at
        )

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "session:test-session-123" in call_args[0]

    @pytest.mark.asyncio
    async def test_save_session_default_expiry(self):
        """기본 만료 시간으로 세션 저장"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        repo.redis_client = mock_redis

        await repo.save_session(
            session_id="test-session-123",
            user_id=1
        )

        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session(self):
        """세션 조회"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        session_data = {
            "userId": 1,
            "role": "user",
            "scenarioType": "ROLEPLAYING"
        }

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(session_data))
        repo.redis_client = mock_redis

        result = await repo.get_session("test-session-123")

        assert result["userId"] == 1
        assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """세션 조회 - 없을 때"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        repo.redis_client = mock_redis

        result = await repo.get_session("nonexistent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_exception_handling(self):
        """세션 조회 - 예외 처리"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        repo.redis_client = mock_redis

        result = await repo.get_session("test-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self):
        """세션 삭제"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        repo.redis_client = mock_redis

        await repo.delete_session("test-session-123")

        mock_redis.delete.assert_called_once_with("session:test-session-123")

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self):
        """세션 삭제 - 없을 때"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)
        repo.redis_client = mock_redis

        await repo.delete_session("nonexistent-session")

        # 삭제 시도는 진행되지만 0 반환

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """Redis 연결 종료"""
        repo = RedisSessionRepository(redis_url="redis://localhost:6379")

        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        repo.redis_client = mock_redis

        await repo.close()

        mock_redis.close.assert_called_once()


class TestDatabaseScenarioRepository:
    """DatabaseScenarioRepository 테스트"""

    @pytest.mark.asyncio
    async def test_get_scenario(self, mock_db_session):
        """시나리오 조회"""
        repo = DatabaseScenarioRepository()

        # Mock DB 행
        mock_row = MagicMock()
        mock_row.scenario_id = 1
        mock_row.subject_id = 100
        mock_row.title = "API Design"
        mock_row.status = "generated"
        mock_row.fixed_questions = json.dumps(["Q1", "Q2", "Q3"])
        mock_row.ai_role = "Tech Lead"
        mock_row.topic_type = "detail"
        mock_row.my_role = "Backend Engineer"

        mock_execute = MagicMock()
        mock_execute.first.return_value = mock_row
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_scenario(
            scenario_id=1,
            user_id=1,
            db=mock_db_session
        )

        assert result.scenarioId == 1
        assert result.myRole == "Backend Engineer"
        assert len(result.fixedQuestions) == 3

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(self, mock_db_session):
        """시나리오 조회 - 없을 때"""
        repo = DatabaseScenarioRepository()

        mock_execute = MagicMock()
        mock_execute.first.return_value = None
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_scenario(
            scenario_id=999,
            user_id=1,
            db=mock_db_session
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_scenario_with_string_questions(self, mock_db_session):
        """JSON 형식 질문 파싱"""
        repo = DatabaseScenarioRepository()

        mock_row = MagicMock()
        mock_row.scenario_id = 1
        mock_row.subject_id = 100
        mock_row.title = "Test"
        mock_row.status = "generated"
        mock_row.fixed_questions = '["Q1", "Q2", "Q3"]'
        mock_row.ai_role = "Lead"
        mock_row.topic_type = "detail"
        mock_row.my_role = "Engineer"

        mock_execute = MagicMock()
        mock_execute.first.return_value = mock_row
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_scenario(
            scenario_id=1,
            user_id=1,
            db=mock_db_session
        )

        assert isinstance(result.fixedQuestions, list)
        assert len(result.fixedQuestions) == 3

    @pytest.mark.asyncio
    async def test_get_scenario_missing_questions(self, mock_db_session):
        """질문이 없을 때 기본값 사용"""
        repo = DatabaseScenarioRepository()

        mock_row = MagicMock()
        mock_row.scenario_id = 1
        mock_row.subject_id = 100
        mock_row.title = "Test"
        mock_row.status = "generated"
        mock_row.fixed_questions = None
        mock_row.ai_role = "Lead"
        mock_row.topic_type = "detail"
        mock_row.my_role = "Engineer"

        mock_execute = MagicMock()
        mock_execute.first.return_value = mock_row
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_scenario(
            scenario_id=1,
            user_id=1,
            db=mock_db_session
        )

        assert len(result.fixedQuestions) == 3

    @pytest.mark.asyncio
    async def test_get_user_scenarios(self, mock_db_session):
        """사용자 시나리오 목록 조회"""
        repo = DatabaseScenarioRepository()

        mock_row = MagicMock()
        mock_row.scenario_id = 1
        mock_row.subject_id = 100
        mock_row.title = "Test"
        mock_row.status = "generated"
        mock_row.fixed_questions = '["Q1", "Q2", "Q3"]'
        mock_row.ai_role = "Lead"
        mock_row.topic_type = "detail"
        mock_row.my_role = "Engineer"

        mock_execute = MagicMock()
        mock_execute.fetchall.return_value = [mock_row]
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_user_scenarios(
            user_id=1,
            limit=10,
            db=mock_db_session
        )

        assert len(result) == 1
        assert result[0].scenarioId == 1

    @pytest.mark.asyncio
    async def test_get_user_scenarios_empty(self, mock_db_session):
        """사용자 시나리오 목록 - 비어있을 때"""
        repo = DatabaseScenarioRepository()

        mock_execute = MagicMock()
        mock_execute.fetchall.return_value = []
        mock_db_session.execute.return_value = mock_execute

        result = await repo.get_user_scenarios(
            user_id=1,
            limit=10,
            db=mock_db_session
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_scenario_no_db_session(self):
        """DB 세션이 없을 때"""
        repo = DatabaseScenarioRepository()

        result = await repo.get_scenario(
            scenario_id=1,
            user_id=1,
            db=None
        )

        assert result is None
