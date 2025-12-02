"""
LLM Providers Tests
===================
OpenAIProvider, OllamaProvider, create_llm_provider 테스트.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.roleplaying.services.llm.llm_provider_factory import (
    OpenAIProvider,
    OllamaProvider,
    create_llm_provider,
)


class TestOpenAIProvider:
    """OpenAI 프로바이더 테스트"""

    def test_openai_provider_initialization(self):
        """OpenAI 프로바이더 초기화"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.ChatOpenAI') as mock_chat:
            provider = OpenAIProvider(
                api_key="test-key",
                model_name="gpt-4",
                temperature=0.7
            )

            assert provider.model_name == "gpt-4"
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_provider_invoke(self):
        """OpenAI 프로바이더 invoke 메서드"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.ChatOpenAI') as mock_chat:
            mock_llm = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_chat.return_value = mock_llm

            provider = OpenAIProvider(
                api_key="test-key",
                model_name="gpt-4"
            )
            provider.llm = mock_llm

            # run_in_executor 모킹
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.run_in_executor = AsyncMock(return_value=mock_response)
                mock_loop.return_value = mock_executor

                result = await provider.invoke("Test prompt")

                assert result == "Test response"

    @pytest.mark.asyncio
    async def test_openai_provider_invoke_without_content_attribute(self):
        """OpenAI 응답이 content 속성이 없을 때"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.ChatOpenAI') as mock_chat:
            mock_llm = MagicMock()
            mock_response = "Direct string response"
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_chat.return_value = mock_llm

            provider = OpenAIProvider(
                api_key="test-key",
                model_name="gpt-4"
            )
            provider.llm = mock_llm

            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.run_in_executor = AsyncMock(return_value=mock_response)
                mock_loop.return_value = mock_executor

                result = await provider.invoke("Test prompt")

                assert result == "Direct string response"


class TestOllamaProvider:
    """Ollama 프로바이더 테스트"""

    def test_ollama_provider_initialization(self):
        """Ollama 프로바이더 초기화"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.OllamaLLM') as mock_ollama:
            provider = OllamaProvider(
                model_name="llama2",
                base_url="http://localhost:11434",
                temperature=0.5
            )

            assert provider.model_name == "llama2"
            mock_ollama.assert_called_once()

    @pytest.mark.asyncio
    async def test_ollama_provider_invoke(self):
        """Ollama 프로바이더 invoke 메서드"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.OllamaLLM') as mock_ollama:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Ollama response"
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_ollama.return_value = mock_llm

            provider = OllamaProvider(
                model_name="llama2",
                base_url="http://localhost:11434"
            )
            provider.llm = mock_llm

            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.run_in_executor = AsyncMock(return_value=mock_response)
                mock_loop.return_value = mock_executor

                result = await provider.invoke("Test prompt")

                assert result == "Ollama response"


class TestCreateLLMProvider:
    """create_llm_provider 팩토리 함수 테스트"""

    def test_create_openai_provider(self, mock_settings):
        """OpenAI 프로바이더 생성"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.ChatOpenAI'):
            provider = create_llm_provider(
                provider_type="openai",
                api_key="test-key",
                model_name="gpt-4",
                temperature=0.7
            )

            assert isinstance(provider, OpenAIProvider)
            assert provider.model_name == "gpt-4"

    def test_create_ollama_provider(self):
        """Ollama 프로바이더 생성"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.OllamaLLM'):
            provider = create_llm_provider(
                provider_type="ollama",
                model_name="llama2",
                base_url="http://localhost:11434",
                temperature=0.5
            )

            assert isinstance(provider, OllamaProvider)
            assert provider.model_name == "llama2"

    def test_create_openai_provider_missing_api_key(self):
        """OpenAI 프로바이더 생성시 API 키 누락"""
        with pytest.raises(ValueError) as exc_info:
            create_llm_provider(
                provider_type="openai",
                model_name="gpt-4"
            )
        assert "api_key" in str(exc_info.value)

    def test_create_openai_provider_missing_model_name(self):
        """OpenAI 프로바이더 생성시 모델명 누락"""
        with pytest.raises(ValueError) as exc_info:
            create_llm_provider(
                provider_type="openai",
                api_key="test-key"
            )
        assert "model_name" in str(exc_info.value)

    def test_create_ollama_provider_missing_model_name(self):
        """Ollama 프로바이더 생성시 모델명 누락"""
        with pytest.raises(ValueError) as exc_info:
            create_llm_provider(
                provider_type="ollama",
                base_url="http://localhost:11434"
            )
        assert "model_name" in str(exc_info.value)

    def test_create_ollama_provider_missing_base_url(self):
        """Ollama 프로바이더 생성시 base_url 누락"""
        with pytest.raises(ValueError) as exc_info:
            create_llm_provider(
                provider_type="ollama",
                model_name="llama2"
            )
        assert "base_url" in str(exc_info.value)

    def test_create_unsupported_provider(self):
        """지원하지 않는 프로바이더"""
        with pytest.raises(ValueError) as exc_info:
            create_llm_provider(
                provider_type="unsupported",
                api_key="test-key",
                model_name="test"
            )
        assert "Unsupported" in str(exc_info.value)

    def test_create_provider_with_default_temperature(self):
        """기본 temperature 사용"""
        with patch('app.roleplaying.services.llm.llm_provider_factory.ChatOpenAI'):
            provider = create_llm_provider(
                provider_type="openai",
                api_key="test-key",
                model_name="gpt-4"
            )

            assert provider.temperature == 0.7
