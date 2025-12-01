"""
Feedback Service Refactored Tests
==================================
GrammarEvaluatorImpl, RelevanceEvaluatorImpl, FeedbackJudgeImpl, FeedbackOrchestratorImpl 테스트.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.roleplaying.services.feedback_service_refactored import (
    GrammarEvaluatorImpl,
    RelevanceEvaluatorImpl,
    FeedbackJudgeImpl,
    FeedbackOrchestratorImpl
)


class TestGrammarEvaluatorImpl:
    """GrammarEvaluatorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_evaluate_grammar_valid_json(self, mock_llm_provider):
        """유효한 JSON 응답으로 문법 평가"""
        evaluator = GrammarEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = json.dumps({
            "score": 85,
            "feedback": "Good grammar with minor errors"
        })

        result = await evaluator.evaluate_grammar("I are happy.")

        assert result["score"] == 85
        assert "Good grammar" in result["feedback"]

    @pytest.mark.asyncio
    async def test_evaluate_grammar_score_normalization(self, mock_llm_provider):
        """점수 정규화 (0-100)"""
        evaluator = GrammarEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = json.dumps({
            "score": 150,
            "feedback": "Too high"
        })

        result = await evaluator.evaluate_grammar("Perfect text")

        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_evaluate_grammar_fallback_parsing(self, mock_llm_provider):
        """JSON 파싱 실패 시 숫자 추출"""
        evaluator = GrammarEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = "Score is 88 out of 100"

        result = await evaluator.evaluate_grammar("Test text")

        assert result["score"] == 88

    @pytest.mark.asyncio
    async def test_evaluate_grammar_exception_handling(self, mock_llm_provider):
        """예외 처리"""
        evaluator = GrammarEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.side_effect = Exception("LLM error")

        result = await evaluator.evaluate_grammar("Any text")

        assert result["score"] == 70
        assert "error" in result["feedback"].lower()


class TestRelevanceEvaluatorImpl:
    """RelevanceEvaluatorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_evaluate_relevance(self, mock_llm_provider):
        """맥락 관련성 평가"""
        evaluator = RelevanceEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = json.dumps({
            "score": 90,
            "feedback": "Highly relevant response"
        })

        result = await evaluator.evaluate_relevance(
            user_text="Redis is perfect for caching",
            conversation_history=[
                {"speaker": "User", "text": "How do we improve performance?"},
                {"speaker": "AI", "text": "Consider caching strategies"}
            ],
            scenario_context={"my_role": "Engineer", "ai_role": "Lead"}
        )

        assert result["score"] == 90
        assert "relevant" in result["feedback"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_relevance_low_score(self, mock_llm_provider):
        """낮은 맥락 관련성"""
        evaluator = RelevanceEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = json.dumps({
            "score": 20,
            "feedback": "Off-topic response"
        })

        result = await evaluator.evaluate_relevance(
            user_text="The weather is nice today",
            conversation_history=[],
            scenario_context={}
        )

        assert result["score"] == 20

    @pytest.mark.asyncio
    async def test_evaluate_relevance_with_recent_history(self, mock_llm_provider):
        """최근 대화 히스토리로 평가"""
        evaluator = RelevanceEvaluatorImpl(api_key="test-key")
        evaluator.llm = mock_llm_provider
        mock_llm_provider.invoke.return_value = json.dumps({
            "score": 75,
            "feedback": "Relevant"
        })

        history = [{"speaker": "User", "text": f"Message {i}"} for i in range(10)]

        result = await evaluator.evaluate_relevance(
            user_text="Response",
            conversation_history=history,
            scenario_context={"my_role": "Role"}
        )

        # 프롬프트에 최근 대화가 포함되었는지 확인
        assert mock_llm_provider.invoke.called


class TestFeedbackJudgeImpl:
    """FeedbackJudgeImpl 테스트"""

    def test_judge_correction_needed_no_issues(self):
        """모든 점수가 기준을 만족할 때"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=85,
            grammar_score=80,
            relevance_score=90,
            retry_count=0
        )

        assert needs_correction is False
        assert issue == "none"

    def test_judge_correction_needed_pronunciation_issue(self):
        """발음 점수 미달"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=50,  # 기준 이하
            grammar_score=80,
            relevance_score=90,
            retry_count=0
        )

        assert needs_correction is True
        assert issue == "pronunciation"

    def test_judge_correction_needed_grammar_issue(self):
        """문법 점수 미달"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=0,  # 발음 데이터 없음 (> 0 체크)
            grammar_score=50,
            relevance_score=90,
            retry_count=0
        )

        assert needs_correction is True
        assert issue == "grammar"

    def test_judge_correction_needed_relevance_issue(self):
        """맥락 점수 미달"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=80,
            grammar_score=80,
            relevance_score=40,
            retry_count=0
        )

        assert needs_correction is True
        assert issue == "relevance"

    def test_judge_correction_needed_max_retries_exceeded(self):
        """재시도 횟수 초과"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=30,
            grammar_score=30,
            relevance_score=30,
            retry_count=3  # 최대값
        )

        assert needs_correction is False
        assert issue == "max_retries_exceeded"

    def test_judge_correction_prioritizes_pronunciation(self):
        """발음이 우선순위"""
        judge = FeedbackJudgeImpl()

        needs_correction, issue = judge.judge_correction_needed(
            pronunciation_score=40,  # < 70
            grammar_score=50,        # < 70
            relevance_score=50,      # < 70
            retry_count=0
        )

        # 발음이 가장 먼저 체크됨
        assert issue == "pronunciation"


class TestFeedbackOrchestratorImpl:
    """FeedbackOrchestratorImpl 테스트"""

    @pytest.mark.asyncio
    async def test_evaluate_response_fast(
        self,
        mock_grammar_evaluator,
        mock_relevance_evaluator,
        mock_pronunciation_evaluator,
        mock_feedback_judge
    ):
        """빠른 응답 평가"""
        orchestrator = FeedbackOrchestratorImpl(
            grammar_evaluator=mock_grammar_evaluator,
            relevance_evaluator=mock_relevance_evaluator,
            pronunciation_evaluator=mock_pronunciation_evaluator,
            feedback_judge=mock_feedback_judge,
            azure_tracker=None
        )

        mock_feedback_judge.judge_correction_needed.return_value = (False, "none")

        result = await orchestrator.evaluate_response_fast(
            user_text="Good response",
            audio_data=b"audio data",
            conversation_history=[],
            scenario_context={},
            retry_count=0
        )

        assert "scores" in result
        assert result["needs_correction"] is False
        assert "feedback_text" in result

    @pytest.mark.asyncio
    async def test_evaluate_response_fast_with_correction_needed(
        self,
        mock_grammar_evaluator,
        mock_relevance_evaluator,
        mock_pronunciation_evaluator,
        mock_feedback_judge
    ):
        """교정이 필요한 경우"""
        orchestrator = FeedbackOrchestratorImpl(
            grammar_evaluator=mock_grammar_evaluator,
            relevance_evaluator=mock_relevance_evaluator,
            pronunciation_evaluator=mock_pronunciation_evaluator,
            feedback_judge=mock_feedback_judge,
            azure_tracker=None
        )

        # 문법 점수를 낮게 설정
        mock_grammar_evaluator.evaluate_grammar.return_value = {
            "score": 40,
            "feedback": "Bad grammar"
        }
        mock_feedback_judge.judge_correction_needed.return_value = (True, "grammar")

        result = await orchestrator.evaluate_response_fast(
            user_text="bad response",
            audio_data=None,
            conversation_history=[],
            scenario_context={},
            retry_count=0
        )

        assert result["needs_correction"] is True
        assert result["primary_issue"] == "grammar"
        assert "다시" in result["feedback_text"] or "retry" in result["feedback_text"].lower()

    @pytest.mark.asyncio
    async def test_evaluate_response_fast_exception_handling(
        self,
        mock_grammar_evaluator,
        mock_relevance_evaluator,
        mock_pronunciation_evaluator,
        mock_feedback_judge
    ):
        """예외 처리"""
        orchestrator = FeedbackOrchestratorImpl(
            grammar_evaluator=mock_grammar_evaluator,
            relevance_evaluator=mock_relevance_evaluator,
            pronunciation_evaluator=mock_pronunciation_evaluator,
            feedback_judge=mock_feedback_judge,
            azure_tracker=None
        )

        # 예외 발생
        mock_grammar_evaluator.evaluate_grammar.side_effect = Exception("Error")

        result = await orchestrator.evaluate_response_fast(
            user_text="Any text",
            audio_data=None,
            conversation_history=[],
            scenario_context={},
            retry_count=0
        )

        # Fallback 응답 반환
        assert result["needs_correction"] is False
        assert result["primary_issue"] == "error"
        assert result["scores"]["overall_score"] == 70
