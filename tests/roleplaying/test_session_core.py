"""
Test Session Core Layer
=======================

Core 계층 테스트:
- SessionStatus, Turn, SessionState
- SessionManager (생성, 조회, 종료, 정리)
- Session 생명주기 관리
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone

from app.roleplaying.core.session_models import (
    SessionState, SessionStatus, Turn, _get_utc_now
)
from app.roleplaying.core.session_manager_base import SessionManager


class TestSessionStatus:
    """SessionStatus Enum 테스트"""

    def test_session_status_values(self):
        """SessionStatus 상수값 확인"""
        assert SessionStatus.ACTIVE.value == "ACTIVE"
        assert SessionStatus.FINISHED.value == "FINISHED"
        assert SessionStatus.ERROR.value == "ERROR"

    def test_session_status_enum_members(self):
        """SessionStatus 멤버 확인"""
        assert len(SessionStatus) == 3


class TestTurn:
    """Turn 데이터 모델 테스트"""

    def test_turn_user_creation(self, sample_turn_user):
        """사용자 턴 생성"""
        assert sample_turn_user.speaker == "user"
        assert sample_turn_user.text == "I need help with API design"
        assert sample_turn_user.audio_s3_url == "s3://bucket/audio-123.wav"
        assert sample_turn_user.is_fixed_question is False

    def test_turn_ai_creation(self, sample_turn_ai):
        """AI 턴 생성"""
        assert sample_turn_ai.speaker == "ai"
        assert sample_turn_ai.text == "What specific aspects concern you?"
        assert sample_turn_ai.is_fixed_question is True
        assert sample_turn_ai.audio_s3_url is None

    def test_turn_timestamp(self):
        """Turn 타임스탬프는 timezone-aware UTC"""
        now = datetime.now(timezone.utc)
        turn = Turn(
            speaker="user",
            text="Test",
            timestamp=now
        )
        assert turn.timestamp.tzinfo is not None


class TestSessionState:
    """SessionState 데이터 모델 테스트"""

    def test_session_state_creation(self, sample_session_state):
        """세션 상태 생성"""
        assert sample_session_state.session_id == "session-123"
        assert sample_session_state.user_id == 1
        assert sample_session_state.subject_id == 1
        assert sample_session_state.my_role == "Software Engineer"
        assert sample_session_state.ai_role == "Tech Lead"
        assert len(sample_session_state.fixed_questions) == 3
        assert sample_session_state.status == SessionStatus.ACTIVE

    def test_session_state_defaults(self, sample_session_state):
        """세션 상태 기본값"""
        assert sample_session_state.history == []
        assert sample_session_state.current_utterance_audio == b""
        assert sample_session_state.utterance_index == 0
        assert sample_session_state.ai_turn_count == 0
        assert sample_session_state.user_turn_count == 0
        assert sample_session_state.current_question_retry_count == 0

    def test_is_expired_not_expired(self, sample_session_state):
        """만료되지 않은 세션"""
        assert not sample_session_state.is_expired()

    def test_is_expired_expired(self):
        """만료된 세션"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        session = SessionState(
            session_id="session-expired",
            user_id=1,
            subject_id=1,
            my_role="User",
            ai_role="AI",
            fixed_questions=["Q1", "Q2", "Q3"],
            expires_at=past_time
        )
        assert session.is_expired()

    def test_is_expired_no_expiration(self):
        """만료 시간 없는 세션"""
        session = SessionState(
            session_id="session-no-exp",
            user_id=1,
            subject_id=1,
            my_role="User",
            ai_role="AI",
            fixed_questions=["Q1", "Q2", "Q3"],
            expires_at=None
        )
        assert not session.is_expired()

    def test_get_ai_turn_number(self, sample_session_state):
        """다음 AI 턴 번호"""
        assert sample_session_state.get_ai_turn_number() == 1
        sample_session_state.ai_turn_count = 2
        assert sample_session_state.get_ai_turn_number() == 3

    def test_should_use_fixed_question(self, sample_session_state):
        """고정 질문 턴 판단"""
        # 턴 1
        sample_session_state.ai_turn_count = 0
        assert sample_session_state.should_use_fixed_question() is True

        # 턴 2 (동적 질문)
        sample_session_state.ai_turn_count = 1
        assert sample_session_state.should_use_fixed_question() is False

        # 턴 4
        sample_session_state.ai_turn_count = 3
        assert sample_session_state.should_use_fixed_question() is True

        # 턴 7
        sample_session_state.ai_turn_count = 6
        assert sample_session_state.should_use_fixed_question() is True

    def test_get_fixed_question_index(self, sample_session_state):
        """고정 질문 인덱스"""
        # 턴 1 → 인덱스 0
        sample_session_state.ai_turn_count = 0
        assert sample_session_state.get_fixed_question_index() == 0

        # 턴 4 → 인덱스 1
        sample_session_state.ai_turn_count = 3
        assert sample_session_state.get_fixed_question_index() == 1

        # 턴 7 → 인덱스 2
        sample_session_state.ai_turn_count = 6
        assert sample_session_state.get_fixed_question_index() == 2

        # 턴 2 (동적) → None
        sample_session_state.ai_turn_count = 1
        assert sample_session_state.get_fixed_question_index() is None

    def test_has_reached_turn_limit(self, sample_session_state):
        """턴 제한 도달 여부"""
        # 10턴 제한, 현재 5턴
        sample_session_state.ai_turn_count = 5
        sample_session_state.user_turn_count = 5
        assert sample_session_state.has_reached_turn_limit(5) is True

        # 제한 미도달
        sample_session_state.ai_turn_count = 2
        sample_session_state.user_turn_count = 2
        assert sample_session_state.has_reached_turn_limit(5) is False

    def test_retry_management(self, sample_session_state):
        """재시도 관리"""
        assert sample_session_state.can_retry() is True

        # 재시도 횟수 증가
        sample_session_state.increment_retry_count()
        assert sample_session_state.current_question_retry_count == 1
        assert sample_session_state.can_retry() is True

        # 최대 재시도 횟수 초과
        sample_session_state.current_question_retry_count = 3
        assert sample_session_state.can_retry() is False

        # 재시도 횟수 초기화
        sample_session_state.reset_retry_count()
        assert sample_session_state.current_question_retry_count == 0


class TestSessionManager:
    """SessionManager 테스트"""

    def test_create_session_success(self, session_manager_instance):
        """세션 생성 성공"""
        session = session_manager_instance.create_session(
            session_id="test-session",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        assert session.session_id == "test-session"
        assert session.user_id == 1

    def test_create_session_duplicate(self, session_manager_instance):
        """세션 중복 생성 실패"""
        session_manager_instance.create_session(
            session_id="duplicate",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        with pytest.raises(ValueError):
            session_manager_instance.create_session(
                session_id="duplicate",
                user_id=2,
                subject_id=2,
                my_role="Engineer",
                ai_role="Lead",
                fixed_questions=["Q1", "Q2", "Q3"]
            )

    def test_create_session_invalid_questions(self, session_manager_instance):
        """고정 질문 개수 검증"""
        with pytest.raises(ValueError):
            session_manager_instance.create_session(
                session_id="invalid",
                user_id=1,
                subject_id=1,
                my_role="Engineer",
                ai_role="Lead",
                fixed_questions=["Q1", "Q2"]  # 2개만
            )

    def test_get_session(self, session_manager_instance):
        """세션 조회"""
        session_manager_instance.create_session(
            session_id="get-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        session = session_manager_instance.get_session("get-test")
        assert session is not None
        assert session.session_id == "get-test"

    def test_get_session_not_found(self, session_manager_instance):
        """존재하지 않는 세션 조회"""
        session = session_manager_instance.get_session("non-existent")
        assert session is None

    def test_end_session_finished(self, session_manager_instance):
        """세션 정상 종료"""
        session_manager_instance.create_session(
            session_id="end-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        session_manager_instance.end_session("end-test", "user_end")
        session = session_manager_instance.get_session("end-test")
        assert session.status == SessionStatus.FINISHED

    def test_end_session_error(self, session_manager_instance):
        """세션 오류로 종료"""
        session_manager_instance.create_session(
            session_id="error-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        session_manager_instance.end_session("error-test", "error")
        session = session_manager_instance.get_session("error-test")
        assert session.status == SessionStatus.ERROR

    def test_cleanup(self, session_manager_instance):
        """세션 메모리 정리"""
        session_manager_instance.create_session(
            session_id="cleanup-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        session_manager_instance.cleanup("cleanup-test")
        session = session_manager_instance.get_session("cleanup-test")
        assert session is None

    def test_get_active_sessions_count(self, session_manager_instance):
        """활성 세션 개수"""
        session_manager_instance.create_session(
            session_id="active-1",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        session_manager_instance.create_session(
            session_id="active-2",
            user_id=2,
            subject_id=2,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        assert session_manager_instance.get_active_sessions_count() == 2

        session_manager_instance.end_session("active-1", "user_end")
        assert session_manager_instance.get_active_sessions_count() == 1

    def test_get_all_sessions_count(self, session_manager_instance):
        """전체 세션 개수"""
        session_manager_instance.create_session(
            session_id="all-1",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        assert session_manager_instance.get_all_sessions_count() == 1


class TestUtcNowFunction:
    """_get_utc_now() 함수 테스트"""

    def test_get_utc_now_timezone_aware(self):
        """UTC 시각이 timezone-aware"""
        now = _get_utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo.utcoffset(now).total_seconds() == 0

    def test_get_utc_now_recent(self):
        """UTC 시각이 현재 시각"""
        before = datetime.now(timezone.utc)
        now = _get_utc_now()
        after = datetime.now(timezone.utc)
        assert before <= now <= after
