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

import logging
from typing import Protocol

from langchain_openai import ChatOpenAI

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

    async def stream(self, prompt: str):
        """
        프롬프트를 LLM에 전달하고 토큰을 스트리밍으로 반환합니다.

        Args:
            prompt: 입력 프롬프트

        Yields:
            각 토큰 문자열
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
        """
        response = await self.llm.ainvoke(prompt)

        # LangChain 응답 객체에서 텍스트 추출
        if hasattr(response, 'content'):
            return response.content
        return str(response)

    async def stream(self, prompt: str):
        """
        OpenAI API를 호출하여 토큰을 스트리밍으로 생성합니다.

        ✅ astream() 사용:
        - 비동기 제너레이터로 진정한 스트리밍
        - 전체 응답 로드 대기 없음
        - 이벤트 루프 블로킹 없음
        - 메모리 효율적

        Args:
            prompt: 입력 프롬프트

        Yields:
            각 토큰 문자열
        """
        # ✅ ChatOpenAI.astream() - 진정한 비동기 스트리밍
        async for chunk in self.llm.astream(prompt):
            if hasattr(chunk, 'content'):
                yield chunk.content
            else:
                yield str(chunk)


def create_llm_provider(
    provider_type: str,
    api_key: str = None,
    model_name: str = None,
    temperature: float = 0.7
) -> LLMProvider:
    """
    LLM 프로바이더 팩토리 함수

    OCP를 준수하는 팩토리 패턴입니다.
    새로운 프로바이더 추가 시 이 함수만 수정하면 됩니다.

    Args:
        provider_type: 프로바이더 타입 ("openai")
        api_key: OpenAI API 키 (필수)
        model_name: 모델명 (필수)
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

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider_type}. "
            f"Supported: 'openai'"
        )


# Provider 레지스트리 (향후 확장용)
# 새로운 프로바이더를 추가할 때 여기에 등록하면 됨
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
}
