"""
==============================================================
Config Module
==============================================================
Application-wide configuration helpers built on Pydantic Settings.

역할:
    - 환경변수(.env) 기반 설정값을 중앙에서 관리
    - DATABASE_URL, OPENAI_API_KEY, ENVIRONMENT 등 환경별 주요 설정 로드
    - Settings 인스턴스를 전역에서 재사용하도록 캐싱 처리

사용예시:
    from app.config import settings

    print(settings.database_url)
    if settings.debug:
        print("Running in development mode")
--------------------------------------------------------------
Author: 정도현
Created: 2025-11-12
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
        - 환경별 설정(개발, 운영, 로컬 등)을 구분 관리
        - FastAPI, SQLAlchemy, 외부 API 클라이언트 등에서 공통 사용

    주요 필드:
        database_url (str): 데이터베이스 연결 URL
        environment (str): 실행 환경 ("development", "production", "local" 등)
        openai_api_key (Optional[str]): OpenAI API 키 (없으면 None)
        필드는 지속적으로 추가 예정

    참고:
        - Pydantic SettingsConfigDict를 통해 env_file, 인코딩, extra 옵션 지정
    """

    # 환경변수 로드 설정
    model_config = SettingsConfigDict(
        env_file=".env",               # 환경변수 파일 경로
        env_file_encoding="utf-8",     # 인코딩
        extra="ignore"                 # 정의되지 않은 변수 무시
    )

    # 환경변수 매핑
    database_url: str = Field(..., alias="DATABASE_URL")
    environment: str = Field("development", alias="ENVIRONMENT")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    @property
    def debug(self) -> bool:
        """
        개발모드 여부를 반환하는 속성.

        Returns:
            bool: ENVIRONMENT가 "development" 또는 "local"이면 True
        """
        return self.environment.lower() in {"development", "local"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    설명:
        - Settings 객체를 프로세스당 한 번만 생성
        - 매번 새로 환경변수를 읽는 오버헤드 방지
    """
    return Settings()


# 전역에서 import하여 사용할 설정 인스턴스
settings = get_settings()