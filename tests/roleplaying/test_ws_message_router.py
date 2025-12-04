"""
Test WebSocket Message Router
==============================

메시지 라우팅 및 디스패칭 테스트:
- MessageRouter (기본 라우터)
- DefaultMessageRouter (기본 핸들러 사전 등록)
- create_message_router (팩토리 함수)
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.roleplaying.handlers.ws_message_router import (
    MessageRouter,
    DefaultMessageRouter,
    create_message_router
)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_handlers():
    """Mock 핸들러들"""
    return {
        "init_handler": AsyncMock(),
        "audio_chunk_handler": AsyncMock(),
        "utterance_end_handler": AsyncMock(),
        "user_text_handler": AsyncMock(),
        "end_session_handler": AsyncMock(),
    }


class TestMessageRouter:
    """기본 메시지 라우터 테스트"""

    def test_init(self):
        """라우터 초기화"""
        router = MessageRouter()
        assert router.handlers == {}

    def test_register_handler(self):
        """핸들러 등록"""
        router = MessageRouter()
        handler = AsyncMock()

        router.register("INIT", handler)
        assert "INIT" in router.handlers
        assert router.handlers["INIT"] == handler

    def test_register_multiple_handlers(self):
        """여러 핸들러 등록"""
        router = MessageRouter()
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        router.register("INIT", handler1)
        router.register("AUDIO_CHUNK", handler2)

        assert len(router.handlers) == 2
        assert router.handlers["INIT"] == handler1
        assert router.handlers["AUDIO_CHUNK"] == handler2

    @pytest.mark.asyncio
    async def test_dispatch_success(self, mock_websocket, mock_handlers):
        """메시지 디스패치 성공"""
        router = MessageRouter()
        router.register("INIT", mock_handlers["init_handler"])

        message = {"type": "INIT", "userId": 1}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is True
        mock_handlers["init_handler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_no_message_type(self, mock_websocket):
        """메시지 타입 없음"""
        router = MessageRouter()
        message = {"userId": 1}  # type 필드 없음

        result = await router.dispatch(mock_websocket, "test-session", message)
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_no_handler(self, mock_websocket):
        """등록되지 않은 핸들러"""
        router = MessageRouter()
        message = {"type": "UNKNOWN"}

        result = await router.dispatch(mock_websocket, "test-session", message)
        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_handler_error(self, mock_websocket, mock_handlers):
        """핸들러 에러 처리"""
        router = MessageRouter()
        handler = AsyncMock(side_effect=Exception("Handler error"))
        router.register("INIT", handler)

        message = {"type": "INIT"}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is False
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_and_dispatch_success(self, mock_websocket, mock_handlers):
        """JSON 파싱 및 디스패치 성공"""
        router = MessageRouter()
        router.register("USER_TEXT", mock_handlers["user_text_handler"])

        raw_message = json.dumps({"type": "USER_TEXT", "text": "Hello"})
        result = await router.parse_and_dispatch(
            mock_websocket, "test-session", raw_message
        )

        assert result is True
        mock_handlers["user_text_handler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_and_dispatch_invalid_json(self, mock_websocket):
        """잘못된 JSON 파싱"""
        router = MessageRouter()
        raw_message = "{ invalid json }"

        result = await router.parse_and_dispatch(
            mock_websocket, "test-session", raw_message
        )

        assert result is False


class TestDefaultMessageRouter:
    """기본 핸들러 사전 등록 라우터 테스트"""

    def test_init_all_handlers(self, mock_handlers):
        """모든 핸들러 등록"""
        router = DefaultMessageRouter(
            init_handler=mock_handlers["init_handler"],
            audio_chunk_handler=mock_handlers["audio_chunk_handler"],
            utterance_end_handler=mock_handlers["utterance_end_handler"],
            user_text_handler=mock_handlers["user_text_handler"],
            end_session_handler=mock_handlers["end_session_handler"],
        )

        assert len(router.handlers) == 5
        assert "INIT" in router.handlers
        assert "AUDIO_CHUNK" in router.handlers
        assert "UTTERANCE_END" in router.handlers
        assert "USER_TEXT" in router.handlers
        assert "END_SESSION" in router.handlers

    def test_init_partial_handlers(self, mock_handlers):
        """일부 핸들러만 등록"""
        router = DefaultMessageRouter(
            init_handler=mock_handlers["init_handler"],
            user_text_handler=mock_handlers["user_text_handler"],
        )

        assert len(router.handlers) == 2
        assert "INIT" in router.handlers
        assert "USER_TEXT" in router.handlers
        assert "AUDIO_CHUNK" not in router.handlers

    def test_init_no_handlers(self):
        """핸들러 없이 초기화"""
        router = DefaultMessageRouter()
        assert len(router.handlers) == 0

    @pytest.mark.asyncio
    async def test_dispatch_init(self, mock_websocket, mock_handlers):
        """INIT 메시지 디스패치"""
        router = DefaultMessageRouter(
            init_handler=mock_handlers["init_handler"]
        )

        message = {"type": "INIT", "userId": 1, "subjectId": 1}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is True
        mock_handlers["init_handler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_audio_chunk(self, mock_websocket, mock_handlers):
        """AUDIO_CHUNK 메시지 디스패치"""
        router = DefaultMessageRouter(
            audio_chunk_handler=mock_handlers["audio_chunk_handler"]
        )

        message = {"type": "AUDIO_CHUNK", "data": b"audio_data"}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is True
        mock_handlers["audio_chunk_handler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_user_text(self, mock_websocket, mock_handlers):
        """USER_TEXT 메시지 디스패치"""
        router = DefaultMessageRouter(
            user_text_handler=mock_handlers["user_text_handler"]
        )

        message = {"type": "USER_TEXT", "text": "I think this is good"}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is True
        mock_handlers["user_text_handler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_message(self, mock_websocket, mock_handlers):
        """등록되지 않은 메시지 타입"""
        router = DefaultMessageRouter(
            init_handler=mock_handlers["init_handler"]
        )

        # END_SESSION 핸들러는 등록되지 않음
        message = {"type": "END_SESSION"}
        result = await router.dispatch(mock_websocket, "test-session", message)

        assert result is False
        mock_handlers["init_handler"].assert_not_called()


class TestCreateMessageRouter:
    """팩토리 함수 테스트"""

    def test_create_with_all_handlers(self, mock_handlers):
        """모든 핸들러와 함께 라우터 생성"""
        router = create_message_router(
            init_handler=mock_handlers["init_handler"],
            audio_chunk_handler=mock_handlers["audio_chunk_handler"],
            utterance_end_handler=mock_handlers["utterance_end_handler"],
            user_text_handler=mock_handlers["user_text_handler"],
            end_session_handler=mock_handlers["end_session_handler"],
        )

        assert isinstance(router, DefaultMessageRouter)
        assert len(router.handlers) == 5

    def test_create_with_partial_handlers(self, mock_handlers):
        """일부 핸들러와 함께 라우터 생성"""
        router = create_message_router(
            init_handler=mock_handlers["init_handler"],
            user_text_handler=mock_handlers["user_text_handler"],
        )

        assert isinstance(router, DefaultMessageRouter)
        assert len(router.handlers) == 2

    def test_create_with_no_handlers(self):
        """핸들러 없이 라우터 생성"""
        router = create_message_router()

        assert isinstance(router, DefaultMessageRouter)
        assert len(router.handlers) == 0

    @pytest.mark.asyncio
    async def test_create_and_dispatch(self, mock_websocket, mock_handlers):
        """팩토리로 생성한 라우터에서 디스패치"""
        router = create_message_router(
            init_handler=mock_handlers["init_handler"],
            user_text_handler=mock_handlers["user_text_handler"],
        )

        # INIT 메시지
        message1 = {"type": "INIT", "userId": 1}
        result1 = await router.dispatch(mock_websocket, "test-session", message1)
        assert result1 is True

        # USER_TEXT 메시지
        message2 = {"type": "USER_TEXT", "text": "Answer"}
        result2 = await router.dispatch(mock_websocket, "test-session", message2)
        assert result2 is True

        assert mock_handlers["init_handler"].call_count == 1
        assert mock_handlers["user_text_handler"].call_count == 1


class TestMessageRouterIntegration:
    """통합 라우팅 테스트"""

    @pytest.mark.asyncio
    async def test_full_session_workflow(self, mock_websocket):
        """전체 세션 워크플로우"""
        # 각 메시지 타입별 핸들러
        init_handler = AsyncMock()
        audio_handler = AsyncMock()
        utterance_handler = AsyncMock()
        end_handler = AsyncMock()

        router = create_message_router(
            init_handler=init_handler,
            audio_chunk_handler=audio_handler,
            utterance_end_handler=utterance_handler,
            end_session_handler=end_handler,
        )

        # 1단계: INIT
        result1 = await router.dispatch(
            mock_websocket,
            "test-session",
            {"type": "INIT", "userId": 1, "subjectId": 1}
        )
        assert result1 is True

        # 2단계: AUDIO_CHUNK
        result2 = await router.dispatch(
            mock_websocket,
            "test-session",
            {"type": "AUDIO_CHUNK"}
        )
        assert result2 is True

        # 3단계: UTTERANCE_END
        result3 = await router.dispatch(
            mock_websocket,
            "test-session",
            {"type": "UTTERANCE_END"}
        )
        assert result3 is True

        # 4단계: END_SESSION
        result4 = await router.dispatch(
            mock_websocket,
            "test-session",
            {"type": "END_SESSION"}
        )
        assert result4 is True

        # 모든 핸들러가 호출되었는지 확인
        assert init_handler.call_count == 1
        assert audio_handler.call_count == 1
        assert utterance_handler.call_count == 1
        assert end_handler.call_count == 1

    @pytest.mark.asyncio
    async def test_json_parse_and_dispatch_workflow(self, mock_websocket):
        """JSON 파싱 및 디스패치 워크플로우"""
        init_handler = AsyncMock()
        text_handler = AsyncMock()

        router = create_message_router(
            init_handler=init_handler,
            user_text_handler=text_handler,
        )

        # INIT 메시지 (JSON)
        init_message = json.dumps({
            "type": "INIT",
            "userId": 1,
            "subjectId": 1,
            "myRole": "Engineer",
            "aiRole": "Lead",
            "fixedQuestions": ["Q1", "Q2", "Q3"]
        })
        result1 = await router.parse_and_dispatch(
            mock_websocket, "test-session", init_message
        )
        assert result1 is True

        # USER_TEXT 메시지 (JSON)
        text_message = json.dumps({
            "type": "USER_TEXT",
            "text": "This is my response"
        })
        result2 = await router.parse_and_dispatch(
            mock_websocket, "test-session", text_message
        )
        assert result2 is True

        assert init_handler.call_count == 1
        assert text_handler.call_count == 1

    @pytest.mark.asyncio
    async def test_handler_receives_correct_arguments(self, mock_websocket):
        """핸들러가 올바른 인자를 받는지 확인"""
        handler = AsyncMock()
        router = create_message_router(init_handler=handler)

        message = {"type": "INIT", "userId": 1, "data": "test"}
        await router.dispatch(mock_websocket, "session-123", message)

        # 핸들러가 호출된 인자 확인
        call_args = handler.call_args
        assert call_args[0][0] == router  # router
        assert call_args[0][1] == mock_websocket  # websocket
        assert call_args[0][2] == "session-123"  # session_id
        assert call_args[0][3] == message  # message
