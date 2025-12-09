"""
IT Explanation Evaluation Service
==================================
사용자의 IT 용어 설명 답변을 평가하는 서비스

역할:
- LLM을 사용하여 답변의 명확성, 기술적 정확성, 전문용어 사용 평가
- 3가지 기준별 점수 (0-100) 제공
- 종합 점수 계산 (단순 평균)
- 구체적인 피드백 제공
"""

import logging
from typing import Dict, Any, Optional

from app.config import settings
from app.roleplaying.services.llm.llm_provider_factory import create_llm_provider
from app.it_explanation.prompts.constants import IT_EXPLANATION_EVALUATION_PROMPT
from app.roleplaying.services.utils.service_utils import extract_json_from_response

logger = logging.getLogger(__name__)


class EvaluationService:
    """IT 설명 답변 평가 서비스"""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        평가 서비스 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_FEEDBACK)
            temperature: 창의성 레벨 (낮을수록 일관적, 기본값: 0.3)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature
        )

        logger.info(f"EvaluationService initialized with model: {self.model_name}")

    async def evaluate_answer(
        self,
        question_text: str,
        user_answer: str,
        key_keywords: list,
        model_answer: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 답변 평가

        Args:
            question_text: 질문 내용
            user_answer: 사용자 답변
            key_keywords: 핵심 키워드 리스트
            model_answer: 모범 답안

        Returns:
            {
                "clarity_score": int (0-100),
                "technical_accuracy_score": int (0-100),
                "terminology_score": int (0-100),
                "overall_score": int (0-100),
                "feedback": str
            }
            또는 None (평가 실패 시)
        """
        try:
            # 프롬프트 구성
            keywords_str = ', '.join(key_keywords) if key_keywords else 'None'

            prompt = IT_EXPLANATION_EVALUATION_PROMPT.format(
                question_text=question_text,
                user_answer=user_answer,
                key_keywords=keywords_str,
                model_answer=model_answer
            )

            logger.info("🔍 [IT 설명 평가] LLM 호출 중...")
            logger.debug(f"Question: {question_text[:50]}...")
            logger.debug(f"User answer: {user_answer[:100]}...")

            # LLM 호출
            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)

            logger.debug(f"LLM response: {response_text[:200]}...")

            # JSON 추출
            result = extract_json_from_response(response_text)

            if not result:
                logger.warning("Failed to parse evaluation result")
                return None

            # 필수 필드 검증
            required_fields = ["clarity_score", "technical_accuracy_score", "terminology_score", "feedback"]
            if not all(field in result for field in required_fields):
                logger.warning(f"Missing required fields in evaluation result: {result.keys()}")
                return None

            # 종합 점수 계산 (단순 평균)
            overall_score = int(
                (result["clarity_score"] +
                 result["technical_accuracy_score"] +
                 result["terminology_score"]) / 3
            )
            result["overall_score"] = overall_score

            logger.info(f"✅ [평가 완료] 종합 {overall_score}점 "
                       f"(명확성: {result['clarity_score']}, "
                       f"정확성: {result['technical_accuracy_score']}, "
                       f"용어: {result['terminology_score']})")

            return result

        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            return None
