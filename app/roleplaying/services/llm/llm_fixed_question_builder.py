"""
LLM Fixed Question Builder Service
==================================
요약 기반 고정 질문 생성

역할:
- 사용자/상대방 요약을 기반으로 고정 질문 생성
- 정확히 3개의 follow-up 질문 생성
- 대화의 특정 턴에서 사용할 질문 세트 제공

예시:
    builder = FixedQuestionBuilderImpl()
    questions = await builder.build_fixed_questions(
        user_summary="사용자는 새로운 기능의 필요성을...",
        counterpart_summary="상대방은 일정 관계로..."
    )
    # ["질문1", "질문2", "질문3"]

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
    - app.roleplaying.services.utils (JSON 추출, 질문 정규화)
"""

import logging
from typing import List, Dict, Any

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import FIXED_QUESTIONS_PROMPT
from app.roleplaying.services.utils.service_utils import (
    extract_json_from_response,
    normalize_questions,
    validate_questions_count,
)

logger = logging.getLogger(__name__)


class FixedQuestionBuilderImpl(LLMServiceBase):
    """
    고정 질문 생성 서비스

    사용자/상대방 요약을 기반으로 3개의 고정 질문을 생성합니다.

    책임:
        - 메시지 요약을 받아 질문 생성
        - 정확히 3개의 질문 검증
        - JSON 응답 파싱 및 정규화

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - FIXED_QUESTIONS_PROMPT (프롬프트 상수)
        - extract_json_from_response (JSON 추출 유틸)
        - normalize_questions (질문 정규화 유틸)
        - validate_questions_count (질문 개수 검증 유틸)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        고정 질문 생성기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_QUESTION_GENERATION)
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
            temperature=temperature
        )

    async def build_fixed_questions(
        self,
        user_summary: str,
        counterpart_summary: str
    ) -> List[str]:
        """
        고정 질문 생성

        사용자와 상대방의 요약을 기반으로 3개의 follow-up 질문을 생성합니다.

        Args:
            user_summary: 사용자 메시지 요약
            counterpart_summary: 상대방 메시지 요약

        Returns:
            정확히 3개의 질문 리스트

        예시:
            questions = await builder.build_fixed_questions(
                user_summary="사용자는 새로운 기능의 필요성을 강조했습니다.",
                counterpart_summary="상대방은 기술적 제약을 언급했습니다."
            )
            # ["질문1", "질문2", "질문3"]
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = FIXED_QUESTIONS_PROMPT.format(
                user_summary=user_summary,
                counterpart_summary=counterpart_summary
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info("❓ [고정 질문 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # ====================================
            # Step 3: JSON 추출 및 검증
            # ====================================
            result = extract_json_from_response(response)

            if result:
                questions = result.get("questions", [])
                normalized_questions = normalize_questions(questions, expected_count=3)

                # 개수 검증
                if validate_questions_count(normalized_questions, expected=3):
                    logger.info(f"✅ [고정 질문 생성 완료] {len(normalized_questions)} 질문 생성")
                    return normalized_questions[:3]

            # ====================================
            # Step 4: 폴백 (기본 질문)
            # ====================================
            logger.warning("Failed to generate questions, using defaults")
            return [
                "Can you provide more details about your perspective?",
                "What are the main challenges you're facing?",
                "How would you approach this situation?",
            ]

        except Exception as e:
            logger.error(f"Fixed question building failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 질문 반환
            # ====================================
            return [
                "Can you provide more details?",
                "What are your thoughts on this?",
                "How do you plan to proceed?",
            ]
