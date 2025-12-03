"""
ReAct Agent Tools for Feedback Decision

Tool 정의 및 래핑
================================================

Tools:
1. evaluate_response: 사용자 발화 평가 (FeedbackOrchestrator 활용)
2. analyze_retry_context: 재시도 상황 분석
3. (Optional) generate_feedback: 피드백 생성
4. (Optional) generate_next_question: 다음 질문 생성

각 Tool은 단일 책임 원칙 준수 (SOLID SRP)
"""

import logging
from typing import Dict, Any, Optional
import json

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================
# Tool Functions (LangChain @tool compatible)
# ============================================


async def evaluate_response_tool(
    feedback_orchestrator,
    user_text: str,
    audio_data: Optional[bytes],
    conversation_history: list,
    scenario_context: dict,
    retry_count: int,
) -> Dict[str, Any]:
    """
    Tool 1: 사용자 발화 평가

    FeedbackOrchestrator를 활용하여 평가 점수 산출

    Args:
        feedback_orchestrator: FeedbackOrchestrator 인스턴스
        user_text: 사용자 발화 텍스트
        audio_data: 사용자 오디오 데이터 (선택사항)
        conversation_history: 대화 히스토리
        scenario_context: 시나리오 컨텍스트
        retry_count: 현재 재시도 횟수

    Returns:
        {
            "pronunciation_score": int | None,
            "grammar_score": int | None,
            "relevance_score": int | None,
            "overall_score": int | None,
            "feedback_text": str,
            "needs_correction": bool,
            "primary_issue": str
        }
    """
    try:
        logger.info(f"🔧 [Tool] evaluate_response_tool called")

        # FeedbackOrchestrator의 기존 메서드 활용
        result = await feedback_orchestrator.evaluate_response_fast(
            user_text=user_text,
            audio_data=audio_data,
            conversation_history=conversation_history,
            scenario_context=scenario_context,
            retry_count=retry_count,
        )

        if result is None:
            logger.warning("⚠️ [Tool] evaluate_response_tool: evaluation failed, returning None")
            return {
                "pronunciation_score": None,
                "grammar_score": None,
                "relevance_score": None,
                "overall_score": None,
                "feedback_text": "",
                "needs_correction": False,
                "primary_issue": "evaluation_failed",
            }

        # 평가 결과 추출
        scores = result.get("scores", {})
        return {
            "pronunciation_score": scores.get("pronunciation_score"),
            "grammar_score": scores.get("grammar_score"),
            "relevance_score": scores.get("relevance_score"),
            "overall_score": scores.get("overall_score"),
            "feedback_text": result.get("feedback_text", ""),
            "needs_correction": result.get("needs_correction", False),
            "primary_issue": result.get("primary_issue", "none"),
            "feedback_sections": result.get("feedback_sections", []),
            "retry_count": result.get("retry_count", retry_count),
        }

    except Exception as e:
        logger.error(f"❌ [Tool] evaluate_response_tool failed: {e}", exc_info=True)
        return {
            "pronunciation_score": None,
            "grammar_score": None,
            "relevance_score": None,
            "overall_score": None,
            "feedback_text": "",
            "needs_correction": False,
            "primary_issue": "tool_error",
            "feedback_sections": [],
            "retry_count": retry_count,
        }


async def analyze_retry_context_tool(
    session_state: Any,
    retry_count: int,
    can_use_azure: bool,
) -> Dict[str, Any]:
    """
    Tool 2: 재시도 상황 분석

    재시도 횟수, 대화 진행도, 학습자 노력 등을 종합 분석

    Args:
        session_state: 세션 상태
        retry_count: 현재 재시도 횟수
        can_use_azure: Azure 발음 평가 사용 가능 여부

    Returns:
        {
            "retry_count": int,
            "max_retries": int,
            "is_max_retries_exceeded": bool,
            "conversation_turn": int,
            "estimated_learning_progress": str,
            "azure_available": bool,
            "recommendation": str
        }
    """
    try:
        logger.info(f"🔧 [Tool] analyze_retry_context_tool called")

        max_retries = settings.FEEDBACK_MAX_RETRY_PER_QUESTION

        return {
            "retry_count": retry_count,
            "max_retries": max_retries,
            "is_max_retries_exceeded": retry_count >= max_retries,
            "conversation_turn": len(session_state.history) // 2 if session_state and session_state.history else 0,
            "estimated_learning_progress": "early" if retry_count == 0 else "in_progress" if retry_count < max_retries else "completed",
            "azure_available": can_use_azure,
            "recommendation": (
                "User needs encouragement - multiple retries already attempted"
                if retry_count >= max_retries
                else "Normal feedback flow"
            ),
        }

    except Exception as e:
        logger.error(f"❌ [Tool] analyze_retry_context_tool failed: {e}", exc_info=True)
        return {
            "retry_count": retry_count,
            "max_retries": settings.FEEDBACK_MAX_RETRY_PER_QUESTION,
            "is_max_retries_exceeded": retry_count >= settings.FEEDBACK_MAX_RETRY_PER_QUESTION,
            "conversation_turn": 0,
            "estimated_learning_progress": "unknown",
            "azure_available": can_use_azure,
            "recommendation": "Use caution due to tool error",
        }


# ============================================
# Tool Registry (확장성을 위한 Registry 패턴)
# ============================================


class AgentToolRegistry:
    """
    ReAct Agent Tools Registry (SOLID OCP 준수)

    새로운 Tool 추가 시:
    1. Tool 함수 정의
    2. registry에 등록만 하면 됨
    """

    _tools = {}

    @classmethod
    def register(cls, name: str, tool_func):
        """Tool 등록"""
        cls._tools[name] = tool_func
        logger.info(f"✅ Tool registered: {name}")

    @classmethod
    def get_tool(cls, name: str):
        """Tool 조회"""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls):
        """모든 Tool 반환"""
        return cls._tools

    @classmethod
    def get_tool_descriptions(cls) -> Dict[str, str]:
        """LangChain Agent용 Tool 설명 반환"""
        return {
            "evaluate_response": "Evaluate user's response on pronunciation, grammar, and relevance. Returns evaluation scores and feedback.",
            "analyze_retry_context": "Analyze retry context including retry count, conversation progress, and learning status.",
        }


# Tool 등록
AgentToolRegistry.register("evaluate_response", evaluate_response_tool)
AgentToolRegistry.register("analyze_retry_context", analyze_retry_context_tool)
