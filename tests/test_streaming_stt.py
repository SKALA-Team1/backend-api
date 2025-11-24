"""
Deepgram 스트리밍 STT 테스트
============================

목표: listen.live.v2.connect() API 변경 후 세션 생성 오류 해결 확인
"""

import asyncio
import json
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

logger = logging.getLogger(__name__)


class TestStreamingSTTManager:
    """스트리밍 STT 매니저 테스트"""

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """✅ 세션 생성 성공 테스트"""
        from app.roleplaying.services.streaming_stt_manager import StreamingSTTManager
        from app.config import settings

        # Mock DeepgramClient
        with patch('app.roleplaying.services.streaming_stt_manager.DeepgramClient') as mock_client_class:
            # Mock connection 객체
            mock_connection = AsyncMock()
            mock_connection.send = AsyncMock()
            mock_connection.recv = AsyncMock()
            mock_connection.finish = AsyncMock()
            mock_connection.aclose = AsyncMock()

            # Mock listen.live.v2.connect()
            mock_client_instance = MagicMock()
            mock_client_instance.listen.live.v2.connect = AsyncMock(return_value=mock_connection)
            mock_client_class.return_value = mock_client_instance

            # 매니저 생성 및 세션 생성
            manager = StreamingSTTManager(client=mock_client_instance)
            session_id = "test-session-001"

            try:
                session = await manager.create_session(session_id)

                # ✅ 검증
                assert session is not None
                assert session.connection == mock_connection
                assert session_id in manager._sessions
                assert session_id in manager._connections

                logger.info("✅ Session creation succeeded!")
                print("✅ Session creation test PASSED")

            except AttributeError as e:
                if "'ListenClient' object has no attribute 'live'" in str(e):
                    pytest.fail(f"❌ Old API still being used: {e}")
                raise

    @pytest.mark.asyncio
    async def test_create_session_api_structure(self):
        """✅ API 구조 검증 (listen.live.v2.connect 호출 확인)"""
        from app.roleplaying.services.streaming_stt_manager import StreamingSTTManager

        with patch('app.roleplaying.services.streaming_stt_manager.DeepgramClient') as mock_client_class:
            mock_connection = AsyncMock()
            mock_client_instance = MagicMock()

            # 올바른 API 구조 확인: listen.live.v2.connect()
            mock_client_instance.listen.live.v2.connect = AsyncMock(return_value=mock_connection)
            mock_client_class.return_value = mock_client_instance

            manager = StreamingSTTManager(client=mock_client_instance)

            try:
                await manager.create_session("test-session-002")

                # ✅ listen.live.v2.connect() 호출 확인
                mock_client_instance.listen.live.v2.connect.assert_called_once()

                # ✅ 올바른 파라미터 전달 확인
                call_kwargs = mock_client_instance.listen.live.v2.connect.call_args[1]
                assert "model" in call_kwargs
                assert "encoding" in call_kwargs
                assert "sample_rate" in call_kwargs

                logger.info("✅ API structure is correct!")
                print("✅ API structure test PASSED")

            except AttributeError as e:
                pytest.fail(f"❌ API structure error: {e}")

    @pytest.mark.asyncio
    async def test_session_event_handlers(self):
        """✅ 이벤트 핸들러 등록 확인"""
        from app.roleplaying.services.streaming_stt_manager import StreamingSTTSession

        # Mock connection
        mock_connection = AsyncMock()
        mock_connection.on = MagicMock()  # 이벤트 핸들러 등록 메서드

        # 세션 생성 시 이벤트 핸들러 등록되는지 확인
        session = StreamingSTTSession(mock_connection)

        # ✅ 이벤트 핸들러가 등록되었는지 확인
        # on() 메서드가 여러 번 호출되어야 함 (OPEN, MESSAGE, CLOSE, ERROR)
        assert mock_connection.on.call_count >= 4, \
            f"Expected at least 4 event handlers, got {mock_connection.on.call_count}"

        logger.info("✅ Event handlers registered!")
        print("✅ Event handlers test PASSED")

    @pytest.mark.asyncio
    async def test_message_processing(self):
        """✅ 이벤트 기반 메시지 처리"""
        from app.roleplaying.services.streaming_stt_manager import StreamingSTTSession

        mock_connection = AsyncMock()
        session = StreamingSTTSession(mock_connection)

        # Mock 메시지 데이터
        test_message = {
            "type": "Results",
            "result": {
                "results": [
                    {
                        "transcript": "Hello world",
                        "confidence": 0.95
                    }
                ]
            }
        }

        # 메시지 핸들러 호출
        session._on_message(test_message)

        # ✅ 트랜스크립트 버퍼에 저장되었는지 확인
        assert session.transcript_buffer == "Hello world"

        logger.info("✅ Message processing works!")
        print("✅ Message processing test PASSED")

    @pytest.mark.asyncio
    async def test_send_chunk(self):
        """✅ 오디오 청크 전송"""
        from app.roleplaying.services.streaming_stt_manager import StreamingSTTSession

        mock_connection = AsyncMock()
        mock_connection.send = AsyncMock()

        session = StreamingSTTSession(mock_connection)

        # 오디오 청크 전송
        test_audio = b'\x00\x01\x02\x03'
        await session.send_chunk(test_audio)

        # ✅ send() 호출 확인
        mock_connection.send.assert_called_once_with(test_audio)

        logger.info("✅ Audio chunk sent!")
        print("✅ Send chunk test PASSED")


class TestWebSocketIntegration:
    """WebSocket 통합 테스트"""

    @pytest.mark.asyncio
    async def test_websocket_init_message(self):
        """✅ WebSocket INIT 메시지 처리"""
        from fastapi.testclient import TestClient
        from app.main import app
        from unittest.mock import patch

        client = TestClient(app)
        session_id = "test-ws-session-001"

        # Deepgram 세션 생성 Mock
        with patch('app.roleplaying.services.stt_service.stt_service.create_streaming_session') as mock_create:
            mock_create.return_value = AsyncMock()

            # Redis 세션 데이터 Mock
            with patch('app.integrations.clients.redis_client.RedisSessionValidator.validate_session') as mock_validate:
                mock_validate.return_value = {
                    "userId": 1,
                    "scenarioId": 1,
                    "status": "ACTIVE",
                    "expiresAt": "2025-12-31T23:59:59Z"
                }

                try:
                    with client.websocket_connect(f"/ws/roleplaying/{session_id}") as websocket:
                        # INIT 메시지 전송 (userId 필수, fixedQuestions 최소 3개)
                        init_msg = {
                            "type": "INIT",
                            "userId": 1,
                            "subjectId": 1,
                            "myRole": "Student",
                            "aiRole": "Teacher",
                            "fixedQuestions": [
                                "How are you?",
                                "What is your name?",
                                "Where are you from?"
                            ]
                        }
                        websocket.send_json(init_msg)

                        # ACK 메시지 수신
                        response = websocket.receive_json()
                        assert response.get("type") in ["ACK", "AI_TEXT"]

                        logger.info("✅ INIT message processed successfully!")
                        print("✅ WebSocket INIT test PASSED")

                except Exception as e:
                    logger.error(f"❌ WebSocket test failed: {e}")
                    pytest.fail(f"WebSocket connection failed: {e}")


# ============================================================================
# 독립 실행용 스크립트
# ============================================================================

async def run_standalone_tests():
    """독립 실행 테스트"""
    print("\n" + "="*60)
    print("🧪 Deepgram SDK 3.x 스트리밍 STT 테스트 시작")
    print("="*60)

    from app.roleplaying.services.streaming_stt_manager import StreamingSTTManager
    from unittest.mock import AsyncMock, MagicMock, patch

    # Test 1: 세션 생성
    print("\n[Test 1] 세션 생성 (listen.live.v2.connect 호출 확인)...")
    with patch('app.roleplaying.services.streaming_stt_manager.DeepgramClient') as mock_client_class:
        mock_connection = AsyncMock()
        mock_client = MagicMock()
        mock_client.listen.live.v2.connect = AsyncMock(return_value=mock_connection)
        mock_client_class.return_value = mock_client

        try:
            manager = StreamingSTTManager(client=mock_client)
            session = await manager.create_session("test-001")

            # API 호출 확인
            if mock_client.listen.live.v2.connect.called:
                print("✅ PASS: listen.live.v2.connect() 호출됨")
            else:
                print("❌ FAIL: listen.live.v2.connect() 호출 안됨")

        except AttributeError as e:
            if "live" in str(e):
                print(f"❌ FAIL: {e}")
                print("   → 여전히 old API를 사용하고 있습니다")
            else:
                raise

    # Test 2: 이벤트 핸들러 등록
    print("\n[Test 2] 이벤트 핸들러 등록 확인...")
    with patch('app.roleplaying.services.streaming_stt_manager.DeepgramClient') as mock_client_class:
        mock_connection = AsyncMock()
        mock_connection.on = MagicMock()
        mock_client = MagicMock()
        mock_client.listen.live.v2.connect = AsyncMock(return_value=mock_connection)
        mock_client_class.return_value = mock_client

        manager = StreamingSTTManager(client=mock_client)
        session = await manager.create_session("test-002")

        handler_count = mock_connection.on.call_count
        if handler_count >= 4:
            print(f"✅ PASS: {handler_count}개의 이벤트 핸들러 등록됨")
        else:
            print(f"❌ FAIL: {handler_count}개 핸들러만 등록됨 (최소 4개 필요)")

    print("\n" + "="*60)
    print("✅ 모든 테스트 완료!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # pytest 없이 독립 실행
    asyncio.run(run_standalone_tests())