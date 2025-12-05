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

from app.config import settings
from app.roleplaying.services.llm.llm_provider_factory import create_llm_provider

logger = logging.getLogger(__name__)


class LLMServiceBase(ABC):
    """
    LLM 서비스 기본 클래스

    모든 LLM 서비스가 상속하여 사용하는 기본 클래스입니다.
    공통적인 LLM 초기화 로직을 제공합니다.

    의존성:
        - app.config (OpenAI API 키, 모델명)
        - app.roleplaying.services.llm.llm_provider_factory (LLM 프로바이더)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7,
    ):
        """
        LLM 서비스 초기화

        Args:
            api_key: OpenAI API 키 (None이면 settings에서 로드)
            model_name: 모델명 (None이면 settings에서 로드)
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        # API 키 및 모델명 설정
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL
        self.temperature = temperature

        # LLM 클라이언트 생성 (OpenAI만 지원)
        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature,
        )

        # 초기화 로그
        logger.info(
            f"{self.__class__.__name__} initialized: "
            f"provider=openai, model={self.model_name}, "
            f"temperature={self.temperature}"
        )
