"""
LLM Question Translator Service
================================
AI 질문 텍스트를 영문에서 한글로 번역하는 서비스

역할:
- AI 질문 한글 번역
- IT 도메인 전문 용어 유지
- 학습자 친화적인 한글 표현

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (QUESTION_BILINGUAL_PROMPT)
"""

import logging
import json
import re
from typing import Optional

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import QUESTION_BILINGUAL_PROMPT

logger = logging.getLogger(__name__)


class QuestionTranslatorImpl(LLMServiceBase):
    """
    AI 질문 번역 서비스

    영문 질문을 한글로 번역하며, IT 도메인 용어와
    학습자 친화적인 표현을 유지합니다.

    책임:
        - AI 질문 문장 번역
        - 번역 오류 처리 및 폴백
        - LLM 인스턴스 재사용 (성능 최적화)

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - QUESTION_BILINGUAL_PROMPT (번역 프롬프트)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        질문 번역기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_FEEDBACK)
            temperature: 창의성 레벨 (기본값: 0.3 - 일관된 번역)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_FEEDBACK,
            temperature=temperature
        )

    async def translate_question(
        self,
        question_en: str,
    ) -> str:
        """
        영문 질문을 한글로 번역

        Args:
            question_en: 영문 질문 텍스트

        Returns:
            한글 질문 텍스트
            (실패 시 원본 영문 반환)

        Examples:
            korean = await translator.translate_question(
                "Can you explain the database schema?"
            )
            # "데이터베이스 스키마를 설명해 주실 수 있나요?"
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성
            # ====================================
            prompt = QUESTION_BILINGUAL_PROMPT.format(
                english_question=question_en
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.debug(f"🟢 [질문 번역] 번역 중... en='{question_en[:50]}...'")
            response = await self.llm.invoke(prompt)
            response = response.strip()

            # ====================================
            # Step 3: JSON 파싱
            # ====================================
            korean_question = self._parse_translation_response(response, question_en)

            logger.debug(f"✅ [질문 번역] 완료: ko='{korean_question[:50]}...'")
            return korean_question

        except Exception as e:
            logger.warning(f"⚠️  [질문 번역] 실패: {e}, 원본 영문 반환")
            # Fallback: 번역 실패 시 원본 영문 반환
            return question_en

    def _parse_translation_response(
        self,
        response: str,
        fallback_text: str
    ) -> str:
        """
        LLM 응답에서 한글 질문 추출

        예상 형식:
        {"korean_question": "한글 질문"}

        Args:
            response: LLM 응답 문자열
            fallback_text: 파싱 실패 시 사용할 폴백 텍스트

        Returns:
            한글 질문 문자열
        """
        try:
            # JSON 추출 (텍스트 주변의 마크다운 제거 등)
            json_match = re.search(
                r'\{[^{}]*"korean_question"[^{}]*\}',
                response,
                re.DOTALL
            )
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                if isinstance(parsed, dict) and "korean_question" in parsed:
                    korean = parsed["korean_question"]
                    if isinstance(korean, str) and korean.strip():
                        return korean.strip()

        except json.JSONDecodeError as e:
            logger.debug(f"JSON 파싱 실패: {e}")
        except Exception as e:
            logger.debug(f"응답 파싱 오류: {e}")

        # Fallback: 파싱 실패 시 폴백 텍스트 반환
        logger.debug(f"폴백 사용: {fallback_text[:50]}...")
        return fallback_text


# ============================================
# 전역 인스턴스 (싱글톤)
# ============================================

_question_translator_instance: Optional["QuestionTranslatorImpl"] = None


def get_question_translator_instance() -> "QuestionTranslatorImpl":
    """
    질문 번역기 싱글톤 인스턴스 접근자

    LLM 클라이언트를 재사용하여 성능을 최적화합니다.
    """
    global _question_translator_instance
    if _question_translator_instance is None:
        _question_translator_instance = QuestionTranslatorImpl()
    return _question_translator_instance


# FastAPI 핸들러 등에서 사용하는 기본 인스턴스
question_translator = get_question_translator_instance()
