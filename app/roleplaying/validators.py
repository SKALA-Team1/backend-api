"""
세션 및 메시지 검증 로직
===============================================

역할:
- 세션 상태 검증
- 메시지 초기화 상태 검증
- 에러 메시지 생성 및 전송
"""

import logging
from typing import Optional

from fastapi import WebSocket

from app.config import settings
from app.roleplaying.session_manager import SessionStatus, SessionState, session_manager
from app.roleplaying.ws_models import ErrorMessage

logger = logging.getLogger(__name__)


class SessionValidator:
    """세션 상태 검증"""

    @staticmethod
    async def validate_active(
        websocket: WebSocket, session_id: str
    ) -> Optional[SessionState]:
        """
        활성 세션 검증

        Returns:
            검증된 세션 또는 None (검증 실패 시)
        """
        session_state = session_manager.get_session(session_id)

        if not session_state:
            await ErrorHandler.send_error(websocket, "Session not found")
            return None

        if session_state.status != SessionStatus.ACTIVE:
            await ErrorHandler.send_error(websocket, "Session not active")
            return None

        if session_state.is_expired():
            await ErrorHandler.send_error(websocket, "Session expired")
            return None

        return session_state

    @staticmethod
    async def validate_initialized(
        websocket: WebSocket, session_initialized: bool
    ) -> bool:
        """
        세션 초기화 상태 검증

        Returns:
            True if 검증 통과, False otherwise
        """
        if not session_initialized:
            await ErrorHandler.send_error(websocket, "Session not initialized")
            return False
        return True


class InitStateValidator:
    """메시지별 초기화 상태 검증"""

    # 초기화 필수 메시지 타입
    REQUIRES_INIT = {"AUDIO_CHUNK", "UTTERANCE_END", "USER_TEXT"}

    # 초기화 불가 메시지 타입 (INIT 전에만 처리)
    REQUIRES_NO_INIT = {"INIT"}

    @staticmethod
    def requires_initialization(message_type: str) -> bool:
        """이 메시지는 초기화가 필요한가?"""
        return message_type in InitStateValidator.REQUIRES_INIT

    @staticmethod
    async def validate_for_message(
        websocket: WebSocket,
        message_type: str,
        session_initialized: bool
    ) -> bool:
        """메시지 타입에 따라 초기화 상태 검증"""
        if InitStateValidator.requires_initialization(message_type):
            if not session_initialized:
                await ErrorHandler.send_error(
                    websocket,
                    "Session not initialized. Send INIT message first."
                )
                return False

        return True


class ErrorHandler:
    """통일된 에러 처리"""

    # 에러 심각도
    SEVERITY_INFO = "INFO"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_ERROR = "ERROR"

    @staticmethod
    async def send_error(
        websocket: WebSocket,
        message: str,
        code: Optional[str] = None,
        severity: str = SEVERITY_ERROR
    ) -> None:
        """
        클라이언트에 에러 메시지 전송

        Args:
            websocket: WebSocket 연결
            message: 에러 메시지
            code: 에러 코드 (선택사항)
            severity: 심각도 (INFO, WARNING, ERROR)
        """
        try:
            error_msg = ErrorMessage(message=message, code=code)
            await websocket.send_json(error_msg.model_dump())

            log_level = {
                ErrorHandler.SEVERITY_INFO: logger.info,
                ErrorHandler.SEVERITY_WARNING: logger.warning,
                ErrorHandler.SEVERITY_ERROR: logger.error,
            }.get(severity, logger.error)

            log_level(f"Error sent to client: {message} (code={code})")

        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    @staticmethod
    async def handle_service_error(
        websocket: WebSocket,
        service_name: str,
        error: Exception,
        critical: bool = False,
        fallback_message: Optional[str] = None
    ) -> None:
        """
        서비스 에러 처리

        Args:
            websocket: WebSocket 연결
            service_name: 서비스 이름 (STT, Spring2 등)
            error: 발생한 에러
            critical: 치명적 에러 여부
            fallback_message: 폴백 메시지
        """
        error_message = fallback_message or f"{service_name} service error"

        if critical:
            logger.error(f"{service_name} critical error: {error}", exc_info=True)
            await ErrorHandler.send_error(
                websocket,
                error_message,
                code=f"{service_name}_ERROR",
                severity=ErrorHandler.SEVERITY_ERROR
            )
        else:
            logger.warning(f"{service_name} non-critical error: {error}")
            await ErrorHandler.send_error(
                websocket,
                error_message,
                code=f"{service_name}_WARNING",
                severity=ErrorHandler.SEVERITY_WARNING
            )

    @staticmethod
    def log_error(
        context: str,
        error: Exception,
        session_id: Optional[str] = None,
        critical: bool = True
    ) -> None:
        """
        에러를 로깅합니다

        Args:
            context: 에러 컨텍스트
            error: 에러 객체
            session_id: 세션 ID (선택사항)
            critical: 치명적 에러 여부
        """
        session_info = f" (session={session_id})" if session_id else ""

        if critical:
            logger.error(f"{context}{session_info}: {error}", exc_info=True)
        else:
            logger.warning(f"{context}{session_info}: {error}")