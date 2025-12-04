"""
Test Core Components
====================

추가 핵심 컴포넌트 테스트:
- SessionCreationBuilder
- RoleplayingModels
- 통합 워크플로우
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.roleplaying.core.session_creation_builder import (
    SessionCreationRequest,
    create_session_builder
)


class TestSessionCreationBuilder:
    """세션 생성 빌더 패턴 테스트"""

    def test_builder_basic_flow(self):
        """기본 빌더 워크플로우"""
        builder = SessionCreationRequest()

        builder.with_session_id("test-123")
        assert builder.session_id == "test-123"

        builder.with_user_id(1)
        assert builder.user_id == 1

        builder.with_subject_id(1)
        assert builder.subject_id == 1

        builder.with_roles("Engineer", "Lead")
        assert builder.my_role == "Engineer"
        assert builder.ai_role == "Lead"

        builder.with_fixed_questions(["Q1", "Q2", "Q3"])
        assert len(builder.fixed_questions) == 3

    def test_builder_fluent_api(self):
        """빌더 Fluent API 체이닝"""
        builder = (
            SessionCreationRequest()
            .with_session_id("fluent-123")
            .with_user_id(1)
            .with_subject_id(1)
            .with_roles("Engineer", "Lead")
            .with_fixed_questions(["Q1", "Q2", "Q3"])
            .with_expiration(datetime.now(timezone.utc) + timedelta(hours=1))
        )

        assert builder.session_id == "fluent-123"
        assert builder.user_id == 1
        assert builder.expires_at is not None

    def test_builder_validation_missing_session_id(self):
        """빌더: 필수 필드 누락 (session_id)"""
        builder = (
            SessionCreationRequest()
            .with_user_id(1)
            .with_subject_id(1)
            .with_roles("Engineer", "Lead")
            .with_fixed_questions(["Q1", "Q2", "Q3"])
        )

        with pytest.raises(ValueError):
            builder.validate()

    def test_builder_validation_missing_user_id(self):
        """빌더: 필수 필드 누락 (user_id)"""
        builder = (
            SessionCreationRequest()
            .with_session_id("test-123")
            .with_subject_id(1)
            .with_roles("Engineer", "Lead")
            .with_fixed_questions(["Q1", "Q2", "Q3"])
        )

        with pytest.raises(ValueError):
            builder.validate()

    def test_builder_validation_invalid_questions(self):
        """빌더: 고정 질문 개수 검증"""
        # Error is raised in with_fixed_questions(), not in validate()
        with pytest.raises(ValueError):
            SessionCreationRequest()\
                .with_session_id("test-123")\
                .with_user_id(1)\
                .with_subject_id(1)\
                .with_roles("Engineer", "Lead")\
                .with_fixed_questions(["Q1", "Q2"])  # 2개만

    def test_builder_validation_empty_role(self):
        """빌더: 빈 역할 검증"""
        builder = (
            SessionCreationRequest()
            .with_session_id("test-123")
            .with_user_id(1)
            .with_subject_id(1)
            .with_roles("", "Lead")  # 빈 역할
            .with_fixed_questions(["Q1", "Q2", "Q3"])
        )

        with pytest.raises(ValueError):
            builder.validate()

    def test_builder_factory(self):
        """빌더 팩토리 함수"""
        builder = create_session_builder()
        assert isinstance(builder, SessionCreationRequest)
        assert builder.session_id is None


class TestIntegrationSessionWorkflow:
    """세션 통합 워크플로우 테스트"""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """세션 전체 생명주기"""
        from app.roleplaying.core.session_manager_base import session_manager
        from app.roleplaying.core.session_message_handler import SessionMessageHandler
        from app.roleplaying.core.session_audio_handler import SessionAudioHandler

        # Clear global session state
        session_manager._sessions.clear()
        session_manager._session_locks.clear()

        # 1. 세션 생성
        session = session_manager.create_session(
            session_id="lifecycle-123",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )
        assert session.session_id == "lifecycle-123"

        # 2. 오디오 추가
        audio_chunk = b'\x00' * 1024
        SessionAudioHandler.append_audio_chunk("lifecycle-123", audio_chunk)
        SessionAudioHandler.append_audio_chunk("lifecycle-123", audio_chunk)

        # 3. 메시지 추가
        await SessionMessageHandler.append_message_async(
            session_id="lifecycle-123",
            speaker="ai",
            text="Hello, how can I help?",
            is_fixed_question=True
        )

        # 4. 발화 인덱스 증가
        idx = await SessionMessageHandler.increment_utterance_index_async("lifecycle-123")
        assert idx == 1

        # 5. 오디오 반환
        audio = SessionAudioHandler.get_current_audio("lifecycle-123")
        assert len(audio) == 2048  # 2개 청크

        # 6. 세션 상태 확인
        session = session_manager.get_session("lifecycle-123")
        assert len(session.history) == 1
        assert session.ai_turn_count == 1
        assert session.utterance_index == 1

        # 7. 세션 종료
        session_manager.end_session("lifecycle-123", "user_end")
        session = session_manager.get_session("lifecycle-123")
        assert session.status.value == "FINISHED"

        # 8. 메모리 정리
        session_manager.cleanup("lifecycle-123")
        session = session_manager.get_session("lifecycle-123")
        assert session is None

        # Clean up after test
        session_manager._sessions.clear()
        session_manager._session_locks.clear()

    @pytest.mark.asyncio
    async def test_multiple_turns_workflow(self):
        """다중 턴 워크플로우"""
        from app.roleplaying.core.session_manager_base import session_manager
        from app.roleplaying.core.session_message_handler import SessionMessageHandler

        # Clear global session state
        session_manager._sessions.clear()
        session_manager._session_locks.clear()

        session = session_manager.create_session(
            session_id="turns-123",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        # Check initial state: Turn 1 should use fixed question (ai_turn_count == 0)
        assert session.should_use_fixed_question() is True
        assert session.get_fixed_question_index() == 0

        # 턴 1: AI 고정 질문
        await SessionMessageHandler.append_message_async(
            session_id="turns-123",
            speaker="ai",
            text="Q1",
            is_fixed_question=True
        )
        # After message, ai_turn_count == 1 (Turn 2)

        # 턴 2: 사용자 응답
        await SessionMessageHandler.append_message_async(
            session_id="turns-123",
            speaker="user",
            text="Answer to Q1"
        )

        # 턴 3: AI 동적 질문
        # ai_turn_count is still 1, check if turn 2 (ai_turn_count == 1) should use fixed
        assert session.should_use_fixed_question() is False

        await SessionMessageHandler.append_message_async(
            session_id="turns-123",
            speaker="ai",
            text="Follow-up question"
        )
        # After message, ai_turn_count == 2 (Turn 3)

        # 턴 4: 사용자 응답
        await SessionMessageHandler.append_message_async(
            session_id="turns-123",
            speaker="user",
            text="Answer to follow-up"
        )

        # 턴 5: AI 고정 질문
        # ai_turn_count is still 2, manually increment to check turn 4
        session.ai_turn_count += 1
        assert session.should_use_fixed_question() is True
        assert session.get_fixed_question_index() == 1

        # 최종 확인
        session = session_manager.get_session("turns-123")
        assert len(session.history) == 4
        assert session.ai_turn_count == 3
        assert session.user_turn_count == 2

        # Clean up after test
        session_manager._sessions.clear()
        session_manager._session_locks.clear()

    @pytest.mark.asyncio
    async def test_retry_workflow(self):
        """재시도 워크플로우"""
        from app.roleplaying.core.session_manager_base import session_manager

        # Clear global session state
        session_manager._sessions.clear()
        session_manager._session_locks.clear()

        session = session_manager.create_session(
            session_id="retry-123",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        # 첫 시도 실패
        session.increment_retry_count()
        assert session.current_question_retry_count == 1
        assert session.can_retry() is True

        # 두 번째 시도 실패
        session.increment_retry_count()
        assert session.current_question_retry_count == 2
        assert session.can_retry() is True

        # 세 번째 시도 실패
        session.increment_retry_count()
        assert session.current_question_retry_count == 3
        assert session.can_retry() is False

        # 다음 질문으로 진행
        session.reset_retry_count()
        assert session.current_question_retry_count == 0
        assert session.can_retry() is True

        # Clean up after test
        session_manager._sessions.clear()
        session_manager._session_locks.clear()
