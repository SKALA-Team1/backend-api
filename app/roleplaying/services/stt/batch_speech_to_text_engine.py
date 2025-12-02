"""
배치 STT 엔진 (Deepgram)
===============================================

역할:
- 전체 오디오 파일 STT 처리
- Deepgram API 호출
- 오류 처리 및 재시도
"""

import asyncio
import logging
from typing import Optional

from deepgram import DeepgramClient

from app.config import settings
from app.roleplaying.services.stt.audio_converter import AudioConverter

logger = logging.getLogger(__name__)


class BatchSTTEngine:
    """배치 STT 처리 (전체 오디오)"""

    def __init__(self, client: Optional[DeepgramClient] = None):
        """
        Args:
            client: Deepgram 클라이언트 (없으면 생성)
        """
        self.client = client or DeepgramClient(api_key=settings.deepgram_api_key)
        self.converter = AudioConverter()

    async def transcribe(self, audio_data: bytes, max_retries: int = 3) -> str:
        """
        오디오를 텍스트로 변환

        Args:
            audio_data: PCM 16-bit mono 오디오
            max_retries: 최대 재시도 횟수

        Returns:
            인식된 텍스트 (빈 문자열 = 침묵)
        """
        if not audio_data:
            logger.warning("Empty audio data provided")
            return ""

        for attempt in range(max_retries):
            try:
                # PCM → WAV 변환
                wav_audio = self.converter.pcm_to_wav(audio_data)

                if not wav_audio:
                    logger.warning("WAV conversion returned empty data")
                    return ""

                # 동기 함수를 스레드에서 실행 (논블로킹)
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_sync,
                    wav_audio
                )

                logger.info(f"STT completed: {result[:100]}...")
                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"STT failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"STT failed after {max_retries} attempts: {e}",
                        exc_info=True
                    )
                    return ""

        return ""

    def _transcribe_sync(self, wav_audio: bytes) -> str:
        """
        동기 STT 처리 (Deepgram API)

        Args:
            wav_audio: WAV 형식 오디오

        Returns:
            인식된 텍스트
        """
        try:
            response = self.client.listen.v1.media.transcribe_file(
                request=wav_audio,
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                smart_format=settings.DEEPGRAM_SMART_FORMAT,
            )

            # 결과 추출
            if hasattr(response, "results"):
                results = response.results
                if hasattr(results, "channels") and results.channels:
                    channel = results.channels[0]
                    if hasattr(channel, "alternatives") and channel.alternatives:
                        alternative = channel.alternatives[0]
                        if hasattr(alternative, "transcript"):
                            text = alternative.transcript.strip()
                            logger.debug(f"Deepgram response: {text[:100]}...")
                            return text

            logger.warning("No transcript found in Deepgram response")
            return ""

        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}", exc_info=True)
            raise