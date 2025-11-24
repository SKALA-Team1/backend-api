"""
스트리밍 STT 관리자 (Deepgram SDK 5.3.0 V1SocketClient - 단일 recv 루프)
================================================================

역할:
- Deepgram WebSocket 세션 관리 (SDK 5.3.0 v1 API)
- 실시간 부분 결과 수신 (queue 기반)
- 세션 초기화/종료

Deepgram SDK 5.3.0 v1 특징:
- listen.v1.connect() 반환: V1SocketClient (동기 context manager)
- recv()는 단 한 곳(reader_loop)에서만 호출
- send()로 오디오 청크 전송 (바이너리)
- 메시지는 queue를 통해 async 작업에 전달

아키텍처:
- StreamingSTTSession: 단일 recv loop + queue 기반 메시지 처리
- _reader_loop(): 유일한 recv() 호출 지점
- message queue: 수신 메시지를 async 작업에 전달
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from deepgram import DeepgramClient
from deepgram.core.events import EventType
from starlette.concurrency import run_in_threadpool

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["StreamingSTTSession", "StreamingSTTManager"]


class StreamingSTTSession:
    """Deepgram WebSocket 스트리밍 세션 (SDK 5.3.0 V1SocketClient - 단일 recv 루프)"""

    def __init__(self, connection: Any, context: Any):
        """
        Args:
            connection: Deepgram V1SocketClient (SDK 5.3.0)
            context: context manager (종료 시 __exit__ 호출용)
        """
        self.connection = connection
        self.context = context
        self.transcript_buffer = ""
        self.is_finalized = False
        self.message_queue: asyncio.Queue = asyncio.Queue()

        # 수신 루프 제어
        self._running = False
        self._reader_task: Optional[asyncio.Task] = None

        # 디버깅: 연결 타입 확인
        logger.info(f"[STT] Connection type = {type(self.connection)}")
        logger.info(f"[STT] Connection has send = {hasattr(self.connection, 'send')}")

        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """SDK 5.3.0 이벤트 핸들러 설정"""
        try:
            # ✅ SDK 5.3.0: 이벤트 기반 메시지 처리
            self.connection.on(EventType.OPEN, self._on_open)
            self.connection.on(EventType.MESSAGE, self._on_message)
            self.connection.on(EventType.CLOSE, self._on_close)
            self.connection.on(EventType.ERROR, self._on_error)

            logger.debug("Event handlers registered for streaming session")
        except Exception as e:
            logger.warning(f"Failed to register event handlers: {e}")

    def _on_open(self, open_msg: Any) -> None:
        """WebSocket 연결 열림"""
        logger.debug("WebSocket connection opened")

    def _on_message(self, message: Any) -> None:
        """메시지 수신 핸들러 (이벤트 기반)"""
        try:
            # Deepgram V1SocketClient 메시지 처리
            if hasattr(message, 'raw'):
                data = message.raw
            else:
                data = message

            # 트랜스크립트 추출
            if hasattr(data, 'channel') and hasattr(data.channel, 'alternatives'):
                alternatives = data.channel.alternatives
                if alternatives and len(alternatives) > 0:
                    transcript = alternatives[0].transcript if hasattr(alternatives[0], 'transcript') else ""
                    if transcript:
                        self.transcript_buffer = transcript
                        logger.debug(f"STT partial: {transcript}")
                        try:
                            self.message_queue.put_nowait(("partial", transcript))
                        except asyncio.QueueFull:
                            pass

            # 최종 결과 확인
            if hasattr(data, 'is_final') and data.is_final:
                self.is_finalized = True
                logger.debug("STT result finalized")

        except Exception as e:
            logger.debug(f"Could not parse streaming response: {e}")

    def _on_close(self, close_msg: Any) -> None:
        """WebSocket 연결 종료"""
        logger.debug("WebSocket connection closed")
        self.is_finalized = True

    def _on_error(self, error_msg: Any) -> None:
        """에러 핸들러"""
        logger.error(f"WebSocket error: {error_msg}")
        self.is_finalized = True

    async def start(self) -> None:
        """
        ✅ 수신 루프 시작 (Event-based with SDK's start_listening())

        Deepgram v1 SDK의 start_listening()을 사용하면:
        1. SDK이 내부적으로 recv 루프 관리 (동시성 문제 해결)
        2. 등록된 event handler가 자동으로 호출됨
        3. 사용자 코드는 recv를 직접 호출하지 않음
        """
        self._running = True
        self._reader_task = asyncio.create_task(self._reader_loop())
        logger.debug("STT reader loop started (event-based)")

    async def _reader_loop(self) -> None:
        """
        ✅ Event-based listening loop (SDK's start_listening() 사용)

        Deepgram v1 SDK의 start_listening()은:
        - 동기 blocking 메서드
        - 내부적으로 recv() 루프 실행
        - 등록된 event handler 자동 호출
        - executor에서 실행하여 asyncio를 블로킹하지 않음
        """
        loop = asyncio.get_running_loop()

        try:
            logger.debug("Reader loop: starting (SDK start_listening mode)")

            # ✅ SDK의 start_listening()을 executor에서 실행
            # 이 메서드는 blocking이며, 내부적으로 recv 루프를 관리함
            await loop.run_in_executor(
                None,
                self.connection.start_listening
            )

            logger.debug("Reader loop: start_listening completed")

        except asyncio.CancelledError:
            logger.debug("Reader loop: cancelled")
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ["connection", "closed", "eof", "reset", "broken"]):
                logger.debug(f"Reader loop: connection closed normally")
            else:
                logger.error(f"Reader loop error: {e}", exc_info=True)
        finally:
            self._running = False
            logger.debug("Reader loop: ended")

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """
        ✅ 오디오 청크 전송 (비동기)

        Deepgram v1 SDK의 send_media()를 사용
        send_media()는 동기 메서드이므로 run_in_threadpool으로 감싸서 실행
        """
        try:
            conn = self.connection

            # ✅ Deepgram v1 공식 메서드: connection.send_media(bytes)
            if hasattr(conn, "send_media"):
                await run_in_threadpool(conn.send_media, audio_chunk)
                logger.debug(f"Audio chunk sent (via send_media()): {len(audio_chunk)} bytes")
                return

            raise RuntimeError(f"No valid send_media method on Deepgram connection: {type(conn)}")

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
        except Exception as e:
            logger.error(f"Failed to receive streaming result: {e}", exc_info=True)
            return None

    async def finalize(self) -> str:
        """스트리밍 종료 및 최종 결과 반환"""
        try:
            # ✅ 마지막 메시지 수신 대기 (최종 결과)
            timeout = 5.0
            loop = asyncio.get_running_loop()
            start_time = loop.time()

            while not self.is_finalized:
                try:
                    elapsed = loop.time() - start_time
                    if elapsed > timeout:
                        logger.warning(f"Timeout waiting for finalized result after {timeout}s")
                        break

                    # 작은 대기 + 폴링
                    await asyncio.sleep(0.1)

                except asyncio.TimeoutError:
                    logger.debug("Timeout waiting for final result")
                    break

            logger.info(f"STT finalized: {self.transcript_buffer}")
            return self.transcript_buffer

        except Exception as e:
            logger.error(f"Failed to finalize streaming: {e}", exc_info=True)
            return self.transcript_buffer

    async def close(self) -> None:
        """
        ✅ 세션 정리 및 연결 종료

        1. 수신 루프 종료
        2. Deepgram connection 정리
        3. Context manager 종료
        """
        try:
            # Step 1: 수신 루프 종료
            self._running = False

            if self._reader_task and not self._reader_task.done():
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass

            logger.debug("Reader task stopped")

            # Step 2: Deepgram connection finish
            loop = asyncio.get_running_loop()

            if hasattr(self.connection, "finish"):
                await loop.run_in_executor(None, self.connection.finish)
                logger.debug("Deepgram connection finished")

            # Step 3: Context manager 종료
            if self.context:
                await loop.run_in_executor(
                    None,
                    lambda: self.context.__exit__(None, None, None)
                )
                logger.debug("Context manager exited")

            logger.info("STT session closed successfully")

        except Exception as e:
            logger.error(f"Error closing STT session: {e}", exc_info=True)


class StreamingSTTManager:
    """스트리밍 STT 세션 관리 (SDK 5.3.0)"""

    def __init__(self, client: Optional[DeepgramClient] = None):
        """
        Args:
            client: Deepgram 클라이언트
        """
        self.client = client or DeepgramClient(api_key=settings.deepgram_api_key)
        self._sessions: Dict[str, StreamingSTTSession] = {}

    async def create_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 세션 생성 (SDK 5.3.0 v1 API)

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession

        Raises:
            Exception: 세션 생성 실패 시
        """
        loop = asyncio.get_running_loop()

        try:
            # ✅ SDK 5.3.0: listen.v1.connect()는 동기 context manager
            # executor에서 실행하여 asyncio 루프 블로킹 방지
            connection, context = await loop.run_in_executor(
                None,
                self._create_connection_sync
            )

            if not connection:
                raise RuntimeError("Failed to create WebSocket connection")

            # 세션 생성
            session = StreamingSTTSession(connection, context)
            self._sessions[session_id] = session

            # ✅ 수신 루프 시작 (단일 recv 루프)
            await session.start()

            logger.info(f"Streaming STT session created: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create streaming session: {e}", exc_info=True)
            raise

    def _create_connection_sync(self) -> tuple:
        """
        동기 WebSocket 연결 생성 (executor에서 실행)

        SDK 5.3.0의 listen.v1.connect()는 동기 context manager이므로,
        executor 스레드에서 실행해야 함

        Returns:
            (connection, context) 튜플
        """
        try:
            # ✅ SDK 5.3.0: v1 API 사용 (일반 STT용)
            context = self.client.listen.v1.connect(
                model=settings.DEEPGRAM_MODEL,
                language=settings.DEEPGRAM_LANGUAGE,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=str(settings.DEEPGRAM_SAMPLE_RATE),
            )

            # ✅ Context manager 진입하여 실제 connection 획득
            connection = context.__enter__()

            logger.debug(f"V1SocketClient created")
            return connection, context

        except Exception as e:
            logger.error(f"Failed to create WebSocket connection: {e}", exc_info=True)
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

        if not session:
            logger.warning(f"Session not found for finalization: {session_id}")
            return ""

        try:
            # 최종 결과 대기
            result = await session.finalize()
            logger.info(f"Session finalized: {session_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to finalize session {session_id}: {e}", exc_info=True)
            return ""

        finally:
            # ✅ 세션 정리 (reader loop + connection close)
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")

    async def cleanup(self, session_id: str) -> None:
        """
        세션 강제 정리 (비정상 종료 시)

        Args:
            session_id: 세션 ID
        """
        session = self._sessions.pop(session_id, None)

        if session:
            try:
                await session.close()
                logger.info(f"Session cleaned up: {session_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up session: {e}")