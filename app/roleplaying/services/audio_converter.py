"""
오디오 포맷 변환
===============================================

역할:
- PCM → WAV 변환
- 자동 게인 조절 (AGC)
- 음성 정규화
"""

import io
import logging
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import soundfile as sf
except ImportError:
    sf = None


class AudioConverter:
    """오디오 포맷 변환"""

    SAMPLE_RATE = settings.DEEPGRAM_SAMPLE_RATE
    NUM_CHANNELS = settings.DEEPGRAM_CHANNELS
    BYTES_PER_SAMPLE = 2  # int16
    AGC_ENABLED = settings.AUDIO_AGC_ENABLED
    AGC_TARGET_LEVEL = settings.AUDIO_AGC_TARGET_LEVEL

    @staticmethod
    def pcm_to_wav(pcm_data: bytes) -> bytes:
        """
        Raw PCM → WAV 변환

        Args:
            pcm_data: PCM 16-bit mono 오디오 데이터

        Returns:
            WAV 형식 오디오 데이터
        """
        if not pcm_data:
            logger.warning("Empty PCM data provided")
            return b""

        try:
            if sf:
                return AudioConverter._pcm_to_wav_with_soundfile(pcm_data)
            else:
                logger.warning("soundfile not available, returning raw PCM")
                return pcm_data

        except Exception as e:
            logger.error(f"PCM to WAV conversion failed: {e}", exc_info=True)
            return pcm_data

    @staticmethod
    def _pcm_to_wav_with_soundfile(pcm_data: bytes) -> bytes:
        """soundfile을 사용한 WAV 변환"""
        try:
            # PCM 바이트 → numpy 배열
            audio_array = np.frombuffer(
                pcm_data, dtype=np.int16
            ).astype(np.float32) / 32768.0

            # AGC 적용
            if AudioConverter.AGC_ENABLED:
                audio_array = AudioConverter._apply_agc(audio_array)

            # WAV로 변환
            buffer = io.BytesIO()
            sf.write(
                buffer,
                audio_array,
                AudioConverter.SAMPLE_RATE,
                format="WAV"
            )
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"soundfile conversion failed: {e}", exc_info=True)
            raise

    @staticmethod
    def _apply_agc(audio_array: np.ndarray) -> np.ndarray:
        """
        자동 게인 조절 (AGC)

        Args:
            audio_array: 정규화된 오디오 배열 [-1.0, 1.0]

        Returns:
            AGC 적용된 오디오 배열
        """
        try:
            max_val = np.max(np.abs(audio_array))

            if max_val == 0:
                logger.debug("Silent audio detected, skipping AGC")
                return audio_array

            # 목표 레벨에 맞춰 게인 적용
            if max_val < AudioConverter.AGC_TARGET_LEVEL:
                gain = AudioConverter.AGC_TARGET_LEVEL / max_val
                audio_array = audio_array * gain

                # 클리핑 방지
                audio_array = np.clip(audio_array, -1.0, 1.0)
                logger.debug(f"AGC applied with gain: {gain:.2f}x")

            return audio_array

        except Exception as e:
            logger.error(f"AGC failed: {e}")
            return audio_array

    @staticmethod
    def get_pcm_chunk_size(duration_ms: int = 100) -> int:
        """청크 크기 계산 (바이트)"""
        return (
            AudioConverter.SAMPLE_RATE // 1000
            * duration_ms
            * AudioConverter.BYTES_PER_SAMPLE
        )