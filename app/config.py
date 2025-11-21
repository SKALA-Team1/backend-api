"""
==============================================================
Config Module
==============================================================
Application-wide configuration helpers built on Pydantic Settings.

역할:
    - 환경변수(.env) 기반 설정값을 중앙에서 관리
    - Redis, S3(MinIO/AWS S3), Spring2 API, Database, OpenAI 등
      SKALA FastAPI가 필요로 하는 모든 설정을 단일 클래스로 관리
    - Settings 인스턴스를 전역에서 재사용하도록 캐싱 처리

사용예시:
    from app.config import settings

    print(settings.REDIS_URL)
    print(settings.S3_BUCKET_NAME)
    print(settings.database_url)
    if settings.debug:
        print("Running in development mode")

--------------------------------------------------------------
Author: 정도현
Created: 2025-11-12
Modified: 2025-11-17
--------------------------------------------------------------
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized environment-driven settings object.

    역할:
        - .env 파일 혹은 시스템 환경변수에서 설정값을 자동 로드
        - 개발(local), 스테이징, 프로덕션 환경까지 구분 관리
        - FastAPI 전역에서 import하여 공통 설정으로 사용
    """

    # -------------------------------------
    # Base Config
    # -------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -------------------------------------
    # DB 환경변수
    # -------------------------------------
    database_url: str = Field(..., alias="DATABASE_URL")
    environment: str = Field("development", alias="ENVIRONMENT")

    # -------------------------------------
    # OpenAI
    # -------------------------------------
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # -------------------------------------
    # Redis
    # -------------------------------------
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # -------------------------------------
    # S3 (MinIO 또는 AWS S3)
    # -------------------------------------
    S3_ENDPOINT_URL: str = Field("http://localhost:9000", alias="S3_ENDPOINT_URL")
    S3_ACCESS_KEY: str = Field("minioadmin", alias="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field("minioadmin123", alias="S3_SECRET_KEY")
    S3_BUCKET_NAME: str = Field("skala", alias="S3_BUCKET_NAME")
    S3_REGION: str = Field("us-east-1", alias="S3_REGION")

    # -------------------------------------
    # Spring 2 Backend
    # -------------------------------------
    SPRING2_BASE_URL: str = Field("http://localhost:8082", alias="SPRING2_BASE_URL")
    WS_BASE_URL: str = Field("ws://localhost:8001", alias="WS_BASE_URL")

    # -------------------------------------
    # Convenience Property
    # -------------------------------------
    @property
    def debug(self) -> bool:
        """개발모드 여부"""
        return self.environment.lower() in {"development", "local"}


# -------------------------------------
# Cached global settings instance
# -------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# 전역에서 import 후 재사용
settings = get_settings()
