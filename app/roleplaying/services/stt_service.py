"""
STT Service
===========
Speech-to-Text 처리를 담당하는 서비스.

현재는 무료로 사용할 수 있는 open-source Whisper 모델을 기본 엔진으로 사용합니다.
필요시 Google/Azure 등 다른 엔진을 연결할 수 있도록 인터페이스 형태는 유지합니다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Whisper는 선택적 의존성이다. 모듈이 없으면 ImportError 대신 None으로 유지했다가
# 실제 호출 시 친절한 예외를 전달한다.
try:
    import whisper  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    whisper = None  # type: ignore


class STTService:
    """
    Speech-to-Text 서비스

    Whisper 모델을 기본으로 오디오 바이너리를 텍스트로 변환한다.
    """

    def __init__(
        self,
        engine: str = "whisper",
        whisper_model_size: str = "base",
        whisper_device: Optional[str] = None
    ):
        """
        Args:
            engine: 사용할 STT 엔진 ("whisper", "google", "azure")
            whisper_model_size: Whisper 모델 크기 (tiny, base, small, medium, large 등)
            whisper_device: CUDA 환경이라면 "cuda" 지정 가능. 기본은 라이브러리 자동판단.
        """
        self.engine = engine
        self.whisper_model_size = whisper_model_size
        self.whisper_device = whisper_device
        self._whisper_model: Optional[Any] = None

        logger.info(
            "STTService initialized (engine=%s, whisper_model=%s)",
            engine,
            whisper_model_size
        )

        if engine == "whisper":
            self._init_whisper()
        elif engine == "google":
            self._init_google()
        elif engine == "azure":
            self._init_azure()
        else:
            logger.warning("Unknown STT engine '%s'. Falling back to Whisper.", engine)
            self.engine = "whisper"
            self._init_whisper()

    # -------------------------------------------------------------------------
    # Engine 초기화
    # -------------------------------------------------------------------------
    def _init_whisper(self) -> None:
        """Whisper 모델 로드"""
        if whisper is None:
            raise ImportError(
                "openai-whisper 모듈이 설치되어 있지 않습니다. "
                "pip install openai-whisper 로 설치 후 다시 시도하세요."
            )

        try:
            self._whisper_model = whisper.load_model(
                self.whisper_model_size,
                device=self.whisper_device
            )
            logger.info("Whisper model '%s' loaded.", self.whisper_model_size)
        except Exception as exc:  # pragma: no cover - hw/env specific
            logger.error("Failed to load Whisper model: %s", exc)
            raise

    def _init_google(self) -> None:
        """Google STT 엔진 초기화 (현재 미구현)"""
        logger.info("Google STT engine selected but not implemented; fallback to Whisper at runtime.")

    def _init_azure(self) -> None:
        """Azure STT 엔진 초기화 (현재 미구현)"""
        logger.info("Azure STT engine selected but not implemented; fallback to Whisper at runtime.")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    async def transcribe(self, audio_data: bytes) -> str:
        """
        오디오 바이너리를 텍스트로 변환한다.

        Args:
            audio_data: 16kHz mono WAV 포맷의 PCM 데이터
        """
        if not audio_data:
            raise ValueError("Empty audio data")

        logger.debug("Transcribing audio (%d bytes) via %s", len(audio_data), self.engine)

        if self.engine == "whisper":
            return await self._transcribe_whisper(audio_data)
        if self.engine == "google":
            return await self._transcribe_google(audio_data)
        if self.engine == "azure":
            return await self._transcribe_azure(audio_data)

        # 예측 불가 엔진 값일 때도 Whisper로 폴백
        logger.warning("Unsupported STT engine '%s'; using Whisper fallback.", self.engine)
        return await self._transcribe_whisper(audio_data)

    async def process_chunk(self, audio_chunk: bytes) -> Optional[str]:
        """
        스트리밍 STT용 청크 처리 (현재는 Whisper 실시간 모델을 사용하지 않아 None 반환)
        """
        return None

    # -------------------------------------------------------------------------
    # Whisper 구현
    # -------------------------------------------------------------------------
    async def _transcribe_whisper(self, audio_data: bytes) -> str:
        if self._whisper_model is None:
            raise RuntimeError("Whisper model is not loaded. Check initialization.")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_whisper_sync, audio_data)

    def _run_whisper_sync(self, audio_data: bytes) -> str:
        """
        Whisper는 동기 API만 제공하므로 thread executor에서 실행한다.
        """
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_path = Path(tmp_file.name)
        try:
            tmp_file.write(audio_data)
            tmp_file.flush()
            tmp_file.close()
            result = self._whisper_model.transcribe(
                tmp_path.as_posix(),
                language=os.getenv("WHISPER_LANGUAGE", "en"),
                fp16=False  # CPU 환경을 고려해 기본값을 False로 둔다.
            )
            text = (result.get("text") or "").strip()
            logger.debug("Whisper transcription completed: %s", text)
            return text
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to cleanup temp audio file: %s", tmp_path)

    # -------------------------------------------------------------------------
    # Placeholder for other engines (미사용)
    # -------------------------------------------------------------------------
    async def _transcribe_google(self, audio_data: bytes) -> str:
        logger.warning("Google STT not implemented. Using Whisper fallback.")
        return await self._transcribe_whisper(audio_data)

    async def _transcribe_azure(self, audio_data: bytes) -> str:
        logger.warning("Azure STT not implemented. Using Whisper fallback.")
        return await self._transcribe_whisper(audio_data)


# 전역 STT 서비스 인스턴스 (기본 Whisper)
stt_service = STTService(engine="whisper")
