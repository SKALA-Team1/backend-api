"""
LLM Service Utilities
====================
LLM 서비스에서 자주 사용되는 유틸리티 함수들을 모아놨습니다.

포함:
- JSON 추출
- 대화 히스토리 포맷팅
- 질문 정규화
- 점수 정규화
"""

import json
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


# ============================================
# JSON 추출 및 파싱
# ============================================

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    LLM 응답에서 JSON 객체를 추출합니다.

    Args:
        response: LLM 응답 문자열

    Returns:
        추출된 JSON 딕셔너리, 또는 None
    """
    if not response:
        return None

    try:
        # JSON 객체 패턴 찾기
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.debug(f"Failed to extract JSON: {e}")

    return None


def extract_json_or_default(response: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    JSON을 추출하거나 기본값을 반환합니다.

    Args:
        response: LLM 응답 문자열
        default: 추출 실패 시 반환할 기본값

    Returns:
        추출된 JSON 또는 기본값
    """
    if default is None:
        default = {}

    result = extract_json_from_response(response)
    return result if result is not None else default


# ============================================
# 대화 히스토리 포맷팅
# ============================================

def format_conversation_history(
    history: List[Dict[str, Any]],
    max_turns: int = 5
) -> str:
    """
    대화 히스토리를 문자열로 포맷합니다.

    Args:
        history: 대화 히스토리 리스트 (각 항목은 speaker, text 포함)
        max_turns: 포함할 최대 턴 수

    Returns:
        포맷된 대화 히스토리 문자열
    """
    if not history:
        return "(No conversation yet)"

    # 최근 max_turns 개의 턴만 포함
    recent_turns = history[-max_turns:]

    history_lines = []
    for turn in recent_turns:
        speaker_label = "AI" if turn.get("speaker") == "ai" else "User"
        text = turn.get("text", "")
        history_lines.append(f"{speaker_label}: {text}")

    return "\n".join(history_lines)


def format_conversation_history_korean(
    history: List[Dict[str, Any]],
    max_turns: int = 4
) -> str:
    """
    대화 히스토리를 한글 포맷으로 반환합니다.

    Args:
        history: 대화 히스토리 리스트
        max_turns: 포함할 최대 턴 수

    Returns:
        포맷된 대화 히스토리 문자열
    """
    if not history:
        return ""

    recent_turns = history[-max_turns:]

    history_text = ""
    for msg in recent_turns:
        speaker = msg.get("speaker", "Unknown")
        text = msg.get("text", "")
        history_text += f"{speaker}: {text}\n"

    return history_text


# ============================================
# 질문 정규화
# ============================================

def normalize_questions(questions: Any, expected_count: int = 3) -> List[str]:
    """
    질문 리스트를 정규화합니다.

    Args:
        questions: 질문 리스트 또는 기타 형식
        expected_count: 예상하는 질문 개수 (기본 3개)

    Returns:
        정규화된 문자열 질문 리스트
    """
    if not isinstance(questions, list):
        return []

    # 문자열만 필터링
    normalized = [str(q).strip() for q in questions if q]

    # 길이 검증
    if len(normalized) != expected_count:
        logger.warning(
            f"Expected {expected_count} questions, got {len(normalized)}"
        )

    return normalized


def validate_questions_count(questions: List[str], expected: int = 3) -> bool:
    """
    질문 개수가 예상과 일치하는지 검증합니다.

    Args:
        questions: 질문 리스트
        expected: 예상 개수

    Returns:
        True if count matches, False otherwise
    """
    return isinstance(questions, list) and len(questions) == expected


# ============================================
# 점수 정규화
# ============================================

def normalize_score(
    score: Any,
    min_val: int = 0,
    max_val: int = 100,
    default: Optional[int] = None
) -> Optional[int]:
    """
    점수를 지정된 범위 내로 정규화합니다.

    Args:
        score: 점수 값
        min_val: 최소값
        max_val: 최대값
        default: 파싱 실패 시 기본값

    Returns:
        정규화된 정수 점수 또는 기본값(default)
    """
    try:
        int_score = int(score)
        return max(min_val, min(max_val, int_score))
    except (ValueError, TypeError):
        logger.debug(f"Invalid score value: {score}, using default: {default}")
        return default


def normalize_score_from_string(
    text: str,
    min_val: int = 0,
    max_val: int = 100,
    default: Optional[int] = None
) -> Optional[int]:
    """
    텍스트에서 숫자를 찾아 점수로 정규화합니다.

    Args:
        text: 텍스트 (숫자 포함)
        min_val: 최소값
        max_val: 최대값
        default: 찾지 못한 경우 기본값

    Returns:
        정규화된 정수 점수 또는 기본값(default)
    """
    if not text:
        return default

    match = re.search(r'\d+', text)
    if match:
        return normalize_score(match.group(), min_val, max_val, default)
    return default


# ============================================
# 기타 유틸리티
# ============================================

def extract_first_number(text: str, default: int = 0) -> int:
    """
    텍스트에서 첫 번째 숫자를 추출합니다.

    Args:
        text: 텍스트
        default: 찾지 못한 경우 기본값

    Returns:
        추출된 정수 또는 기본값
    """
    match = re.search(r'\d+', text)
    return int(match.group()) if match else default


def clean_text(text: str) -> str:
    """
    텍스트를 정리합니다 (양쪽 공백 제거).

    Args:
        text: 입력 텍스트

    Returns:
        정리된 텍스트
    """
    return text.strip() if isinstance(text, str) else ""
