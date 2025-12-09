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

from pydantic import Field, field_validator, model_validator
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

    # 용도별 모델 설정
    OPENAI_MODEL_FEEDBACK: str = Field("gpt-4.1", alias="OPENAI_MODEL_FEEDBACK")
    OPENAI_MODEL_QUESTION_GENERATION: str = Field("gpt-4.1-mini", alias="OPENAI_MODEL_QUESTION_GENERATION")
    OPENAI_MODEL_AI_RESPONSE: str = Field("gpt-4.1-mini", alias="OPENAI_MODEL_AI_RESPONSE")

    deepgram_api_key: Optional[str] = Field(default=None, alias="DEEPGRAM_API_KEY")

    # ========================================
    # Azure Speech (발음 평가)
    # ========================================
    AZURE_SPEECH_KEY: Optional[str] = Field(default=None, alias="AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION: str = Field("eastus", alias="AZURE_SPEECH_REGION")
    AZURE_SPEECH_ENABLED: bool = Field(False, alias="AZURE_SPEECH_ENABLED")
    AZURE_SPEECH_FREE_TIER_ONLY: bool = Field(True, alias="AZURE_SPEECH_FREE_TIER_ONLY")
    AZURE_SPEECH_DAILY_LIMIT: int = Field(600, alias="AZURE_SPEECH_DAILY_LIMIT")

    # ========================================
    # Ollama Settings
    # ========================================
    OLLAMA_MODEL: str = Field("llama3.2", alias="OLLAMA_MODEL")
    OLLAMA_BASE_URL: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")

    # ========================================
    # LLM Provider Selection
    # ========================================
    FEEDBACK_LLM_PROVIDER: str = Field("openai", alias="FEEDBACK_LLM_PROVIDER")

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
    SPRING2_BASE_URL: str = Field("http://localhost:8081", alias="SPRING2_BASE_URL")
    WS_BASE_URL: str = Field("ws://localhost:8001", alias="WS_BASE_URL")

    # -------------------------------------
    # Roleplay Session Settings
    # -------------------------------------
    ROLEPLAY_MAX_TURNS: int = Field(7, alias="ROLEPLAY_MAX_TURNS")
    ROLEPLAY_REDIS_CACHE_TTL: int = Field(7200, alias="ROLEPLAY_REDIS_CACHE_TTL")  # 2시간
    ROLEPLAY_SESSION_TIMEOUT: int = Field(3600, alias="ROLEPLAY_SESSION_TIMEOUT")  # 1시간
    ROLEPLAY_STT_TIMEOUT: int = Field(20, alias="ROLEPLAY_STT_TIMEOUT")
    ROLEPLAY_AI_RESPONSE_TIMEOUT: int = Field(30, alias="ROLEPLAY_AI_RESPONSE_TIMEOUT")
    ROLEPLAY_AUTO_CLEANUP_INTERVAL: int = Field(3600, alias="ROLEPLAY_AUTO_CLEANUP_INTERVAL")  # 1시간

    # -------------------------------------
    # Deepgram STT Settings
    # -------------------------------------
    DEEPGRAM_MODEL: str = Field("nova-2", alias="DEEPGRAM_MODEL")
    DEEPGRAM_LANGUAGE: str = Field("en", alias="DEEPGRAM_LANGUAGE")
    DEEPGRAM_ENCODING: str = Field("linear16", alias="DEEPGRAM_ENCODING")
    DEEPGRAM_SAMPLE_RATE: int = Field(16000, alias="DEEPGRAM_SAMPLE_RATE")
    DEEPGRAM_SMART_FORMAT: bool = Field(True, alias="DEEPGRAM_SMART_FORMAT")
    DEEPGRAM_INTERIM_RESULTS: bool = Field(True, alias="DEEPGRAM_INTERIM_RESULTS")
    DEEPGRAM_CHANNELS: int = Field(1, alias="DEEPGRAM_CHANNELS")

    # -------------------------------------
    # Audio Processing Settings
    # -------------------------------------
    AUDIO_CHUNK_SIZE_MS: int = Field(100, alias="AUDIO_CHUNK_SIZE_MS")  # 100ms chunks
    AUDIO_AGC_ENABLED: bool = Field(True, alias="AUDIO_AGC_ENABLED")
    AUDIO_AGC_TARGET_LEVEL: float = Field(0.8, alias="AUDIO_AGC_TARGET_LEVEL")
    AUDIO_MIN_TEXT_LENGTH: int = Field(2, alias="AUDIO_MIN_TEXT_LENGTH")  # 침묵 감지 기준

    # ========================================
    # Feedback & Evaluation Settings
    # ========================================
    FEEDBACK_PRONUNCIATION_THRESHOLD: int = Field(70, alias="FEEDBACK_PRONUNCIATION_THRESHOLD")
    FEEDBACK_GRAMMAR_THRESHOLD: int = Field(70, alias="FEEDBACK_GRAMMAR_THRESHOLD")
    FEEDBACK_RELEVANCE_THRESHOLD: int = Field(70, alias="FEEDBACK_RELEVANCE_THRESHOLD")
    FEEDBACK_MAX_RETRY_PER_QUESTION: int = Field(3, alias="FEEDBACK_MAX_RETRY_PER_QUESTION")
    FEEDBACK_ASYNC_TEXT_GENERATION: bool = Field(True, alias="FEEDBACK_ASYNC_TEXT_GENERATION")

    # ========================================
    # ✅ Field Validators
    # ========================================

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """
        환경값 검증 (development, staging, production만 허용)
        """
        valid_environments = {"development", "staging", "production", "local"}
        if v.lower() not in valid_environments:
            raise ValueError(
                f"Invalid environment: {v}. Must be one of {valid_environments}"
            )
        return v.lower()

    @field_validator("DEEPGRAM_SAMPLE_RATE")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """
        샘플레이트 검증 (8000, 16000, 48000만 허용)
        """
        valid_rates = {8000, 16000, 48000}
        if v not in valid_rates:
            raise ValueError(
                f"Invalid sample rate: {v}. Must be one of {valid_rates}"
            )
        return v

    @field_validator("AUDIO_CHUNK_SIZE_MS")
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        """
        청크 크기 검증 (10-500ms)
        """
        if not 10 <= v <= 500:
            raise ValueError(
                f"Invalid chunk size: {v}ms. Must be between 10-500ms"
            )
        return v

    @field_validator("AUDIO_AGC_TARGET_LEVEL")
    @classmethod
    def validate_agc_level(cls, v: float) -> float:
        """
        AGC 타겟 레벨 검증 (0.0-1.0)
        """
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"Invalid AGC target level: {v}. Must be between 0.0-1.0"
            )
        return v

    @field_validator("ROLEPLAY_MAX_TURNS")
    @classmethod
    def validate_max_turns(cls, v: int) -> int:
        """
        최대 턴 수 검증 (1-50)
        """
        if not 1 <= v <= 50:
            raise ValueError(
                f"Invalid max turns: {v}. Must be between 1-50"
            )
        return v

    @field_validator(
        "ROLEPLAY_REDIS_CACHE_TTL",
        "ROLEPLAY_SESSION_TIMEOUT",
        "ROLEPLAY_STT_TIMEOUT",
        "ROLEPLAY_AI_RESPONSE_TIMEOUT",
        "ROLEPLAY_AUTO_CLEANUP_INTERVAL"
    )
    @classmethod
    def validate_timeouts(cls, v: int) -> int:
        """
        타임아웃/TTL 값 검증 (1초 이상)
        """
        if v < 1:
            raise ValueError(
                f"Invalid timeout value: {v}. Must be at least 1 second"
            )
        return v

    @model_validator(mode="after")
    def validate_model_urls(self) -> "Settings":
        """
        URL 및 데이터베이스 URL 형식 검증 (엄격한 스킴 검증)

        ✅ 각 URL 필드에 맞는 스킴만 허용하여 설정 오류 조기 방지:
        - S3_ENDPOINT_URL: http://, https://만 허용
        - SPRING2_BASE_URL: http://, https://만 허용
        - WS_BASE_URL: ws://, wss://만 허용
        - REDIS_URL: redis://, rediss://만 허용
        - DATABASE_URL: mysql://, mysql+pymysql://만 허용
        """
        # ✅ 각 URL에 맞는 스킴 정의 (허용된 스킴만 명시)
        url_validations = {
            "S3_ENDPOINT_URL": (self.S3_ENDPOINT_URL, ("http://", "https://")),
            "SPRING2_BASE_URL": (self.SPRING2_BASE_URL, ("http://", "https://")),
            "WS_BASE_URL": (self.WS_BASE_URL, ("ws://", "wss://")),
            "REDIS_URL": (self.REDIS_URL, ("redis://", "rediss://")),
        }

        for field_name, (url, schemes) in url_validations.items():
            if not url.startswith(schemes):
                raise ValueError(
                    f"Invalid URL format for {field_name}: {url}. "
                    f"Must start with {schemes}"
                )

        # ✅ 데이터베이스 URL 검증
        valid_db_schemes = ("mysql://", "mysql+pymysql://")
        if not self.database_url.startswith(valid_db_schemes):
            raise ValueError(
                f"Invalid database URL: {self.database_url}. "
                f"Must start with {valid_db_schemes}"
            )

        return self

    # ========================================
    # Convenience Property
    # ========================================
    @property
    def debug(self) -> bool:
        """개발모드 여부"""
        return self.environment.lower() in {"development", "local"}

    @property
    def audio_chunk_bytes(self) -> int:
        """청크 크기 (바이트)"""
        # 16kHz, PCM 16-bit mono: sample_rate/1000 * chunk_size_ms * 2 (bytes per sample)
        return self.DEEPGRAM_SAMPLE_RATE // 1000 * self.AUDIO_CHUNK_SIZE_MS * 2


# -------------------------------------
# Cached global settings instance
# -------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# 전역에서 import 후 재사용
settings = get_settings()
