"""
STT Service Facade (Deepgram)
=============================

역할:
- 배치 및 스트리밍 STT 서비스 제공
- 각 모듈 간의 조정 (AudioConverter, BatchSTTEngine, StreamingSTTManager)
- 스트리밍 세션 라이프사이클 관리
"""

import logging
from typing import Optional

from app.config import settings
from app.roleplaying.services.audio_converter import AudioConverter
from app.roleplaying.services.batch_stt_engine import BatchSTTEngine
from app.roleplaying.services.streaming_stt_manager import (
    StreamingSTTManager,
    StreamingSTTSession,
)

logger = logging.getLogger(__name__)


class STTService:
    """
    STT 서비스 Facade

    배치 모드와 스트리밍 모드 모두 지원:
    1. 배치: transcribe() - 전체 오디오 처리 후 최종 결과 반환
    2. 스트리밍: create_streaming_session() - 실시간 부분 결과 반환
    """

    def __init__(self):
        """STT 서비스 초기화"""
        self.batch_engine = BatchSTTEngine()
        self.streaming_manager = StreamingSTTManager()
        logger.info("STTService initialized with modular architecture")

    async def transcribe(self, audio_data: bytes) -> str:
        """
        배치 모드: 오디오를 텍스트로 변환

        Args:
            audio_data: PCM 16-bit mono 오디오

        Returns:
            인식된 텍스트
        """
        if not audio_data:
            logger.warning("Empty audio data, returning empty string")
            return ""

        logger.debug("Transcribing audio (%d bytes) via batch engine", len(audio_data))
        return await self.batch_engine.transcribe(audio_data)

    async def create_streaming_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 STT 세션 생성 (SDK 3.x: 비동기)

        ✅ SDK 3.x 변경: create_session()이 비동기로 변경됨

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession 객체
        """
        logger.debug(f"Creating streaming session: {session_id}")
        return await self.streaming_manager.create_session(session_id)

    async def process_chunk(
        self, session_id: str, audio_chunk: bytes
    ) -> Optional[str]:
        """
        스트리밍 모드: 청크 처리 및 부분 결과 반환

        Args:
            session_id: 스트리밍 세션 ID
            audio_chunk: 오디오 청크 바이너리

        Returns:
            부분 STT 결과 (있으면)
        """
        return await self.streaming_manager.process_chunk(session_id, audio_chunk)

    async def finalize_streaming(self, session_id: str) -> str:
        """
        스트리밍 세션 종료 및 최종 결과 반환

        Args:
            session_id: 스트리밍 세션 ID

        Returns:
            최종 STT 결과
        """
        logger.debug(f"Finalizing streaming session: {session_id}")
        return await self.streaming_manager.finalize_session(session_id)

    async def cleanup(self, session_id: str) -> None:
        """
        스트리밍 세션 강제 정리 (비정상 종료 시)

        finalize_streaming()과 다르게, 최종 결과를 기다리지 않고 즉시 리소스를 정리합니다.
        예상치 못한 클라이언트 연결 해제 시 사용하세요.

        Args:
            session_id: 스트리밍 세션 ID
        """
        logger.debug(f"Cleaning up streaming session: {session_id}")
        await self.streaming_manager.cleanup(session_id)


# 전역 STT 서비스 인스턴스
stt_service = STTService()