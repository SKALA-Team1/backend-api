"""
LLM Service Base Class
====================
모든 LLM 서비스의 공통 초기화 로직을 담당합니다.

사용 예:
    class MyLLMService(LLMServiceBase):
        async def some_method(self):
            response = await self.llm.invoke(prompt)
"""

import logging
from abc import ABC

from app.core.settings import settings
from app.roleplaying.services.llm_providers import create_llm_provider

logger = logging.getLogger(__name__)


class LLMServiceBase(ABC):
    """
    LLM 서비스 기본 클래스

    모든 LLM 서비스가 상속하여 사용하는 기본 클래스입니다.
    공통적인 LLM 초기화 로직을 제공합니다.

    의존성:
        - app.core.settings (OpenAI API 키, 모델명)
        - app.roleplaying.services.llm_providers (LLM 프로바이더)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7,
        base_url: str = None,
    ):
        """
        LLM 서비스 초기화

        Args:
            api_key: OpenAI API 키 (None이면 settings에서 로드)
            model_name: 모델명 (None이면 settings에서 로드)
            temperature: 창의성 레벨 (기본값: 0.7)
            base_url: Ollama 등 로컬 LLM의 베이스 URL
        """
        # API 키 및 모델명 설정
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL
        self.temperature = temperature
        self.base_url = base_url or settings.OLLAMA_BASE_URL

        # LLM 프로바이더 결정
        # OpenAI API 키가 있으면 OpenAI 사용, 없으면 Ollama 사용
        provider_type = "openai" if self.api_key else "ollama"

        # LLM 클라이언트 생성
        self.llm = create_llm_provider(
            provider_type=provider_type,
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
        )

        # 초기화 로그
        logger.info(
            f"{self.__class__.__name__} initialized: "
            f"provider={provider_type}, model={self.model_name}, "
            f"temperature={self.temperature}"
        )
