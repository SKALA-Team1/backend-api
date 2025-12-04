"""
Session Service Tests
=====================
SessionServiceImpl 테스트.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.roleplaying.services.business.session_service import SessionServiceImpl
from app.roleplaying.api.api_schemas import ScenarioDetail


class TestSessionServiceImpl:
    """SessionServiceImpl 테스트"""

    @pytest.mark.asyncio
    async def test_setup_session_success(self, mock_session_repository, mock_scenario_repository):
        """세션 설정 성공"""
        service = SessionServiceImpl(
            session_repository=mock_session_repository,
            scenario_repository=mock_scenario_repository
        )

        scenario = ScenarioDetail(
            scenarioId=1,
            subjectId=100,
            myRole="Backend Engineer",
            aiRole="Tech Lead",
            title="API Design",
            topicType="detail",
            fixedQuestions=["Q1", "Q2", "Q3"]
        )

        mock_scenario_repository.get_scenario.return_value = scenario

        session_id, returned_scenario, expires_at = await service.setup_session(
            session_id="test-session-123",
            user_id=1,
            scenario_id=1,
            db=MagicMock()
        )

        assert session_id == "test-session-123"
        assert returned_scenario.scenarioId == 1
        assert returned_scenario.myRole == "Backend Engineer"
        assert isinstance(expires_at, datetime)

        # 저장소 메서드 호출 확인
        mock_scenario_repository.get_scenario.assert_called_once()
        mock_session_repository.save_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_session_scenario_not_found(self, mock_session_repository, mock_scenario_repository):
        """시나리오를 찾을 수 없을 때"""
        service = SessionServiceImpl(
            session_repository=mock_session_repository,
            scenario_repository=mock_scenario_repository
        )

        mock_scenario_repository.get_scenario.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await service.setup_session(
                session_id="test-session-123",
                user_id=1,
                scenario_id=999,
                db=MagicMock()
            )

        assert "not found" in str(exc_info.value)
        # 세션 저장을 시도하지 않아야 함
        mock_session_repository.save_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_session_saves_to_redis(self, mock_session_repository, mock_scenario_repository):
        """Redis에 세션 저장"""
        service = SessionServiceImpl(
            session_repository=mock_session_repository,
            scenario_repository=mock_scenario_repository
        )

        scenario = ScenarioDetail(
            scenarioId=1,
            subjectId=100,
            myRole="Engineer",
            aiRole="Lead",
            title="Test",
            topicType="detail",
            fixedQuestions=["Q1", "Q2", "Q3"]
        )

        mock_scenario_repository.get_scenario.return_value = scenario

        await service.setup_session(
            session_id="test-session-123",
            user_id=1,
            scenario_id=1,
            db=MagicMock()
        )

        # save_session이 올바른 인자로 호출되었는지 확인
        mock_session_repository.save_session.assert_called_once()
        call_args = mock_session_repository.save_session.call_args

        assert call_args[1]["session_id"] == "test-session-123"
        assert call_args[1]["user_id"] == 1

    @pytest.mark.asyncio
    async def test_setup_session_returns_expires_at(self, mock_session_repository, mock_scenario_repository):
        """만료 시각 반환"""
        service = SessionServiceImpl(
            session_repository=mock_session_repository,
            scenario_repository=mock_scenario_repository
        )

        scenario = ScenarioDetail(
            scenarioId=1,
            subjectId=100,
            myRole="Engineer",
            aiRole="Lead",
            title="Test",
            topicType="detail",
            fixedQuestions=["Q1", "Q2", "Q3"]
        )

        mock_scenario_repository.get_scenario.return_value = scenario

        session_id, returned_scenario, expires_at = await service.setup_session(
            session_id="test-session-123",
            user_id=1,
            scenario_id=1,
            db=MagicMock()
        )

        # expires_at는 현재 시간 + 2시간
        now = datetime.utcnow()
        time_diff = (expires_at - now).total_seconds()

        # 2시간 근처 (오차 범위: 10초)
        assert 7190 < time_diff < 7210

    @pytest.mark.asyncio
    async def test_setup_session_integrates_repositories(self, mock_session_repository, mock_scenario_repository):
        """저장소 통합"""
        service = SessionServiceImpl(
            session_repository=mock_session_repository,
            scenario_repository=mock_scenario_repository
        )

        scenario = ScenarioDetail(
            scenarioId=5,
            subjectId=200,
            myRole="QA Engineer",
            aiRole="Architect",
            title="Quality Assurance",
            topicType="overview",
            fixedQuestions=["What?", "Why?", "How?"]
        )

        mock_scenario_repository.get_scenario.return_value = scenario

        session_id, returned_scenario, expires_at = await service.setup_session(
            session_id="qa-session-456",
            user_id=2,
            scenario_id=5,
            db=MagicMock()
        )

        # ScenarioRepository와 SessionRepository가 모두 호출되었는지 확인
        mock_scenario_repository.get_scenario.assert_called_once_with(5, 2, MagicMock)
        mock_session_repository.save_session.assert_called_once()

        # 반환값 검증
        assert session_id == "qa-session-456"
        assert returned_scenario.scenarioId == 5
        assert returned_scenario.myRole == "QA Engineer"
