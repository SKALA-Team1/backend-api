"""
LLM Provider Implementations
=============================
다양한 LLM 프로바이더를 추상화하여 OCP(Open-Closed Principle)를 준수합니다.

설계:
- LLMProvider Protocol로 인터페이스 정의
- 각 프로바이더는 Protocol 구현
- Factory 함수로 프로바이더 생성
- 새로운 프로바이더 추가 시 create_llm_provider() 함수만 수정

OCP 준수:
- 기존 클래스 수정 없음 (Closed for modification)
- 새로운 프로바이더 추가 가능 (Open for extension)
"""

import asyncio
import logging
from typing import Any, Protocol

from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """LLM 프로바이더 인터페이스

    모든 LLM 프로바이더가 구현해야 하는 기본 메서드를 정의합니다.
    """

    async def invoke(self, prompt: str) -> str:
        """
        프롬프트를 LLM에 전달하고 결과를 반환합니다.

        Args:
            prompt: 입력 프롬프트

        Returns:
            LLM의 응답
        """
        ...


class OpenAIProvider:
    """OpenAI GPT 프로바이더

    OpenAI의 GPT 모델을 사용합니다.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        temperature: float = 0.7
    ):
        """
        OpenAI 프로바이더 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델명 (예: "gpt-4.1", "gpt-4.1-mini")
            temperature: 창의성 레벨 (0.0-2.0)
        """
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=temperature
        )
        self.model_name = model_name
        logger.info(f"✅ OpenAIProvider initialized: model={model_name}")

    async def invoke(self, prompt: str) -> str:
        """
        OpenAI API를 호출하여 응답을 생성합니다.

        동기 API를 비동기로 래핑하여 이벤트 루프를 블로킹하지 않습니다.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.llm.invoke, prompt)

        # LangChain 응답 객체에서 텍스트 추출
        if hasattr(response, 'content'):
            return response.content
        return str(response)


class OllamaProvider:
    """Ollama 로컬 LLM 프로바이더

    로컬에서 실행되는 오픈소스 LLM을 사용합니다.
    """

    def __init__(
        self,
        model_name: str,
        base_url: str,
        temperature: float = 0.7
    ):
        """
        Ollama 프로바이더 초기화

        Args:
            model_name: 모델명 (예: "llama2", "mistral", "neural-chat")
            base_url: Ollama 서버 URL (예: "http://localhost:11434")
            temperature: 창의성 레벨
        """
        self.llm = OllamaLLM(
            model=model_name,
            base_url=base_url,
            temperature=temperature
        )
        self.model_name = model_name
        logger.info(f"✅ OllamaProvider initialized: model={model_name}, url={base_url}")

    async def invoke(self, prompt: str) -> str:
        """
        Ollama API를 호출하여 응답을 생성합니다.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.llm.invoke, prompt)

        if hasattr(response, 'content'):
            return response.content
        return str(response)


def create_llm_provider(
    provider_type: str,
    api_key: str = None,
    model_name: str = None,
    base_url: str = None,
    temperature: float = 0.7
) -> LLMProvider:
    """
    LLM 프로바이더 팩토리 함수

    OCP를 준수하는 팩토리 패턴입니다.
    새로운 프로바이더 추가 시 이 함수만 수정하면 됩니다.

    Args:
        provider_type: 프로바이더 타입 ("openai" 또는 "ollama")
        api_key: OpenAI API 키 (OpenAI 사용 시 필수)
        model_name: 모델명
        base_url: Ollama 서버 URL (Ollama 사용 시 필수)
        temperature: 창의성 레벨

    Returns:
        LLMProvider 인스턴스

    Raises:
        ValueError: 지원하지 않는 프로바이더 타입 또는 필수 파라미터 누락

    Example:
        # OpenAI 프로바이더 생성
        provider = create_llm_provider(
            provider_type="openai",
            api_key="sk-...",
            model_name="gpt-4.1",
            temperature=0.3
        )

        # Ollama 프로바이더 생성
        provider = create_llm_provider(
            provider_type="ollama",
            model_name="mistral",
            base_url="http://localhost:11434"
        )
    """
    if provider_type == "openai":
        if not api_key:
            raise ValueError("OpenAI requires 'api_key' parameter")
        if not model_name:
            raise ValueError("OpenAI requires 'model_name' parameter")

        logger.info(f"Creating OpenAI provider: {model_name}")
        return OpenAIProvider(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )

    elif provider_type == "ollama":
        if not model_name:
            raise ValueError("Ollama requires 'model_name' parameter")
        if not base_url:
            raise ValueError("Ollama requires 'base_url' parameter")

        logger.info(f"Creating Ollama provider: {model_name} at {base_url}")
        return OllamaProvider(
            model_name=model_name,
            base_url=base_url,
            temperature=temperature
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_type}. "
            f"Supported: 'openai', 'ollama'"
        )


# Provider 레지스트리 (향후 확장용)
# 새로운 프로바이더를 추가할 때 여기에 등록하면 됨
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}
