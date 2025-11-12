"""
==============================================================
Centralized Logging Configuration
==============================================================
Centralized JSON logging configuration for the FastAPI app.

역할:
    - FastAPI, Uvicorn, 그리고 애플리케이션(app) 전반에 걸쳐 통일된 로깅 형식 설정
    - 로그를 사람이 읽기 좋은 JSON 형태로 출력 (Cloud 환경에 적합)
    - 개발 환경에서는 DEBUG, 운영 환경에서는 INFO 수준으로 자동 설정
    - 로거 이름별(uvicorn, app 등) 세부 로그 설정 통합 관리

핵심 기능:
    1. _build_logging_config(level): JSON 형식 로깅 딕셔너리 구성
    2. setup_logging(): 환경에 따라 로그 레벨 설정 및 적용
    3. get_logger(name): 모듈별 로거 인스턴스 반환

사용 예시:
    from app.core.logging_config import setup_logging, get_logger

    setup_logging()
    logger = get_logger(__name__)
    logger.info("Server started")
--------------------------------------------------------------
Author: 정도현
Created: 2025-11-12
--------------------------------------------------------------
"""

from __future__ import annotations
import logging
from logging.config import dictConfig

from app.config import settings


def _build_logging_config(level: str) -> dict[str, object]:
    """
    Return a dictConfig payload that formats logs as structured JSON.

    설명:
        - Python logging.dictConfig()에 전달할 설정 딕셔너리 생성
        - 로그 포맷을 JSON 형태로 지정하여 클라우드/컨테이너 환경에서 분석하기 쉽게 함
        - 로그 항목: level, time, name, message

    Args:
        level (str): 로그 레벨 (예: "DEBUG", "INFO")

    Returns:
        dict[str, object]: dictConfig에 전달할 로깅 설정
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,  # 기존 로거 비활성화 방지
        "formatters": {
            "json": {
                # 로그 메시지를 JSON 형태로 구성
                "format": (
                    '{"level":"%(levelname)s","time":"%(asctime)s",'
                    '"name":"%(name)s","message":"%(message)s"}'
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",  # ISO8601 시간 포맷
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",  # 콘솔 출력 핸들러
                "formatter": "json",
            },
        },
        "loggers": {
            # Uvicorn 및 FastAPI 관련 로거들
            "uvicorn": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": level, "propagate": False},
            # 앱 내부 로거
            "app": {"handlers": ["default"], "level": level, "propagate": False},
        },
        # 이름 없는 기본 로거 설정
        "root": {"handlers": ["default"], "level": level},
    }


def setup_logging() -> None:
    """
    Initialize logging once during application startup.

    설명:
        - settings.debug 값을 기반으로 로그 레벨 결정
        - DEBUG 모드: 개발용(세부 로그 포함)
        - INFO 모드: 운영용(요약 로그만)
        - 생성된 설정을 dictConfig()로 적용
    """
    level = "DEBUG" if settings.debug else "INFO"
    dictConfig(_build_logging_config(level))


def get_logger(name: str = "app") -> logging.Logger:
    """
    Return a module-scoped logger that abides by the shared config.

    설명:
        - 모듈별로 로거를 생성하거나 가져옴
        - 같은 이름으로 요청 시 동일 로거를 반환 (중복 생성 방지)
        - setup_logging()이 먼저 실행되어 있어야 설정이 적용됨

    Args:
        name (str): 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger: 지정된 이름의 로거 객체
    """
    return logging.getLogger(name)