"""
Prompt Registry
==============
프롬프트를 동적으로 로드하고 관리합니다.

사용 예:
    from app.roleplaying.prompts.registry import get_prompt

    prompt = get_prompt("followup_question", role="Interviewer")
"""

from typing import Dict, Any
from app.roleplaying.prompts.constants import (
    FOLLOWUP_QUESTION_PROMPT,
    FIXED_QUESTIONS_PROMPT,
    GRAMMAR_EVALUATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    CONVERSATION_ANALYSIS_PROMPT,
    SCENARIO_GENERATION_PROMPT,
    SITUATION_ENHANCEMENT_PROMPT,
    AI_RESPONSE_PROMPT,
    MESSAGE_SUMMARY_PROMPT,
    TITLE_GENERATION_PROMPT,
)


# 프롬프트 레지스트리
_PROMPT_REGISTRY: Dict[str, str] = {
    "followup_question": FOLLOWUP_QUESTION_PROMPT,
    "fixed_questions": FIXED_QUESTIONS_PROMPT,
    "grammar_evaluation": GRAMMAR_EVALUATION_PROMPT,
    "relevance_evaluation": RELEVANCE_EVALUATION_PROMPT,
    "conversation_analysis": CONVERSATION_ANALYSIS_PROMPT,
    "scenario_generation": SCENARIO_GENERATION_PROMPT,
    "situation_enhancement": SITUATION_ENHANCEMENT_PROMPT,
    "ai_response": AI_RESPONSE_PROMPT,
    "message_summary": MESSAGE_SUMMARY_PROMPT,
    "title_generation": TITLE_GENERATION_PROMPT,
}


def get_prompt(prompt_id: str, **kwargs) -> str:
    """
    프롬프트를 가져오고 변수를 포맷합니다.

    Args:
        prompt_id: 프롬프트 식별자
        **kwargs: 프롬프트 템플릿의 변수들

    Returns:
        포맷된 프롬프트 문자열

    Raises:
        KeyError: 존재하지 않는 프롬프트 ID
    """
    if prompt_id not in _PROMPT_REGISTRY:
        available = ", ".join(_PROMPT_REGISTRY.keys())
        raise KeyError(
            f"Unknown prompt ID: {prompt_id}. Available prompts: {available}"
        )

    template = _PROMPT_REGISTRY[prompt_id]

    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(
            f"Missing variable in prompt '{prompt_id}': {e}"
        )


def get_all_prompts() -> Dict[str, str]:
    """모든 프롬프트 반환"""
    return _PROMPT_REGISTRY.copy()


def register_prompt(prompt_id: str, template: str) -> None:
    """
    새로운 프롬프트 등록 (동적 추가용)

    Args:
        prompt_id: 프롬프트 식별자
        template: 프롬프트 템플릿 문자열
    """
    _PROMPT_REGISTRY[prompt_id] = template