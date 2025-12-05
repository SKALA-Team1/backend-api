"""
스트리밍 STT 관리자 (Deepgram SDK 3.x)
===============================================

역할:
- Deepgram WebSocket 세션 관리 (SDK 3.x API)
- 실시간 부분 결과 수신
- 세션 초기화/종료

Deepgram SDK 3.x API:
- listen.websocket.v() (async context manager)
- listen.live는 SDK 3.4.0부터 deprecated
- 버전 메서드: .v() (구버전에서는 .v1())
- 모든 메서드가 async/await 기반
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional
from deepgram.clients.listen import LiveOptions

from deepgram import DeepgramClient

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["StreamingSTTSession", "StreamingSTTManager"]


class StreamingSTTSession:
    """Deepgram WebSocket 스트리밍 세션 (SDK 3.x)"""

    def __init__(self, connection: Any):
        """
        Args:
            connection: Deepgram WebSocket Connection (SDK 3.11.0+)
        """
        self.connection = connection
        self.transcript_buffer = ""
        self.is_finalized = False

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """오디오 청크 전송 (비동기)"""
        try:
            # ✅ SDK 3.x: send()는 이미 async
            await self.connection.send(audio_chunk)
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}", exc_info=True)
            raise

    async def receive_partial(self) -> Optional[str]:
        """부분 인식 결과 수신 (비동기)"""
        try:
            # ✅ SDK 3.x: recv()는 이미 async
            response = await self.connection.recv()

            if not response:
                return None

            try:
                # 응답이 문자열일 수도, dict일 수도 있음
                if isinstance(response, str):
                    data = json.loads(response)
                else:
                    data = response

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

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Could not parse streaming response: {e}")

            return None

        except asyncio.TimeoutError:
            logger.debug("Timeout waiting for streaming result")
            return None
        except Exception as e:
            logger.error(f"Failed to receive streaming result: {e}", exc_info=True)
            raise

    async def finalize(self) -> str:
        """스트리밍 종료 및 최종 결과 반환"""
        try:
            # ✅ SDK 3.x: finish()는 비동기
            await self.connection.finish()

            # 최종 결과 대기 (타임아웃 5초)
            timeout = 5.0
            loop = asyncio.get_running_loop()
            start_time = loop.time()

            while not self.is_finalized:
                try:
                    elapsed = loop.time() - start_time
                    if elapsed > timeout:
                        logger.warning(f"Timeout waiting for finalized result after {timeout}s")
                        break

                    # ✅ SDK 3.x: recv()는 비동기
                    response = await asyncio.wait_for(
                        self.connection.recv(),
                        timeout=timeout - elapsed
                    )

                    if isinstance(response, str):
                        data = json.loads(response)
                    else:
                        data = response

                    if data.get("is_final"):
                        self.is_finalized = True

                except asyncio.TimeoutError:
                    logger.debug("Timeout waiting for final result")
                    break
                except (json.JSONDecodeError, StopIteration, TypeError):
                    break

            logger.info(f"STT finalized: {self.transcript_buffer}")
            return self.transcript_buffer

        except Exception as e:
            logger.error(f"Failed to finalize streaming: {e}", exc_info=True)
            return self.transcript_buffer


class StreamingSTTManager:
    """스트리밍 STT 세션 관리 (SDK 3.x)"""

    def __init__(self, client: Optional[DeepgramClient] = None):
        """
        Args:
            client: Deepgram 클라이언트
        """
        self.client = client or DeepgramClient(api_key=settings.deepgram_api_key)
        self._sessions: Dict[str, StreamingSTTSession] = {}
        self._connections: Dict[str, Any] = {}  # 활성 WebSocket 연결 추적

    async def create_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 세션 생성 (SDK 3.x: async context manager)

        ✅ SDK 3.x 변경:
        - listen.live() → listen.websocket.v() (SDK 3.11.0+)
        - 동기 → 비동기
        - Context manager 사용

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession

        Raises:
            Exception: 세션 생성 실패 시
        """
        try:
            # ✅ SDK 3.11.0: LiveOptions 객체 생성
            options = LiveOptions(
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                smart_format=settings.DEEPGRAM_SMART_FORMAT,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=settings.DEEPGRAM_SAMPLE_RATE,
                interim_results=settings.DEEPGRAM_INTERIM_RESULTS,
                # ✅ 타임아웃 설정: Deepgram init 후 5초 내에 오디오 필요
                utterance_end_ms=5000,
                # ✅ no_delay: 지연 없이 즉시 응답 (스트리밍 최적화)
                no_delay=True,
            )
            # ✅ WebSocket 연결 생성 (asyncwebsocket 사용 - async start() 필수)
            connection = self.client.listen.asyncwebsocket.v("1")
            # ✅ 비동기로 연결 시작
            success = await connection.start(options)
            if not success:
                raise Exception("Failed to start WebSocket connection")

            # 연결 저장 (cleanup 시 필요)
            self._connections[session_id] = connection
            session = StreamingSTTSession(connection)
            self._sessions[session_id] = session
            logger.info(f"✅ Streaming STT session created: {session_id}")
            return session
        except Exception as e:
            logger.error(f"❌ Failed to create streaming session: {e}", exc_info=True)
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
            # 오디오 전송
            await session.send_chunk(chunk)
            # 부분 결과 수신
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
        connection = self._connections.pop(session_id, None)

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

        finally:
            # 연결 정리
            if connection:
                try:
                    # AsyncListenWebSocketClient는 aclose() 대신 finish() 사용
                    # 하지만 finalize()에서 이미 finish() 호출했으므로 참조만 제거
                    pass
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

    async def cleanup(self, session_id: str) -> None:
        """
        세션 강제 정리 (비정상 종료 시)

        Args:
            session_id: 세션 ID
        """
        self._sessions.pop(session_id, None)
        connection = self._connections.pop(session_id, None)

        if connection:
            try:
                # AsyncListenWebSocketClient는 finish()로 정리 (한 번만 호출)
                # finalize()에서 호출되지 않았을 경우 here에서 호출
                try:
                    await connection.finish()
                except Exception:
                    pass  # 이미 종료된 연결일 수 있음
                logger.info(f"Connection cleaned up: {session_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up connection: {e}")