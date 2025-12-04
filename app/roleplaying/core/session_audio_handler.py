"""
Session Audio Handler
====================

목적: 세션의 오디오 버퍼 관리
━━━━━━━━━━━━━━━━━━━━━━━━━

책임:
    - 오디오 청크 누적
    - 누적된 오디오 반환 및 버퍼 초기화
    - 오디오 버퍼 관리

메서드:
    - append_audio_chunk(): 오디오 청크 추가
    - get_current_audio(): 오디오 반환 후 버퍼 초기화
    - clear_audio_buffer(): 오디오 버퍼 초기화
"""

import logging

from app.roleplaying.core.session_manager_base import session_manager

logger = logging.getLogger(__name__)


class SessionAudioHandler:
    """세션 오디오 처리"""

    @staticmethod
    def append_audio_chunk(session_id: str, chunk: bytes) -> None:
        """
        현재 발화에 오디오 청크 추가

        Args:
            session_id: 세션 ID
            chunk: 오디오 청크 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.current_utterance_audio += chunk
        logger.debug(
            f"Audio chunk added to session {session_id}: "
            f"{len(chunk)} bytes (total: {len(session.current_utterance_audio)} bytes)"
        )

    @staticmethod
    def get_current_audio(session_id: str) -> bytes:
        """
        현재 발화 오디오 반환 후 버퍼 초기화

        Args:
            session_id: 세션 ID

        Returns:
            누적된 오디오 데이터 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        audio = session.current_utterance_audio
        session.current_utterance_audio = b""  # 버퍼 초기화

        logger.debug(f"Audio retrieved from session {session_id}: {len(audio)} bytes")
        return audio

    @staticmethod
    def clear_audio_buffer(session_id: str) -> None:
        """
        현재 발화 오디오 버퍼 초기화

        Args:
            session_id: 세션 ID

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.current_utterance_audio = b""
        logger.debug(f"Audio buffer cleared for session {session_id}")
