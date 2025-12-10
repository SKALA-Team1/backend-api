"""
📄 파일명: prompt_builder.py
📌 역할: LLM 피드백 요청을 위한 프롬프트를 생성하고 포맷팅.
🧩 관련 모듈:
  - app.adapters.llm_client.py : 생성된 프롬프트를 LLM에 전달
  - response_parser.py         : LLM 응답 파싱
  - prompts.constants          : 프롬프트 템플릿 정의
🧠 주요 기능:
  - build_comprehensive_feedback_prompt(): 종합 피드백 프롬프트 생성
"""

from typing import List, Dict, Optional

from app.feedback.prompts.constants import COMPREHENSIVE_FEEDBACK_PROMPT_TEMPLATE


def build_comprehensive_feedback_prompt(
    utterances: List[Dict]
) -> str:
    """
    종합 피드백 생성용 프롬프트 빌드

    Args:
        utterances: 발화 목록
            [
                {
                    "user_text": "...",
                    "pronunciation_score": 85,
                    "pronunciation_feedback_ko": "...",
                    "grammar_score": 90,
                    "grammar_feedback_ko": "...",
                    "relevance_score": 75,
                    "relevance_feedback_ko": "..."
                },
                ...
            ]

    Returns:
        완성된 프롬프트 문자열
    """

    # 발화 목록 포맷팅
    utterances_text = ""
    for idx, utt in enumerate(utterances, start=1):
        user_text = utt.get("user_text", "")
        pronunciation_score = utt.get("pronunciation_score")
        pronunciation_feedback = utt.get("pronunciation_feedback_ko", "")
        grammar_score = utt.get("grammar_score")
        grammar_feedback = utt.get("grammar_feedback_ko", "")
        relevance_score = utt.get("relevance_score")
        relevance_feedback = utt.get("relevance_feedback_ko", "")

        utterances_text += f"""
### 발화 {idx}
- **사용자가 말한 내용**: "{user_text}"
- **발음 점수**: {pronunciation_score}/100 {'(없음)' if pronunciation_score is None else ''}
- **발음 피드백**: {pronunciation_feedback if pronunciation_feedback else '(없음)'}
- **문법 점수**: {grammar_score}/100 {'(없음)' if grammar_score is None else ''}
- **문법 피드백**: {grammar_feedback if grammar_feedback else '(없음)'}
- **맥락 점수**: {relevance_score}/100 {'(없음)' if relevance_score is None else ''}
- **맥락 피드백**: {relevance_feedback if relevance_feedback else '(없음)'}
"""

    # 템플릿에 데이터 삽입하여 최종 프롬프트 생성
    prompt = COMPREHENSIVE_FEEDBACK_PROMPT_TEMPLATE.format(
        utterances_text=utterances_text
    )

    return prompt
