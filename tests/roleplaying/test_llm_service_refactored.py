"""
LLM Service Refactored Tests
============================
ConversationAnalyzerImpl, ScenarioGeneratorImpl, QuestionGeneratorImpl, AIResponseGeneratorImpl 테스트.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.roleplaying.services.llm_service_refactored import (
    ConversationAnalyzerImpl,
    ScenarioGeneratorImpl,
    QuestionGeneratorImpl,
    AIResponseGeneratorImpl
)


class TestConversationAnalyzerImpl:
    """ConversationAnalyzerImpl 테스트"""

    @pytest.mark.asyncio
    async def test_analyze_situation(self, mock_llm_provider):
        """대화 상황 분석"""
        analyzer = ConversationAnalyzerImpl(api_key="test-key")
        analyzer.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "This is an API design discussion about performance optimization."

        messages = [
            {"senderName": "User", "text": "How do we improve API performance?"},
            {"senderName": "Tech Lead", "text": "Let's discuss caching strategies."}
        ]

        result = await analyzer.analyze_situation(
            messages=messages,
            my_role="Backend Engineer",
            conversation_date="2025-12-01"
        )

        assert "API design discussion" in result or "performance" in result.lower()
        mock_llm_provider.invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_situation_with_empty_messages(self, mock_llm_provider):
        """빈 메시지로 분석"""
        analyzer = ConversationAnalyzerImpl(api_key="test-key")
        analyzer.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Default analysis"

        result = await analyzer.analyze_situation(
            messages=[],
            my_role="Backend Engineer",
            conversation_date="2025-12-01"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_situation_handles_exception(self, mock_llm_provider):
        """예외 처리"""
        analyzer = ConversationAnalyzerImpl(api_key="test-key")
        analyzer.llm = mock_llm_provider
        mock_llm_provider.invoke.side_effect = Exception("LLM error")

        result = await analyzer.analyze_situation(
            messages=[{"senderName": "User", "text": "Hello"}],
            my_role="Engineer",
            conversation_date="2025-12-01"
        )

        assert result == "Unable to analyze conversation"


class TestScenarioGeneratorImpl:
    """ScenarioGeneratorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_generate_scenario_from_prompt(self, mock_llm_provider):
        """프롬프트 기반 시나리오 생성"""
        scenario_response = json.dumps({
            "opening_question": "How would you approach this?",
            "questions": ["Q1", "Q2", "Q3"],
            "context": "System design discussion"
        })

        generator = ScenarioGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = scenario_response

        result = await generator.generate_scenario_from_prompt(
            situation="API performance issue",
            my_role="Backend Engineer",
            ai_role="Tech Lead"
        )

        assert result["opening_question"] == "How would you approach this?"
        assert len(result["questions"]) == 3
        assert result["context"] == "System design discussion"

    @pytest.mark.asyncio
    async def test_generate_scenario_normalizes_questions(self, mock_llm_provider):
        """3개 미만의 질문을 정규화"""
        scenario_response = json.dumps({
            "opening_question": "Question?",
            "questions": ["Q1", "Q2"],
            "context": "Context"
        })

        generator = ScenarioGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = scenario_response

        result = await generator.generate_scenario_from_prompt(
            situation="Situation",
            my_role="Role",
            ai_role="AI Role"
        )

        assert len(result["questions"]) == 3

    @pytest.mark.asyncio
    async def test_generate_scenario_malformed_json_fallback(self, mock_llm_provider):
        """잘못된 JSON 응답 처리"""
        generator = ScenarioGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Invalid JSON response"

        result = await generator.generate_scenario_from_prompt(
            situation="Situation",
            my_role="Role",
            ai_role="AI Role"
        )

        assert "opening_question" in result
        assert "questions" in result
        assert len(result["questions"]) == 3

    @pytest.mark.asyncio
    async def test_generate_scenario_streaming(self, mock_llm_provider):
        """시나리오 스트리밍 생성"""
        scenario_response = json.dumps({
            "opening_question": "Question?",
            "questions": ["Q1", "Q2", "Q3"],
            "context": "Context"
        })

        generator = ScenarioGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = scenario_response

        chunks = []
        async for chunk in generator.generate_scenario_streaming(
            situation="Situation",
            my_role="Role",
            ai_role="AI Role"
        ):
            chunks.append(chunk)

        assert len(chunks) > 0


class TestQuestionGeneratorImpl:
    """QuestionGeneratorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_generate_next_question(self, mock_llm_provider):
        """다음 질문 생성"""
        generator = QuestionGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "What are the main challenges you face?"

        result = await generator.generate_next_question(
            situation="API optimization",
            conversation_history=[
                {"speaker": "User", "text": "Hello"},
                {"speaker": "AI", "text": "Hi there"}
            ]
        )

        assert "challenges" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_next_question_handles_exception(self, mock_llm_provider):
        """예외 처리"""
        generator = QuestionGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.side_effect = Exception("LLM error")

        result = await generator.generate_next_question(
            situation="Situation",
            conversation_history=[]
        )

        assert result == "Could you tell me more about that?"

    @pytest.mark.asyncio
    async def test_generate_followup_question(self, mock_llm_provider):
        """Follow-up 질문 생성"""
        generator = QuestionGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Can you elaborate on that?"

        result = await generator.generate_followup_question(
            prompt="Tell me more about your concerns"
        )

        assert "elaborate" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_followup_question_stream(self, mock_llm_provider):
        """Follow-up 질문 스트리밍"""
        generator = QuestionGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Tell me more"

        chunks = []
        async for chunk in generator.generate_followup_question_stream("Prompt"):
            chunks.append(chunk)

        assert len(chunks) > 0


class TestAIResponseGeneratorImpl:
    """AIResponseGeneratorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_generate_ai_response(self, mock_llm_provider):
        """AI 응답 생성"""
        generator = AIResponseGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "I'd suggest implementing caching strategies..."

        result = await generator.generate_ai_response(
            situation="API performance",
            my_role="Backend Engineer",
            ai_role="Tech Lead",
            conversation_history=[
                {"speaker": "User", "text": "How do we improve performance?"}
            ]
        )

        assert "caching" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_ai_response_handles_exception(self, mock_llm_provider):
        """예외 처리"""
        generator = AIResponseGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.side_effect = Exception("LLM error")

        result = await generator.generate_ai_response(
            situation="Situation",
            my_role="Role",
            ai_role="AI Role",
            conversation_history=[]
        )

        assert "clarify" in result.lower() or "appreciate" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_ai_response_streaming(self, mock_llm_provider):
        """AI 응답 스트리밍"""
        generator = AIResponseGeneratorImpl(api_key="test-key")
        generator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Here is my response"

        chunks = []
        async for chunk in generator.generate_ai_response_streaming(
            situation="Situation",
            my_role="Role",
            ai_role="AI Role",
            conversation_history=[]
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
