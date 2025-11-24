"""
스트리밍 STT 관리자 (Deepgram SDK 5.3.0 V2SocketClient)
================================================================

역할:
- Deepgram WebSocket 세션 관리 (SDK 5.3.0 API)
- 실시간 부분 결과 수신
- 세션 초기화/종료

Deepgram SDK 5.3.0 특징:
- listen.v2.connect() 반환: V2SocketClient (Iterator 기반)
- recv() 비동기 호출로 메시지 수신
- send_media()로 오디오 청크 전송
- 이벤트 핸들러 기반 처리 (on() 메서드)
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from deepgram import DeepgramClient
from deepgram.extensions.types.sockets.listen_v2_media_message import ListenV2MediaMessage
from deepgram.core.events import EventType

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["StreamingSTTSession", "StreamingSTTManager"]


class StreamingSTTSession:
    """Deepgram WebSocket 스트리밍 세션 (SDK 5.3.0 V2SocketClient)"""

    def __init__(self, connection: Any):
        """
        Args:
            connection: Deepgram V2SocketClient (SDK 5.3.0)
        """
        self.connection = connection
        self.transcript_buffer = ""
        self.is_finalized = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
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
            # Deepgram V2SocketClient 메시지 처리
            if hasattr(message, 'raw'):
                # ListenV2ConnectedEvent, ListenV2TurnInfoEvent 등의 raw 필드
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

    async def send_chunk(self, audio_chunk: bytes) -> None:
        """오디오 청크 전송 (비동기)"""
        try:
            # ✅ SDK 5.3.0: send_media() 사용
            media_message = ListenV2MediaMessage(data=audio_chunk)
            self.connection.send_media(media_message)
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
            # ✅ SDK 5.3.0: 마지막 메시지 수신 (최종 결과)
            timeout = 5.0
            loop = asyncio.get_running_loop()
            start_time = loop.time()

            while not self.is_finalized:
                try:
                    elapsed = loop.time() - start_time
                    if elapsed > timeout:
                        logger.warning(f"Timeout waiting for finalized result after {timeout}s")
                        break

                    # ✅ SDK 5.3.0: recv()는 동기 (블로킹)이지만 asyncio 루프에서 실행
                    # 이를 피하기 위해 작은 타임아웃으로 poll
                    await asyncio.sleep(0.1)

                except asyncio.TimeoutError:
                    logger.debug("Timeout waiting for final result")
                    break

            logger.info(f"STT finalized: {self.transcript_buffer}")
            return self.transcript_buffer

        except Exception as e:
            logger.error(f"Failed to finalize streaming: {e}", exc_info=True)
            return self.transcript_buffer


class StreamingSTTManager:
    """스트리밍 STT 세션 관리 (SDK 5.3.0)"""

    def __init__(self, client: Optional[DeepgramClient] = None):
        """
        Args:
            client: Deepgram 클라이언트
        """
        self.client = client or DeepgramClient(api_key=settings.deepgram_api_key)
        self._sessions: Dict[str, StreamingSTTSession] = {}
        self._connections: Dict[str, Any] = {}  # 활성 V2SocketClient 연결 추적
        self._listening_tasks: Dict[str, asyncio.Task] = {}  # recv() 반복 태스크

    async def create_session(self, session_id: str) -> StreamingSTTSession:
        """
        스트리밍 세션 생성 (SDK 5.3.0: V2SocketClient)

        ✅ SDK 5.3.0 특징:
        - listen.v2.connect()는 Iterator를 반환
        - next(iterator)를 호출하여 V2SocketClient를 획득
        - start_listening()으로 수신 대기 시작
        - send_media()로 오디오 전송

        Args:
            session_id: 세션 ID

        Returns:
            StreamingSTTSession

        Raises:
            Exception: 세션 생성 실패 시
        """
        try:
            # ✅ SDK 5.3.0: listen.v2.connect()는 Iterator 반환
            connection_iterator = self.client.listen.v2.connect(
                model=settings.DEEPGRAM_MODEL,
                encoding=settings.DEEPGRAM_ENCODING,
                sample_rate=settings.DEEPGRAM_SAMPLE_RATE,
            )

            # Iterator에서 V2SocketClient 획득
            connection = next(connection_iterator)
            logger.debug(f"V2SocketClient obtained for session {session_id}")

            # 연결 저장
            self._connections[session_id] = connection

            # 세션 생성
            session = StreamingSTTSession(connection)
            self._sessions[session_id] = session

            # ✅ 백그라운드에서 recv() 반복 시작
            # V2SocketClient는 non-blocking recv()를 제공하지 않으므로
            # 별도 태스크에서 recv()를 호출하고 이벤트 발생
            listening_task = asyncio.create_task(
                self._listening_loop(session_id, connection)
            )
            self._listening_tasks[session_id] = listening_task

            logger.info(f"Streaming STT session created: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to create streaming session: {e}", exc_info=True)
            raise

    async def _listening_loop(self, session_id: str, connection: Any) -> None:
        """
        백그라운드에서 메시지 수신 루프 (비동기)

        Deepgram V2SocketClient의 recv()는 동기 함수이므로,
        run_in_executor()를 사용하여 asyncio 루프를 블로킹하지 않음
        """
        loop = asyncio.get_running_loop()

        try:
            logger.debug(f"Starting listening loop for session {session_id}")

            while session_id in self._sessions:
                try:
                    # ✅ recv()를 executor에서 실행하여 asyncio 루프 블로킹 방지
                    # 최대 1초까지 기다림 (타임아웃)
                    response = await asyncio.wait_for(
                        loop.run_in_executor(None, connection.recv),
                        timeout=1.0
                    )

                    if response:
                        logger.debug(f"Received message: {type(response).__name__}")
                        # 이벤트 핸들러가 비동기적으로 메시지 처리

                except asyncio.TimeoutError:
                    # 타임아웃은 정상 - recv()가 메시지 대기 중
                    logger.debug(f"Listening timeout for session {session_id} (normal)")
                    continue

                except Exception as e:
                    error_str = str(e).lower()
                    if any(x in error_str for x in ["connection", "closed", "eof", "reset"]):
                        logger.debug(f"Connection closed for session {session_id}")
                        break
                    else:
                        logger.warning(f"Error in listening loop: {e}")
                        await asyncio.sleep(0.1)  # 에러 후 재시도

        except asyncio.CancelledError:
            logger.debug(f"Listening loop cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Listening loop error for session {session_id}: {e}", exc_info=True)
        finally:
            logger.debug(f"Listening loop ended for session {session_id}")

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
        listening_task = self._listening_tasks.pop(session_id, None)

        if not session:
            logger.warning(f"Session not found for finalization: {session_id}")
            return ""

        try:
            # 수신 루프 종료
            if listening_task and not listening_task.done():
                listening_task.cancel()
                try:
                    await listening_task
                except asyncio.CancelledError:
                    pass

            # 최종 결과 대기
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
                    # V2SocketClient는 finish() 메서드 제공
                    if hasattr(connection, 'finish'):
                        connection.finish()
                    logger.info(f"Connection closed: {session_id}")
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
        listening_task = self._listening_tasks.pop(session_id, None)

        if listening_task and not listening_task.done():
            listening_task.cancel()
            try:
                await listening_task
            except asyncio.CancelledError:
                pass

        if connection:
            try:
                if hasattr(connection, 'finish'):
                    connection.finish()
                logger.info(f"Connection closed: {session_id}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")