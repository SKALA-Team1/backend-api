"""
Test User Utterance Processor
=============================

발화 처리 모듈 테스트:
- SilenceDetector (침묵 감지)
- UtteranceProcessor (STT + 히스토리)
- UtterancePersistence (Spring 2 저장)
- TextUtteranceProcessor (텍스트 기반 발화)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.roleplaying.processing.user_utterance_processor import (
    SilenceDetector,
    UtteranceProcessor,
    UtterancePersistence,
    TextUtteranceProcessor
)
from app.roleplaying.core.session_manager_base import session_manager


@pytest.fixture
def clean_sessions():
    """테스트 전후 세션 정리"""
    session_manager._sessions.clear()
    session_manager._session_locks.clear()
    yield session_manager
    session_manager._sessions.clear()
    session_manager._session_locks.clear()


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


@pytest.fixture
def sample_audio():
    """샘플 오디오 데이터"""
    return b'\x00\x01\x02\x03' * 256  # 1024 bytes


class TestSilenceDetector:
    """침묵 감지 테스트"""

    def test_is_silence_empty_text(self):
        """빈 텍스트는 침묵"""
        assert SilenceDetector.is_silence("") is True

    def test_is_silence_none_text(self):
        """None은 침묵"""
        assert SilenceDetector.is_silence(None) is True

    def test_is_silence_whitespace_only(self):
        """공백만 있는 텍스트는 침묵"""
        assert SilenceDetector.is_silence("   ") is True

    def test_is_silence_very_short_text(self):
        """매우 짧은 텍스트는 침묵"""
        assert SilenceDetector.is_silence("hi", min_length=5) is True

    def test_is_not_silence_normal_text(self):
        """정상 텍스트는 침묵이 아님"""
        assert SilenceDetector.is_silence("This is a normal sentence") is False

    def test_is_not_silence_minimum_length(self):
        """최소 길이 이상이면 침묵 아님"""
        assert SilenceDetector.is_silence("hello", min_length=3) is False

    def test_detect_with_logging_silence(self, caplog):
        """로깅과 함께 침묵 감지"""
        result = SilenceDetector.detect_with_logging(None, audio_length=1024)
        assert result is True
        assert "Silence detected" in caplog.text

    def test_detect_with_logging_with_audio(self, caplog):
        """오디오 길이와 함께 침묵 감지"""
        result = SilenceDetector.detect_with_logging("", audio_length=2048)
        assert result is True
        assert "2048 bytes" in caplog.text

    def test_detect_with_logging_speech(self):
        """음성 감지됨"""
        result = SilenceDetector.detect_with_logging("Hello, world!")
        assert result is False


class TestUtteranceProcessor:
    """발화 처리 테스트"""

    @pytest.mark.asyncio
    async def test_process_stt_success(self, sample_audio):
        """STT 처리 성공"""
        with patch('app.roleplaying.services.stt.speech_to_text_service.stt_service') as mock_stt:
            mock_stt.transcribe = AsyncMock(return_value="Hello, how are you?")

            result = await UtteranceProcessor.process_stt(sample_audio)
            assert result == "Hello, how are you?"
            mock_stt.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_stt_silence(self, sample_audio):
        """STT 침묵 감지"""
        with patch('app.roleplaying.services.stt.speech_to_text_service.stt_service') as mock_stt:
            mock_stt.transcribe = AsyncMock(return_value="")

            result = await UtteranceProcessor.process_stt(sample_audio)
            assert result is None

    @pytest.mark.asyncio
    async def test_process_stt_error(self, sample_audio):
        """STT 에러 처리"""
        with patch('app.roleplaying.services.stt.speech_to_text_service.stt_service') as mock_stt:
            mock_stt.transcribe = AsyncMock(side_effect=Exception("STT service error"))

            result = await UtteranceProcessor.process_stt(sample_audio)
            assert result is None

    @pytest.mark.asyncio
    async def test_save_to_history_success(self, sample_session):
        """히스토리 저장 성공"""
        await UtteranceProcessor.save_to_history(
            session_id="test-session",
            speaker="user",
            text="Hello, world!",
            audio_s3_url="s3://bucket/audio.wav"
        )

        # 세션에 메시지가 추가되었는지 확인
        session = session_manager.get_session("test-session")
        assert len(session.history) == 1
        assert session.history[0].text == "Hello, world!"
        assert session.history[0].speaker == "user"

    @pytest.mark.asyncio
    async def test_save_to_history_invalid_session(self):
        """존재하지 않는 세션에 저장"""
        with pytest.raises(ValueError):
            await UtteranceProcessor.save_to_history(
                session_id="non-existent",
                speaker="user",
                text="Hello"
            )


class TestUtterancePersistence:
    """발화 저장 테스트"""

    @pytest.mark.asyncio
    async def test_schedule_save(self):
        """비동기 저장 스케줄"""
        # schedule_save는 asyncio.create_task를 사용하므로 비동기 컨텍스트에서만 작동
        # 스케줄만 되고 실행되지는 않음
        with patch('app.roleplaying.processing.user_utterance_processor.spring2_client'):
            UtterancePersistence.schedule_save(
                session_id="test-session",
                text="Hello",
                utterance_index=1,
                speaker="user"
            )
            # 예외 없이 실행됨

    @pytest.mark.asyncio
    async def test_save_with_retry_success(self):
        """재시도 로직으로 저장 성공 (첫 시도)"""
        with patch('app.roleplaying.processing.user_utterance_processor.spring2_client') as mock_spring2:
            mock_spring2.save_utterance = AsyncMock(return_value=None)

            await UtterancePersistence._save_with_retry(
                session_id="test-session",
                text="Hello",
                utterance_index=1,
                speaker="user",
                max_retries=3
            )

            mock_spring2.save_utterance.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_with_retry_speaker_normalization(self):
        """발화자 정규화"""
        with patch('app.roleplaying.processing.user_utterance_processor.spring2_client') as mock_spring2:
            mock_spring2.save_utterance = AsyncMock(return_value=None)

            await UtterancePersistence._save_with_retry(
                session_id="test-session",
                text="Hello",
                utterance_index=1,
                speaker="USER",  # 대문자
                max_retries=1
            )

            # 호출 시 speaker가 소문자로 변환됨
            call_args = mock_spring2.save_utterance.call_args
            assert call_args[1]['speaker'] == 'user'

    @pytest.mark.asyncio
    async def test_save_with_retry_retry_on_failure(self):
        """실패 시 재시도"""
        with patch('app.roleplaying.processing.user_utterance_processor.spring2_client') as mock_spring2:
            # 첫 번째는 실패, 두 번째는 성공
            mock_spring2.save_utterance = AsyncMock(
                side_effect=[Exception("Error"), None]
            )

            await UtterancePersistence._save_with_retry(
                session_id="test-session",
                text="Hello",
                utterance_index=1,
                speaker="user",
                max_retries=2
            )

            # 두 번 시도함
            assert mock_spring2.save_utterance.call_count == 2

    @pytest.mark.asyncio
    async def test_save_with_retry_max_attempts_exceeded(self):
        """최대 재시도 초과"""
        with patch('app.roleplaying.processing.user_utterance_processor.spring2_client') as mock_spring2:
            mock_spring2.save_utterance = AsyncMock(side_effect=Exception("Network error"))

            # 예외를 발생시키지 않고 로깅만 함
            await UtterancePersistence._save_with_retry(
                session_id="test-session",
                text="Hello",
                utterance_index=1,
                speaker="user",
                max_retries=2
            )

            # 2번 재시도함
            assert mock_spring2.save_utterance.call_count == 2


class TestTextUtteranceProcessor:
    """텍스트 기반 발화 처리 테스트"""

    @pytest.mark.asyncio
    async def test_process_and_save_success(self, sample_session):
        """텍스트 발화 처리 및 저장 성공"""
        await TextUtteranceProcessor.process_and_save(
            session_id="test-session",
            user_text="This is my answer",
            utterance_index=1
        )

        # 히스토리에 추가됨
        session = session_manager.get_session("test-session")
        assert len(session.history) == 1
        assert session.history[0].text == "This is my answer"
        assert session.history[0].speaker == "user"

    @pytest.mark.asyncio
    async def test_process_and_save_invalid_session(self):
        """존재하지 않는 세션"""
        with pytest.raises(ValueError):
            await TextUtteranceProcessor.process_and_save(
                session_id="non-existent",
                user_text="Hello",
                utterance_index=1
            )

    @pytest.mark.asyncio
    async def test_process_and_save_long_text(self, sample_session):
        """긴 텍스트 처리"""
        long_text = "A" * 1000

        await TextUtteranceProcessor.process_and_save(
            session_id="test-session",
            user_text=long_text,
            utterance_index=1
        )

        session = session_manager.get_session("test-session")
        assert session.history[0].text == long_text


class TestUtteranceWorkflow:
    """발화 처리 통합 워크플로우 테스트"""

    @pytest.mark.asyncio
    async def test_complete_audio_workflow(self, sample_session, sample_audio):
        """완전한 오디오 발화 워크플로우"""
        with patch('app.roleplaying.services.stt.speech_to_text_service.stt_service') as mock_stt:
            mock_stt.transcribe = AsyncMock(return_value="This is a good question")

            # 1. STT 처리
            text = await UtteranceProcessor.process_stt(sample_audio)
            assert text == "This is a good question"

            # 2. 침묵 아님 확인
            assert SilenceDetector.is_silence(text) is False

            # 3. 히스토리에 저장
            await UtteranceProcessor.save_to_history(
                session_id="test-session",
                speaker="user",
                text=text,
                audio_s3_url="s3://bucket/audio.wav"
            )

            # 4. 세션에 메시지 추가 확인
            session = session_manager.get_session("test-session")
            assert len(session.history) == 1
            assert session.history[0].speaker == "user"
            assert session.history[0].text == "This is a good question"

    @pytest.mark.asyncio
    async def test_silence_handling_workflow(self, sample_session, sample_audio):
        """침묵 처리 워크플로우"""
        with patch('app.roleplaying.services.stt.speech_to_text_service.stt_service') as mock_stt:
            mock_stt.transcribe = AsyncMock(return_value="")

            # 1. STT 처리 (침묵)
            text = await UtteranceProcessor.process_stt(sample_audio)
            assert text is None

            # 2. 침묵 감지 확인
            assert SilenceDetector.is_silence(None) is True

            # 3. 히스토리에 저장하지 않음
            session = session_manager.get_session("test-session")
            assert len(session.history) == 0
