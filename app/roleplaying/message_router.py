"""
WebSocket 메시지 라우팅
===============================================

역할:
- 메시지 타입별 핸들러 라우팅
- 메시지 검증 및 파싱
- 메시지 디스패칭
"""

import json
import logging
from typing import Awaitable, Callable, Dict, Optional

from fastapi import WebSocket

from app.roleplaying.ws_models import (InitMessage, UserTextMessage,
                                       UtteranceEndMessage)

logger = logging.getLogger(__name__)

# 핸들러 타입 정의
MessageHandler = Callable[["MessageRouter", WebSocket, str, dict], Awaitable[None]]


class MessageRouter:
    """WebSocket 메시지 라우팅 및 디스패칭"""

    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}

    def register(self, message_type: str, handler: MessageHandler) -> None:
        """메시지 타입에 핸들러 등록"""
        self.handlers[message_type] = handler
        logger.debug(f"Handler registered for message type: {message_type}")

    async def dispatch(
        self,
        websocket: WebSocket,
        session_id: str,
        message: dict
    ) -> bool:
        """
        메시지를 타입에 따라 디스패치

        Args:
            websocket: WebSocket 연결
            session_id: 세션 ID
            message: 메시지 데이터

        Returns:
            성공 여부
        """
        message_type = message.get("type")

        if not message_type:
            logger.warning("Message without type field")
            return False

        handler = self.handlers.get(message_type)

        if not handler:
            logger.warning(f"No handler for message type: {message_type}")
            return False

        try:
            await handler(self, websocket, session_id, message)
            return True
        except Exception as e:
            logger.error(
                f"Handler error for message type {message_type}: {e}",
                exc_info=True
            )
            return False

    async def parse_and_dispatch(
        self,
        websocket: WebSocket,
        session_id: str,
        raw_message: str
    ) -> bool:
        """
        JSON 메시지를 파싱하고 디스패치

        Args:
            websocket: WebSocket 연결
            session_id: 세션 ID
            raw_message: 원본 메시지 (JSON 문자열)

        Returns:
            성공 여부
        """
        try:
            message = json.loads(raw_message)
            return await self.dispatch(websocket, session_id, message)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return False


class DefaultMessageRouter(MessageRouter):
    """기본 메시지 라우터 (모든 핸들러 사전 등록)"""

    def __init__(
        self,
        init_handler: Optional[MessageHandler] = None,
        audio_chunk_handler: Optional[MessageHandler] = None,
        utterance_end_handler: Optional[MessageHandler] = None,
        user_text_handler: Optional[MessageHandler] = None,
        end_session_handler: Optional[MessageHandler] = None,
    ):
        super().__init__()

        if init_handler:
            self.register("INIT", init_handler)
        if audio_chunk_handler:
            self.register("AUDIO_CHUNK", audio_chunk_handler)
        if utterance_end_handler:
            self.register("UTTERANCE_END", utterance_end_handler)
        if user_text_handler:
            self.register("USER_TEXT", user_text_handler)
        if end_session_handler:
            self.register("END_SESSION", end_session_handler)


def create_message_router(
    init_handler: Optional[MessageHandler] = None,
    audio_chunk_handler: Optional[MessageHandler] = None,
    utterance_end_handler: Optional[MessageHandler] = None,
    user_text_handler: Optional[MessageHandler] = None,
    end_session_handler: Optional[MessageHandler] = None,
) -> DefaultMessageRouter:
    """메시지 라우터 팩토리"""
    return DefaultMessageRouter(
        init_handler=init_handler,
        audio_chunk_handler=audio_chunk_handler,
        utterance_end_handler=utterance_end_handler,
        user_text_handler=user_text_handler,
        end_session_handler=end_session_handler,
    )