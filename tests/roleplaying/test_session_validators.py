"""
Test Session Validators
=======================

세션/메시지 검증 및 에러 처리 테스트:
- SessionValidator (세션 상태 검증)
- InitStateValidator (초기화 상태 검증)
- ErrorHandler (에러 처리)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from app.roleplaying.handlers.session_validators import (
    SessionValidator,
    InitStateValidator,
    ErrorHandler
)
from app.roleplaying.core.session_manager_base import session_manager
from app.roleplaying.core.session_models import SessionStatus


@pytest.fixture
def clean_sessions():
    """테스트 전후 세션 정리"""
    session_manager._sessions.clear()
    session_manager._session_locks.clear()
    yield session_manager
    session_manager._sessions.clear()
    session_manager._session_locks.clear()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def sample_session(clean_sessions):
    """샘플 활성 세션"""
    session = clean_sessions.create_session(
        session_id="test-session",
        user_id=1,
        subject_id=1,
        my_role="Engineer",
        ai_role="Lead",
        fixed_questions=["Q1", "Q2", "Q3"],
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return session


class TestSessionValidator:
    """세션 검증 테스트"""

    @pytest.mark.asyncio
    async def test_validate_active_success(self, mock_websocket, sample_session):
        """활성 세션 검증 성공"""
        session = await SessionValidator.validate_active(
            mock_websocket, "test-session"
        )
        assert session is not None
        assert session.session_id == "test-session"
        assert session.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_validate_active_session_not_found(self, mock_websocket, clean_sessions):
        """세션 존재하지 않음"""
        session = await SessionValidator.validate_active(
            mock_websocket, "non-existent"
        )
        assert session is None
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_validate_active_session_not_active(self, mock_websocket, clean_sessions):
        """세션 비활성화 상태"""
        session = clean_sessions.create_session(
            session_id="inactive-session",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        # 세션 종료
        clean_sessions.end_session("inactive-session", "user_end")

        result = await SessionValidator.validate_active(
            mock_websocket, "inactive-session"
        )
        assert result is None
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_validate_active_session_expired(self, mock_websocket, clean_sessions):
        """세션 만료됨"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        session = clean_sessions.create_session(
            session_id="expired-session",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"],
            expires_at=past_time
        )

        result = await SessionValidator.validate_active(
            mock_websocket, "expired-session"
        )
        assert result is None
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_validate_session_for_operation_success(self, mock_websocket, sample_session):
        """작업 전 세션 검증 성공"""
        session = await SessionValidator.validate_session_for_operation(
            mock_websocket, "test-session", "send_message"
        )
        assert session is not None
        assert session.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_validate_session_for_operation_failure(self, mock_websocket, clean_sessions):
        """작업 전 세션 검증 실패"""
        session = await SessionValidator.validate_session_for_operation(
            mock_websocket, "non-existent", "send_message"
        )
        assert session is None

    @pytest.mark.asyncio
    async def test_validate_initialized_true(self, mock_websocket):
        """초기화 상태 검증 성공"""
        result = await SessionValidator.validate_initialized(
            mock_websocket, True
        )
        assert result is True
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_initialized_false(self, mock_websocket):
        """초기화되지 않은 상태"""
        result = await SessionValidator.validate_initialized(
            mock_websocket, False
        )
        assert result is False
        mock_websocket.send_json.assert_called()


class TestInitStateValidator:
    """초기화 상태 검증 테스트"""

    def test_requires_initialization_audio_chunk(self):
        """AUDIO_CHUNK는 초기화 필요"""
        assert InitStateValidator.requires_initialization("AUDIO_CHUNK") is True

    def test_requires_initialization_utterance_end(self):
        """UTTERANCE_END는 초기화 필요"""
        assert InitStateValidator.requires_initialization("UTTERANCE_END") is True

    def test_requires_initialization_user_text(self):
        """USER_TEXT는 초기화 필요"""
        assert InitStateValidator.requires_initialization("USER_TEXT") is True

    def test_requires_initialization_init(self):
        """INIT는 초기화 불필요"""
        assert InitStateValidator.requires_initialization("INIT") is False

    def test_requires_initialization_end_session(self):
        """END_SESSION은 초기화 불필요"""
        assert InitStateValidator.requires_initialization("END_SESSION") is False

    @pytest.mark.asyncio
    async def test_validate_for_message_initialized(self, mock_websocket):
        """초기화됨 상태에서 AUDIO_CHUNK 검증"""
        result = await InitStateValidator.validate_for_message(
            mock_websocket, "AUDIO_CHUNK", session_initialized=True
        )
        assert result is True
        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_for_message_not_initialized(self, mock_websocket):
        """초기화 안됨 상태에서 AUDIO_CHUNK 검증"""
        result = await InitStateValidator.validate_for_message(
            mock_websocket, "AUDIO_CHUNK", session_initialized=False
        )
        assert result is False
        mock_websocket.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_validate_for_message_init_requires_no_init(self, mock_websocket):
        """INIT 메시지는 초기화 상태 무관"""
        # 초기화됨 상태에서 INIT
        result = await InitStateValidator.validate_for_message(
            mock_websocket, "INIT", session_initialized=True
        )
        assert result is True

        # 초기화 안됨 상태에서 INIT
        result = await InitStateValidator.validate_for_message(
            mock_websocket, "INIT", session_initialized=False
        )
        assert result is True


class TestErrorHandler:
    """에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_send_error_basic(self, mock_websocket):
        """기본 에러 메시지 전송"""
        await ErrorHandler.send_error(
            mock_websocket,
            "Test error message",
            code="TEST_ERROR"
        )
        mock_websocket.send_json.assert_called_once()

        # 호출 인자 확인
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["message"] == "Test error message"
        assert call_args["code"] == "TEST_ERROR"
        assert call_args["type"] == "ERROR"

    @pytest.mark.asyncio
    async def test_send_error_with_severity(self, mock_websocket):
        """심각도별 에러 메시지"""
        for severity in [
            ErrorHandler.SEVERITY_INFO,
            ErrorHandler.SEVERITY_WARNING,
            ErrorHandler.SEVERITY_ERROR
        ]:
            mock_websocket.send_json.reset_mock()
            await ErrorHandler.send_error(
                mock_websocket,
                "Test message",
                severity=severity
            )
            mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_error_websocket_disconnected(self):
        """WebSocket 연결 끊김"""
        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        # 에러를 로깅하지만 예외를 발생시키지 않음
        await ErrorHandler.send_error(ws, "Test message")

    @pytest.mark.asyncio
    async def test_handle_service_error_critical(self, mock_websocket):
        """치명적 서비스 에러"""
        error = ValueError("Service failure")
        await ErrorHandler.handle_service_error(
            mock_websocket,
            "STT",
            error,
            critical=True,
            fallback_message="STT service failed"
        )
        mock_websocket.send_json.assert_called_once()

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["message"] == "STT service failed"
        assert call_args["code"] == "STT_ERROR"

    @pytest.mark.asyncio
    async def test_handle_service_error_non_critical(self, mock_websocket):
        """비치명적 서비스 에러"""
        error = ValueError("Non-critical failure")
        await ErrorHandler.handle_service_error(
            mock_websocket,
            "Spring2",
            error,
            critical=False,
            fallback_message="Spring2 temporarily unavailable"
        )
        mock_websocket.send_json.assert_called_once()

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["message"] == "Spring2 temporarily unavailable"
        assert call_args["code"] == "Spring2_WARNING"

    def test_log_error_critical(self):
        """치명적 에러 로깅"""
        error = ValueError("Critical error")
        # 로깅 실행 (예외 발생 안함)
        ErrorHandler.log_error(
            "Database operation",
            error,
            session_id="test-session",
            critical=True
        )

    def test_log_error_non_critical(self):
        """비치명적 에러 로깅"""
        error = ValueError("Non-critical error")
        ErrorHandler.log_error(
            "Cache operation",
            error,
            session_id="test-session",
            critical=False
        )

    def test_log_error_no_session_id(self):
        """세션 ID 없이 로깅"""
        error = ValueError("Unknown error")
        ErrorHandler.log_error(
            "Validation",
            error,
            critical=True
        )


class TestValidatorIntegration:
    """통합 검증 시나리오"""

    @pytest.mark.asyncio
    async def test_full_validation_workflow_success(self, mock_websocket, sample_session):
        """성공적인 전체 검증 흐름"""
        # 1단계: 초기화 상태 검증
        init_valid = await InitStateValidator.validate_for_message(
            mock_websocket, "AUDIO_CHUNK", session_initialized=True
        )
        assert init_valid is True

        # 2단계: 세션 검증
        session = await SessionValidator.validate_session_for_operation(
            mock_websocket, "test-session", "send_audio"
        )
        assert session is not None

        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_validation_workflow_failure_init(self, mock_websocket, sample_session):
        """초기화 상태 실패"""
        # 1단계: 초기화 상태 검증 - 실패
        init_valid = await InitStateValidator.validate_for_message(
            mock_websocket, "AUDIO_CHUNK", session_initialized=False
        )
        assert init_valid is False

        # 2단계에 도달하지 않음
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_validation_workflow_failure_session(self, mock_websocket, clean_sessions):
        """세션 검증 실패"""
        # 1단계: 초기화 상태 검증 - 통과
        init_valid = await InitStateValidator.validate_for_message(
            mock_websocket, "AUDIO_CHUNK", session_initialized=True
        )
        assert init_valid is True

        # 2단계: 세션 검증 - 실패
        session = await SessionValidator.validate_session_for_operation(
            mock_websocket, "non-existent", "send_audio"
        )
        assert session is None
