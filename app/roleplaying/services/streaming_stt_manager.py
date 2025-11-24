"""
스트리밍 STT 관리자 (Deepgram SDK 3.x)
===============================================

역할:
- Deepgram WebSocket 세션 관리 (SDK 3.x API)
- 실시간 부분 결과 수신
- 세션 초기화/종료

Deepgram SDK 3.x 변경사항:
- listen.live.v2.connect() 사용 (AsyncLiveConnection 반환)
- 이벤트 기반 메시지 처리 (EventType.MESSAGE 등)
- 모든 메서드가 async/await 기반
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

from deepgram import DeepgramClient

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["StreamingSTTSession", "StreamingSTTManager"]


class StreamingSTTSession:
    """Deepgram WebSocket 스트리밍 세션 (SDK 3.x - 이벤트 기반)"""

    def __init__(self, connection: Any):
        """
        Args:
            connection: Deepgram AsyncLiveConnection (SDK 3.x)
        """
        self.connection = connection
        self.transcript_buffer = ""
        self.is_finalized = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """SDK 3.x 이벤트 핸들러 설정"""
        try:
            from deepgram.core.events import EventType

            # ✅ SDK 3.x: 이벤트 기반 메시지 처리
            self.connection.on(EventType.OPEN, self._on_open)
            self.connection.on(EventType.MESSAGE, self._on_message)
            self.connection.on(EventType.CLOSE, self._on_close)
            self.connection.on(EventType.ERROR, self._on_error)

            logger.debug("Event handlers registered for streaming session")
        except ImportError:
            logger.warning("deepgram.core.events.EventType not available, will use fallback")

    def _on_open(self, open_msg: Any) -> None:
        """WebSocket 연결 열림"""
        logger.debug("WebSocket connection opened")

    def _on_message(self, message: Any) -> None:
        """메시지 수신 핸들러 (이벤트 기반)"""
        try:
            # 메시지가 객체일 수도, 문자열일 수도 있음
            if hasattr(message, 'raw'):
                # SDK 3.x LiveMessage 객체
                data = json.loads(message.raw) if isinstance(message.raw, str) else message.raw
            elif isinstance(message, str):
                data = json.loads(message)
            else:
                data = message if isinstance(message, dict) else {}

            # 부분 결과 추출
            if "result" in data:
                results = data.get("result", {}).get("results", [])
                if results and len(results) > 0:
                    transcript = results[0].get("transcript", "")
                    if transcript:
                        self.transcript_buffer = transcript
                        logger.debug(f"STT partial: {transcript}")
                        # 큐에 추가 (비동기 처리용)
                        try:
                            self.message_queue.put_nowait(("partial", transcript))
                        except asyncio.QueueFull:
                            pass

            # 최종 결과 표시
            if data.get("is_final"):
                self.is_finalized = True

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            logger.debug(f"Could not parse streaming response: {e}")

    def _on_close(self, close_msg: Any) -> None:
        """WebSocket 연결 종료"""
        logger.debug("WebSocket connection closed")
        self.is_finalized = True

    def _on_error(self, error_msg: Any) -> None:
        """에러 핸들러"""
        logger.error(f"WebSocket error: {error_msg}")
        self.is_finalized = True

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """오디오 청크 전송 (비동기)"""
        try:
            # ✅ SDK 3.x: send()는 비동기
            await self.connection.send(audio_chunk)
            logger.debug(f"Audio chunk sent: {len(audio_chunk)} bytes")
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}", exc_info=True)
            raise

    async def receive_partial(self) -> Optional[str]:
        """부분 인식 결과 수신 (비동기)"""
        try:
            # 타임아웃: 500ms (부분 결과 대기)
            message_type, text = await asyncio.wait_for(
                self.message_queue.get(),
                timeout=0.5
            )

            if message_type == "partial":
                return text

            return None

        except asyncio.TimeoutError:
            # 타임아웃은 정상 (부분 결과가 없을 수 있음)
            return None
        except asyncio.QueueEmpty:
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
        스트리밍 세션 생성 (SDK 3.x: AsyncLiveConnection)

        ✅ SDK 3.x 변경:
        - listen.live.v2.connect()를 사용하여 WebSocket 연결 생성
        - async context manager 또는 수동으로 .start()/.stop() 호출
        - 이벤트 기반 메시지 처리

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession

        Raises:
            Exception: 세션 생성 실패 시
        """
        try:
            # ✅ SDK 3.x: listen.live.v2.connect()로 WebSocket 연결 생성
            # async context manager 사용 (자동으로 cleanup 처리)
            connection = await self.client.listen.live.v2.connect(
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                smart_format=settings.DEEPGRAM_SMART_FORMAT,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=settings.DEEPGRAM_SAMPLE_RATE,
                interim_results=settings.DEEPGRAM_INTERIM_RESULTS,
            )

            # 연결 저장 (cleanup 시 필요)
            self._connections[session_id] = connection

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
                    await connection.aclose()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

    async def cleanup(self, session_id: str) -> None:
        """
        세션 강제 정리 (비정상 종료 시)

        Args:
            session_id: 세션 ID
        """
        session = self._sessions.pop(session_id, None)
        connection = self._connections.pop(session_id, None)

        if connection:
            try:
                await connection.aclose()
                logger.info(f"Connection closed: {session_id}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")