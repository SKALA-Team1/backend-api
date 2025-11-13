"""
==============================================================
Dependency Utilities for FastAPI
==============================================================
FastAPI dependency helpers shared across routers.

역할:
    - 공용 의존성(Dependencies)을 정의하여 라우터 간 중복 제거
    - SQLAlchemy 세션 주입 (요청 단위 세션 생성 및 종료)
    - 전역 Settings 객체(FastAPI Config) 의존성 제공

주요 기능:
    1. get_db():  요청마다 새로운 DB 세션을 열고 자동으로 닫음
    2. get_app_settings():  캐싱된 Pydantic Settings 인스턴스를 주입

사용예시 (라우터 내):
    from fastapi import Depends, APIRouter
    from app.core.deps import get_db, get_app_settings

    router = APIRouter()

    @router.get("/users")
    def list_users(db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)):
        ...
--------------------------------------------------------------
Author: 정도현
Created: 2025-11-12
--------------------------------------------------------------
"""

from collections.abc import Generator
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy session and close it once the request finishes.

    설명:
        - 각 요청마다 DB 세션(SessionLocal)을 새로 생성
        - 요청이 완료되면 finally 블록에서 세션을 자동으로 닫음
        - FastAPI의 Depends()로 라우터 함수에 주입 가능

    예시:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_app_settings() -> Settings:
    """
    Expose the cached Settings instance as a dependency.

    설명:
        - app.config 모듈의 get_settings()을 래핑
        - Settings 객체(Pydantic 기반 환경설정 클래스)를 FastAPI의 Depends()로 주입 가능

    예시:
        @router.get("/status")
        def get_status(settings: Settings = Depends(get_app_settings)):
            return {"debug": settings.debug, "env": settings.environment}
    """
    return get_settings()