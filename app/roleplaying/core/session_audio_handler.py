"""
Session Audio Handler
====================

목적: 세션의 오디오 버퍼 관리 (스레드 안전)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

책임:
    - 오디오 청크 누적 (Lock으로 보호)
    - 누적된 오디오 반환 및 버퍼 초기화
    - 오디오 버퍼 관리

메서드:
    - append_audio_chunk_async(): 오디오 청크 추가 (비동기)
    - get_current_audio_async(): 오디오 반환 후 버퍼 초기화 (비동기)
    - clear_audio_buffer_async(): 오디오 버퍼 초기화 (비동기)

스레드 안전성:
    - 모든 버퍼 접근을 asyncio.Lock으로 보호
    - race condition 방지 (동시 AUDIO_CHUNK와 UTTERANCE_END)
"""

import logging

from app.roleplaying.core.session_manager_base import session_manager

logger = logging.getLogger(__name__)


class SessionAudioHandler:
    """세션 오디오 처리 (Lock으로 보호된 버퍼 관리)"""

    @staticmethod
    async def append_audio_chunk_async(session_id: str, chunk: bytes) -> None:
        """
        현재 발화에 오디오 청크 추가 (스레드 안전)

        Args:
            session_id: 세션 ID
            chunk: 오디오 청크 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        lock = session_manager._get_lock(session_id)
        async with lock:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            session.current_utterance_audio += chunk
            logger.debug(
                f"Audio chunk added: {len(chunk)} bytes "
                f"(total: {len(session.current_utterance_audio)} bytes)"
            )

    @staticmethod
    async def get_current_audio_async(session_id: str) -> bytes:
        """
        현재 발화 오디오 반환 후 버퍼 초기화 (스레드 안전)

        Args:
            session_id: 세션 ID

        Returns:
            누적된 오디오 데이터 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        lock = session_manager._get_lock(session_id)
        async with lock:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            audio = session.current_utterance_audio
            session.current_utterance_audio = b""

            logger.debug(f"Audio retrieved: {len(audio)} bytes")
            return audio

    @staticmethod
    async def clear_audio_buffer_async(session_id: str) -> None:
        """
        현재 발화 오디오 버퍼 초기화 (스레드 안전)

        Args:
            session_id: 세션 ID

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        lock = session_manager._get_lock(session_id)
        async with lock:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            session.current_utterance_audio = b""
            logger.debug("Audio buffer cleared")
