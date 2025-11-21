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
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from deepgram import DeepgramClient  # type: ignore
from app.config import settings


class StreamingSTTSession:
    """
    Deepgram WebSocket 스트리밍 STT 세션

    실시간 오디오 청크 처리로 부분 인식 결과를 즉시 반환한다.
    """

    def __init__(self, connection: Any):
        """
        Args:
            connection: Deepgram WebSocket 연결 객체
        """
        self.connection = connection
        self.transcript_buffer = ""
        self.is_finalized = False
        logger.debug("StreamingSTTSession initialized")

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """오디오 청크를 Deepgram으로 전송"""
        try:
            self.connection.send(audio_chunk)
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}")
            raise

    async def receive_partial(self) -> Optional[str]:
        """부분 인식 결과 수신 (스트리밍)"""
        try:
            # Deepgram 스트리밍 응답 수신
            response = self.connection.recv()

            if not response:
                return None

            # 부분 결과 추출
            try:
                import json
                data = json.loads(response)

                # 부분 인식 결과
                if "result" in data and "results" in data["result"]:
                    results = data["result"]["results"]
                    if results and len(results) > 0:
                        transcript = results[0].get("transcript", "")
                        if transcript and transcript != self.transcript_buffer:
                            self.transcript_buffer = transcript
                            logger.debug(f"Partial STT: {transcript}")
                            return transcript

                # 최종 인식 결과 (is_final=true)
                if data.get("is_final"):
                    self.is_finalized = True
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Could not parse streaming response: {e}")

            return None
        except Exception as e:
            logger.error(f"Failed to receive streaming result: {e}")
            raise

    async def finalize(self) -> str:
        """스트리밍 종료 및 최종 결과 반환"""
        try:
            self.connection.finish()

            # 최종 결과 대기
            while not self.is_finalized:
                try:
                    import json
                    response = self.connection.recv()

                    if response:
                        data = json.loads(response)
                        if data.get("is_final"):
                            self.is_finalized = True
                except Exception:
                    break

            logger.debug(f"Final STT: {self.transcript_buffer}")
            return self.transcript_buffer
        except Exception as e:
            logger.error(f"Failed to finalize streaming: {e}")
            return self.transcript_buffer


class STTService:
    """
    Speech-to-Text 서비스 (Deepgram 기반)

    Deepgram API를 사용하여 오디오 바이너리를 텍스트로 변환한다.

    두 가지 모드 지원:
    1. 배치 모드: transcribe() - 전체 오디오 처리 후 최종 결과 반환
    2. 스트리밍 모드: process_chunk() - 청크 단위 부분 결과 실시간 반환
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Deepgram API Key. 없으면 settings.deepgram_api_key 사용.
        """
        self.api_key = api_key or settings.deepgram_api_key
        if not self.api_key:
            raise ValueError(
                "Deepgram API key not found. Set DEEPGRAM_API_KEY in .env file."
            )

        self.client = DeepgramClient(api_key=self.api_key)
        self._streaming_sessions: Dict[str, StreamingSTTSession] = {}
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
            logger.warning("Empty audio data, returning empty string")
            return ""

        logger.debug("Transcribing audio (%d bytes) via Deepgram", len(audio_data))

        try:
            # Deepgram 동기 API 사용 (비동기 래퍼)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, self._transcribe_sync, audio_data
            )
            return result
        except Exception as exc:
            logger.error("Deepgram transcription failed in async wrapper: %s", exc)
            # Fallback: return empty string instead of raising
            return ""

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
                encoding="linear16",
                sample_rate=16000,
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
            # Fallback: 더미 오디오나 오류 발생 시 기본 응답
            logger.warning("Deepgram failed, returning empty string")
            return ""

    def create_streaming_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 STT 세션 생성

        Args:
            session_id: 세션 ID (고유식별자)

        Returns:
            StreamingSTTSession 객체
        """
        try:
            # Deepgram WebSocket 스트리밍 연결
            connection = self.client.listen.live(
                model="nova-2",
                language="en",
                smart_format=True,
                encoding="linear16",  # 16-bit PCM
                sample_rate=16000,    # 16kHz
                interim_results=True,  # 부분 결과 활성화
            )

            session = StreamingSTTSession(connection)
            self._streaming_sessions[session_id] = session
            logger.info(f"Streaming STT session created: {session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create streaming session: {e}")
            raise

    async def process_chunk(self, session_id: str, audio_chunk: bytes) -> Optional[str]:
        """
        스트리밍 STT용 청크 처리

        실시간 오디오 청크를 Deepgram WebSocket으로 전송하고
        부분 인식 결과를 즉시 반환한다.

        Args:
            session_id: 스트리밍 세션 ID
            audio_chunk: 오디오 청크 바이너리 데이터

        Returns:
            부분 STT 결과 텍스트 (없으면 None)
        """
        session = self._streaming_sessions.get(session_id)
        if not session:
            logger.warning(f"Streaming session not found: {session_id}")
            return None

        try:
            # 오디오 청크 전송
            await session.send_chunk(audio_chunk)

            # 부분 결과 수신
            partial_text = await session.receive_partial()
            if partial_text:
                logger.debug(f"Streaming STT partial: {partial_text}")
            return partial_text
        except Exception as e:
            logger.error(f"Streaming chunk processing failed: {e}")
            return None

    async def finalize_streaming(self, session_id: str) -> str:
        """
        스트리밍 STT 세션 종료 및 최종 결과 반환

        Args:
            session_id: 스트리밍 세션 ID

        Returns:
            최종 STT 결과 텍스트
        """
        session = self._streaming_sessions.pop(session_id, None)
        if not session:
            logger.warning(f"Streaming session not found: {session_id}")
            return ""

        try:
            final_text = await session.finalize()
            logger.info(f"Streaming session finalized: {session_id}, result: {final_text}")
            return final_text
        except Exception as e:
            logger.error(f"Failed to finalize streaming session: {e}")
            return ""


# 전역 STT 서비스 인스턴스
stt_service = STTService()