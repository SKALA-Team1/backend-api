"""
Test Session Handlers
=====================

핸들러 계층 테스트:
- SessionMessageHandler (메시지 추가, 발화 인덱스)
- SessionAudioHandler (오디오 청크, 반환, 초기화)
"""

import pytest
import asyncio

from app.roleplaying.core.session_message_handler import SessionMessageHandler
from app.roleplaying.core.session_audio_handler import SessionAudioHandler
from app.roleplaying.core.session_manager_base import session_manager


@pytest.fixture
def clean_session():
    """
    Clean session state for each test.

    Handlers use the global session_manager, so we work with that.
    """
    # Clear any existing sessions before test
    session_manager._sessions.clear()
    session_manager._session_locks.clear()

    yield session_manager

    # Clean up after test
    session_manager._sessions.clear()
    session_manager._session_locks.clear()


class TestSessionMessageHandler:
    """메시지 핸들러 테스트"""

    @pytest.mark.asyncio
    async def test_append_message_user(self, clean_session):
        """사용자 메시지 추가"""
        clean_session.create_session(
            session_id="msg-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        await SessionMessageHandler.append_message_async(
            session_id="msg-test",
            speaker="user",
            text="I need help"
        )

        updated_session = clean_session.get_session("msg-test")
        assert len(updated_session.history) == 1
        assert updated_session.history[0].speaker == "user"
        assert updated_session.history[0].text == "I need help"
        assert updated_session.user_turn_count == 1

    @pytest.mark.asyncio
    async def test_append_message_ai(self, clean_session):
        """AI 메시지 추가"""
        clean_session.create_session(
            session_id="ai-msg-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        await SessionMessageHandler.append_message_async(
            session_id="ai-msg-test",
            speaker="ai",
            text="What's your approach?",
            is_fixed_question=True
        )

        updated_session = clean_session.get_session("ai-msg-test")
        assert len(updated_session.history) == 1
        assert updated_session.history[0].speaker == "ai"
        assert updated_session.history[0].is_fixed_question is True
        assert updated_session.ai_turn_count == 1

    @pytest.mark.asyncio
    async def test_append_message_with_audio_url(self, clean_session):
        """오디오 URL 포함 메시지"""
        clean_session.create_session(
            session_id="audio-url-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        await SessionMessageHandler.append_message_async(
            session_id="audio-url-test",
            speaker="user",
            text="Hello",
            audio_s3_url="s3://bucket/audio.wav"
        )

        updated_session = clean_session.get_session("audio-url-test")
        assert updated_session.history[0].audio_s3_url == "s3://bucket/audio.wav"

    @pytest.mark.asyncio
    async def test_append_message_session_not_found(self, clean_session):
        """존재하지 않는 세션에 메시지 추가"""
        with pytest.raises(ValueError):
            await SessionMessageHandler.append_message_async(
                session_id="non-existent",
                speaker="user",
                text="Hello"
            )

    @pytest.mark.asyncio
    async def test_increment_utterance_index(self, clean_session):
        """발화 인덱스 증가"""
        clean_session.create_session(
            session_id="utterance-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        index1 = await SessionMessageHandler.increment_utterance_index_async("utterance-test")
        assert index1 == 1

        index2 = await SessionMessageHandler.increment_utterance_index_async("utterance-test")
        assert index2 == 2

    @pytest.mark.asyncio
    async def test_increment_utterance_index_not_found(self, clean_session):
        """존재하지 않는 세션의 발화 인덱스"""
        with pytest.raises(ValueError):
            await SessionMessageHandler.increment_utterance_index_async("non-existent")

    @pytest.mark.asyncio
    async def test_message_history_order(self, clean_session):
        """메시지 히스토리 순서"""
        clean_session.create_session(
            session_id="order-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        await SessionMessageHandler.append_message_async(
            session_id="order-test",
            speaker="ai",
            text="Hi, I'm your AI"
        )

        await SessionMessageHandler.append_message_async(
            session_id="order-test",
            speaker="user",
            text="Thanks for the help"
        )

        session = clean_session.get_session("order-test")
        assert len(session.history) == 2
        assert session.history[0].speaker == "ai"
        assert session.history[1].speaker == "user"


class TestSessionAudioHandler:
    """오디오 핸들러 테스트"""

    def test_append_audio_chunk(self, clean_session, sample_audio_chunk):
        """오디오 청크 추가"""
        clean_session.create_session(
            session_id="audio-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        SessionAudioHandler.append_audio_chunk("audio-test", sample_audio_chunk)
        session = clean_session.get_session("audio-test")
        assert len(session.current_utterance_audio) == 1024

    def test_append_multiple_audio_chunks(self, clean_session, sample_audio_chunk):
        """여러 오디오 청크 추가"""
        clean_session.create_session(
            session_id="multi-audio-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        for _ in range(3):
            SessionAudioHandler.append_audio_chunk("multi-audio-test", sample_audio_chunk)

        session = clean_session.get_session("multi-audio-test")
        assert len(session.current_utterance_audio) == 3072  # 1024 * 3

    def test_get_current_audio(self, clean_session, sample_audio_chunk):
        """오디오 반환 및 버퍼 초기화"""
        clean_session.create_session(
            session_id="get-audio-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        SessionAudioHandler.append_audio_chunk("get-audio-test", sample_audio_chunk)
        audio = SessionAudioHandler.get_current_audio("get-audio-test")

        assert len(audio) == 1024
        # 버퍼가 초기화되었는지 확인
        session = clean_session.get_session("get-audio-test")
        assert len(session.current_utterance_audio) == 0

    def test_get_current_audio_empty_buffer(self, clean_session):
        """빈 버퍼에서 오디오 반환"""
        clean_session.create_session(
            session_id="empty-audio-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        audio = SessionAudioHandler.get_current_audio("empty-audio-test")
        assert len(audio) == 0

    def test_clear_audio_buffer(self, clean_session, sample_audio_chunk):
        """오디오 버퍼 초기화"""
        clean_session.create_session(
            session_id="clear-audio-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        SessionAudioHandler.append_audio_chunk("clear-audio-test", sample_audio_chunk)
        session = clean_session.get_session("clear-audio-test")
        assert len(session.current_utterance_audio) == 1024

        SessionAudioHandler.clear_audio_buffer("clear-audio-test")
        session = clean_session.get_session("clear-audio-test")
        assert len(session.current_utterance_audio) == 0

    def test_append_audio_chunk_session_not_found(self, clean_session, sample_audio_chunk):
        """존재하지 않는 세션에 오디오 추가"""
        with pytest.raises(ValueError):
            SessionAudioHandler.append_audio_chunk("non-existent", sample_audio_chunk)

    def test_get_current_audio_session_not_found(self, clean_session):
        """존재하지 않는 세션에서 오디오 반환"""
        with pytest.raises(ValueError):
            SessionAudioHandler.get_current_audio("non-existent")

    def test_clear_audio_buffer_session_not_found(self, clean_session):
        """존재하지 않는 세션 오디오 초기화"""
        with pytest.raises(ValueError):
            SessionAudioHandler.clear_audio_buffer("non-existent")

    def test_audio_accumulation_workflow(self, clean_session, sample_audio_chunk):
        """오디오 누적 워크플로우"""
        clean_session.create_session(
            session_id="workflow-test",
            user_id=1,
            subject_id=1,
            my_role="Engineer",
            ai_role="Lead",
            fixed_questions=["Q1", "Q2", "Q3"]
        )

        # 청크 10개 추가
        for _ in range(10):
            SessionAudioHandler.append_audio_chunk("workflow-test", sample_audio_chunk)

        session = clean_session.get_session("workflow-test")
        assert len(session.current_utterance_audio) == 10240

        # 오디오 반환 (버퍼 초기화)
        audio = SessionAudioHandler.get_current_audio("workflow-test")
        assert len(audio) == 10240

        # 버퍼 확인
        session = clean_session.get_session("workflow-test")
        assert len(session.current_utterance_audio) == 0
