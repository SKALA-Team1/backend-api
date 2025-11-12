"""
==============================================================
Exception Handling Module
==============================================================
Shared exception types and FastAPI exception handler wiring.

역할:
    - 애플리케이션 전역에서 사용할 공통 예외(AppException) 정의
    - 도메인 로직(App 내부 비즈니스 에러)과 Pydantic ValidationError를
      일관된 JSON 형식으로 응답하도록 FastAPI에 핸들러 등록
    - 개발자 정의 예외 발생 시 status_code, detail, extra 필드를 사용해
      클라이언트에게 명확하고 구조화된 오류 메시지 전달

핵심 기능:
    1. AppException : 커스텀 예외 클래스 (HTTP 상태 코드와 추가 데이터 포함)
    2. _app_exception_handler : AppException → JSON 응답 변환
    3. _validation_exception_handler : ValidationError → JSON 응답 변환
    4. register_exception_handlers : FastAPI 앱에 예외 핸들러 등록

사용예시:
    from fastapi import FastAPI
    from app.core.exceptions import register_exception_handlers, AppException

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/error")
    def raise_error():
        raise AppException("Something went wrong", status_code=400, extra={"field": "user"})
--------------------------------------------------------------
Author: [Your Name or Team]
Created: 2025-11-12
--------------------------------------------------------------
"""

from __future__ import annotations
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.http_status import StatusCode


class AppException(Exception):
    """
    Domain-level exception that allows custom status codes and payload data.

    역할:
        - 개발자가 서비스 로직에서 명시적으로 예외를 발생시킬 때 사용
        - detail(메시지), status_code(HTTP 코드), extra(추가 데이터) 지정 가능

    예시:
        raise AppException(
            detail="User not found",
            status_code=404,
            extra={"user_id": 123}
        )
    """

    def __init__(
        self,
        detail: str,
        status_code: int | StatusCode = StatusCode.BAD_REQUEST,
        extra: dict[str, Any] | None = None,
    ):
        self.detail = detail
        self.status_code = int(status_code)
        self.extra = extra or {}
        super().__init__(detail)


def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """
    Translate AppException into a structured JSON response.

    Args:
        _: Request (요청 객체, 여기서는 사용하지 않음)
        exc: AppException 예외 인스턴스

    Returns:
        JSONResponse: {"detail": 메시지, ...extra} 형식의 응답
    """
    payload = {"detail": exc.detail, **exc.extra}
    return JSONResponse(status_code=exc.status_code, content=payload)


def _validation_exception_handler(_: Request, exc: ValidationError) -> JSONResponse:
    """
    Convert Pydantic validation errors to JSON response (HTTP 422).

    Args:
        _: Request (요청 객체)
        exc: ValidationError (요청 데이터 검증 실패)

    Returns:
        JSONResponse: {"detail": [오류 목록]} 형식의 응답
    """
    return JSONResponse(status_code=int(StatusCode.UNPROCESSABLE_ENTITY), content={"detail": exc.errors()})


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach shared exception handlers to the FastAPI app.

    설명:
        - AppException 및 ValidationError에 대한 공통 핸들러를 등록
        - 앱 전체에서 발생하는 예외를 일관된 JSON 형태로 처리

    예시:
        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(ValidationError, _validation_exception_handler)
