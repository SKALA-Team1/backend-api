"""
Validation Module for WebSocket Sessions & Messages
====================================================

🔍 목적: WebSocket 실시간 통신에서의 세션/메시지 검증 및 에러 처리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 모듈은 WebSocket 핸들러에서 모든 요청을 처리하기 전에
필수적인 검증을 수행합니다. 세션 상태, 메시지 형식, 초기화 상태 등을 확인하고
적절한 에러 응답을 클라이언트에 전송합니다.

📊 검증 종류:

    [세션 검증] - SessionValidator
    ├─ validate_active(): 세션 존재/활성/만료 확인
    ├─ validate_session_for_operation(): 특정 작업 전 포괄 검증
    └─ validate_initialized(): 세션 초기화 여부 확인

    [메시지 검증] - InitStateValidator
    ├─ requires_initialization(): 초기화 필수 메시지 타입 판별
    ├─ validate_for_message(): 메시지 타입별 초기화 상태 검증
    └─ 규칙: AUDIO_CHUNK, UTTERANCE_END, USER_TEXT는 초기화 후에만 허용

    [에러 처리] - ErrorHandler
    ├─ send_error(): 구조화된 에러 메시지 클라이언트 전송
    ├─ handle_service_error(): 서비스 레이어 에러 처리
    ├─ log_error(): 일관된 형식의 에러 로깅
    └─ 심각도 레벨: INFO, WARNING, ERROR

🔄 검증 흐름:

    WebSocket 메시지 수신
    ↓
    InitStateValidator.validate_for_message() ← 메시지 타입별 초기화 상태 확인
    ↓ (통과)
    SessionValidator.validate_session_for_operation() ← 세션 상태 확인
    ↓ (통과)
    실제 메시지 처리 (STT, AI 응답 등)
    ↓ (실패)
    ErrorHandler.handle_service_error() ← 서비스 에러 처리

⚠️ 설계 원칙:

    1. 빠른 실패 (Fast Fail): 검증 실패 시 즉시 에러 반환
    2. 명확한 에러 코드: 클라이언트가 에러 원인 파악 용이
    3. 컨텍스트 보존: 로깅에 session_id, operation 등 포함
    4. 심각도 구분: 치명적 오류와 경고 구분
    5. 서비스 회복력: 일부 에러는 폴백으로 처리

예시:

    # 세션 검증
    session_state = await SessionValidator.validate_active(websocket, session_id)
    if not session_state:
        return  # 에러 이미 클라이언트로 전송됨

    # 메시지 초기화 상태 검증
    if not await InitStateValidator.validate_for_message(
        websocket, message_type, session_initialized
    ):
        return

    # 서비스 에러 처리
    try:
        result = await some_service.process()
    except Exception as e:
        await ErrorHandler.handle_service_error(
            websocket, "SomeService", e, critical=True
        )
        return

의존성:
    - session_manager: SessionState, SessionStatus, session_manager 인스턴스
    - ws_models: ErrorMessage DTO
    - logging: 에러 로깅
"""

import logging
from typing import Optional

from fastapi import WebSocket

from app.config import settings
from app.roleplaying.core.session_state_manager import SessionStatus, SessionState, session_manager
from app.roleplaying.handlers.ws_message_models import ErrorMessage

logger = logging.getLogger(__name__)


class SessionValidator:
    """세션 상태 검증"""

    @staticmethod
    async def validate_active(
        websocket: WebSocket, session_id: str
    ) -> Optional[SessionState]:
        """
        활성 세션 검증

        ✅ 종합 검증:
        - 세션 존재 여부
        - 세션 상태 (ACTIVE)
        - 세션 만료 여부

        Returns:
            검증된 세션 또는 None (검증 실패 시)
        """
        session_state = session_manager.get_session(session_id)

        if not session_state:
            await ErrorHandler.send_error(
                websocket,
                "Session not found",
                code="SESSION_NOT_FOUND",
                severity=ErrorHandler.SEVERITY_WARNING
            )
            return None

        if session_state.status != SessionStatus.ACTIVE:
            await ErrorHandler.send_error(
                websocket,
                f"Session not active (status={session_state.status})",
                code="SESSION_NOT_ACTIVE",
                severity=ErrorHandler.SEVERITY_WARNING
            )
            return None

        if session_state.is_expired():
            await ErrorHandler.send_error(
                websocket,
                "Session expired",
                code="SESSION_EXPIRED",
                severity=ErrorHandler.SEVERITY_WARNING
            )
            return None

        return session_state

    @staticmethod
    async def validate_session_for_operation(
        websocket: WebSocket,
        session_id: str,
        operation: str = "operation"
    ) -> Optional[SessionState]:
        """
        특정 작업 수행 전 세션 검증

        ✅ 추가 검증:
        - 활성 세션 존재 확인
        - 세션 상태 검증
        - 만료 여부 확인
        - 작업 로깅

        Args:
            websocket: WebSocket 연결
            session_id: 세션 ID
            operation: 수행할 작업 명 (로깅용)

        Returns:
            검증된 세션 또는 None
        """
        session_state = await SessionValidator.validate_active(websocket, session_id)

        if session_state:
            logger.debug(
                f"Session validation passed for {operation}: "
                f"session={session_id}, status={session_state.status}, "
                f"turns={session_state.ai_turn_count}"
            )
        else:
            logger.warning(
                f"Session validation failed for {operation}: "
                f"session={session_id}"
            )

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