"""
📄 파일명: response_parser.py
📌 역할: LLM이 반환한 피드백 응답(JSON/Text)을 파싱하여 구조화된 형태로 변환.
🧩 관련 모듈:
  - llm_client.py : 원본 응답 수신
  - aggregation_service.py : 구조화된 결과를 전달
🧠 주요 기능:
  - parse_comprehensive_feedback_response(): 종합 피드백 JSON 파싱
"""

import json
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def parse_comprehensive_feedback_response(response_text: str) -> Optional[Dict[str, str]]:
    """
    GPT-4 응답에서 JSON 추출 및 파싱

    Args:
        response_text: GPT-4 raw 응답 텍스트

    Returns:
        {
            "feedback_long": "...",
            "feedback_short": "..."
        }
        또는 None (파싱 실패)
    """
    try:
        # Step 1: 응답에서 JSON 객체 부분을 더 안정적으로 찾기
        # 첫 번째 '{' 와 마지막 '}' 사이의 문자열을 추출
        # (피드백 내용에 { } 문자가 포함될 수 있으므로 정규식 [^{}] 방식은 취약)
        start_index = response_text.find('{')
        end_index = response_text.rfind('}')

        if start_index == -1 or end_index == -1 or end_index < start_index:
            logger.warning(f"No JSON object found in response: {response_text[:200]}...")
            return None

        json_str = response_text[start_index : end_index + 1]
        logger.debug(f"Extracted JSON: {json_str[:200]}...")

        # Step 2: JSON 파싱
        parsed = json.loads(json_str)

        # Step 3: 필수 필드 확인
        if "feedback_long" not in parsed or "feedback_short" not in parsed:
            logger.warning(f"Missing required fields in JSON: {parsed.keys()}")
            return None

        feedback_long = parsed.get("feedback_long", "").strip()
        feedback_short = parsed.get("feedback_short", "").strip()

        if not feedback_long or not feedback_short:
            logger.warning("Empty feedback fields detected")
            return None

        logger.info(f"✅ Successfully parsed feedback (long: {len(feedback_long)} chars, short: {len(feedback_short)} chars)")

        return {
            "feedback_long": feedback_long,
            "feedback_short": feedback_short
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}, response: {response_text[:200]}...")
        return None

    except Exception as e:
        logger.error(f"Unexpected error during parsing: {e}", exc_info=True)
        return None
