"""
STT Service (Deepgram)
======================
Speech-to-Text 처리를 담당하는 서비스.

Deepgram을 기본 엔진으로 사용합니다.
실시간 스트리밍 처리로 지연을 최소화합니다.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

from deepgram import DeepgramClient  # type: ignore


class STTService:
    """
    Speech-to-Text 서비스 (Deepgram 기반)

    Deepgram API를 사용하여 오디오 바이너리를 텍스트로 변환한다.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Deepgram API Key. 없으면 DEEPGRAM_API_KEY 환경변수 사용.
        """
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Deepgram API key not found. Set DEEPGRAM_API_KEY environment variable."
            )

        self.client = DeepgramClient(api_key=self.api_key)
        logger.info("STTService initialized with Deepgram")

    async def transcribe(self, audio_data: bytes) -> str:
        """
        오디오 바이너리를 텍스트로 변환한다.

        Args:
            audio_data: 오디오 바이너리 데이터

        Returns:
            STT 결과 텍스트
        """
        if not audio_data:
            raise ValueError("Empty audio data")

        logger.debug("Transcribing audio (%d bytes) via Deepgram", len(audio_data))

        try:
            # Deepgram 동기 API 사용 (비동기 래퍼)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._transcribe_sync, audio_data
            )
            return result
        except Exception as exc:
            logger.error("Deepgram transcription failed: %s", exc)
            raise

    def _transcribe_sync(self, audio_data: bytes) -> str:
        """
        Deepgram 동기 API를 사용하여 트랜스크립션을 수행한다.
        """
        try:
            response = self.client.listen.v1.media.transcribe_file(
                request=audio_data,
                model="nova-2",
                language="en",
                smart_format=True,
            )

            # 트랜스크립션 결과 추출
            if response.results and response.results.channels:
                transcript = response.results.channels[0].alternatives[0].transcript.strip()
            else:
                transcript = ""

            logger.debug("Deepgram transcription completed: %s", transcript)
            return transcript

        except Exception as exc:
            logger.error("Deepgram transcription error: %s", exc)
            raise

    async def process_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """
        스트리밍 STT용 청크 처리 (향후 구현)

        현재는 None 반환. WebSocket 실시간 스트리밍은 ws_realtime.py에서
        청크를 버퍼링한 후 UTTERANCE_END 시점에 transcribe()를 호출합니다.
        """
        return None


# 전역 STT 서비스 인스턴스
stt_service = STTService()