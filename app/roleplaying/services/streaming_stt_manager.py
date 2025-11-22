"""
스트리밍 STT 관리자
===============================================

역할:
- Deepgram WebSocket 세션 관리
- 실시간 부분 결과 수신
- 세션 초기화/종료
"""

import json
import logging
from typing import Any, Dict, Optional

from deepgram import DeepgramClient

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["StreamingSTTSession", "StreamingSTTManager"]


class StreamingSTTSession:
    """Deepgram WebSocket 스트리밍 세션"""

    def __init__(self, connection: Any):
        """
        Args:
            connection: Deepgram WebSocket 연결
        """
        self.connection = connection
        self.transcript_buffer = ""
        self.is_finalized = False

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """오디오 청크 전송"""
        try:
            self.connection.send(audio_chunk)
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}", exc_info=True)
            raise

    async def receive_partial(self) -> Optional[str]:
        """부분 인식 결과 수신"""
        try:
            response = self.connection.recv()

            if not response:
                return None

            try:
                data = json.loads(response)

                # 부분 결과 추출
                if "result" in data and "results" in data["result"]:
                    results = data["result"]["results"]
                    if results and len(results) > 0:
                        transcript = results[0].get("transcript", "")
                        if transcript and transcript != self.transcript_buffer:
                            self.transcript_buffer = transcript
                            logger.debug(f"STT partial: {transcript}")
                            return transcript

                # 최종 결과 표시
                if data.get("is_final"):
                    self.is_finalized = True

            except (json.JSONDecodeError, KeyError):
                logger.debug("Could not parse streaming response")

            return None

        except Exception as e:
            logger.error(f"Failed to receive streaming result: {e}", exc_info=True)
            raise

    async def finalize(self) -> str:
        """스트리밍 종료 및 최종 결과 반환"""
        try:
            self.connection.finish()

            # 최종 결과 대기
            while not self.is_finalized:
                try:
                    response = self.connection.recv()
                    data = json.loads(response)

                    if data.get("is_final"):
                        self.is_finalized = True

                except (json.JSONDecodeError, StopIteration):
                    break

            logger.info(f"STT finalized: {self.transcript_buffer}")
            return self.transcript_buffer

        except Exception as e:
            logger.error(f"Failed to finalize streaming: {e}", exc_info=True)
            return self.transcript_buffer


class StreamingSTTManager:
    """스트리밍 STT 세션 관리"""

    def __init__(self, client: Optional[DeepgramClient] = None):
        """
        Args:
            client: Deepgram 클라이언트
        """
        self.client = client or DeepgramClient(api_key=settings.deepgram_api_key)
        self._sessions: Dict[str, StreamingSTTSession] = {}

    def create_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 세션 생성

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession
        """
        try:
            connection = self.client.listen.live(
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                smart_format=settings.DEEPGRAM_SMART_FORMAT,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=settings.DEEPGRAM_SAMPLE_RATE,
                interim_results=settings.DEEPGRAM_INTERIM_RESULTS,
            )

            session = StreamingSTTSession(connection)
            self._sessions[session_id] = session

            logger.info(f"Streaming STT session created: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create streaming session: {e}", exc_info=True)
            raise

    async def process_chunk(
        self, session_id: str, chunk: bytes
    ) -> Optional[str]:
        """
        청크 처리

        Args:
            session_id: 세션 ID
            chunk: 오디오 청크

        Returns:
            부분 인식 결과 (있으면)
        """
        session = self._sessions.get(session_id)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        try:
            return await session.receive_partial()
        except Exception as e:
            logger.error(f"Chunk processing failed: {e}", exc_info=True)
            return None

    async def finalize_session(self, session_id: str) -> str:
        """
        세션 종료 및 최종 결과 반환

        Args:
            session_id: 세션 ID

        Returns:
            최종 인식 결과
        """
        session = self._sessions.pop(session_id, None)

        if not session:
            logger.warning(f"Session not found for finalization: {session_id}")
            return ""

        try:
            result = await session.finalize()
            logger.info(f"Session finalized: {session_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to finalize session {session_id}: {e}", exc_info=True)
            return ""