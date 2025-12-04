"""
LLM Feedback Translator Service
================================
피드백 텍스트를 영문에서 한글로 번역하는 서비스

역할:
- 발음/문법/관련성 피드백 한글 번역
- IT 도메인 전문 용어 유지
- 학습자 친화적인 한글 표현

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (FEEDBACK_BILINGUAL_PROMPT)
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import FEEDBACK_BILINGUAL_PROMPT

logger = logging.getLogger(__name__)


class FeedbackTranslatorImpl(LLMServiceBase):
    """
    피드백 번역 서비스

    영문 피드백을 한글로 번역하며, IT 도메인 용어와
    학습자 친화적인 표현을 유지합니다.

    책임:
        - 개별 피드백 문장 번역
        - 여러 피드백 섹션 병렬 처리
        - 번역 오류 처리 및 폴백

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - FEEDBACK_BILINGUAL_PROMPT (번역 프롬프트)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        피드백 번역기 초기화

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

    async def translate_feedback(
        self,
        feedback_en: str,
    ) -> str:
        """
        영문 피드백을 한글로 번역

        Args:
            feedback_en: 영문 피드백 텍스트

        Returns:
            한글 피드백 텍스트
            (실패 시 원본 영문 반환)

        Examples:
            korean = await translator.translate_feedback(
                "Pronunciation is clear. Well done!"
            )
            # "발음이 명확합니다. 잘했습니다!"
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성
            # ====================================
            prompt = FEEDBACK_BILINGUAL_PROMPT.format(
                english_feedback=feedback_en
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.debug(f"🟢 [피드백 번역] 번역 중... en='{feedback_en[:50]}...'")
            response = await self.llm.invoke(prompt)
            response = response.strip()

            # ====================================
            # Step 3: JSON 파싱
            # ====================================
            korean_feedback = self._parse_translation_response(response, feedback_en)

            logger.debug(f"✅ [피드백 번역] 완료: ko='{korean_feedback[:50]}...'")
            return korean_feedback

        except Exception as e:
            logger.warning(f"⚠️  [피드백 번역] 실패: {e}, 원본 영문 반환")
            # Fallback: 번역 실패 시 원본 영문 반환
            return feedback_en

    async def translate_feedback_sections(
        self,
        sections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        여러 피드백 섹션을 일괄 번역

        각 섹션의 feedback_en을 feedback_ko로 추가합니다.

        Args:
            sections: 피드백 섹션 리스트
                [
                    {
                        "type": "pronunciation",
                        "feedback_en": "...",
                        "score": 70
                    },
                    ...
                ]

        Returns:
            번역된 섹션 리스트
            [
                {
                    "type": "pronunciation",
                    "feedback_en": "...",
                    "feedback_ko": "...",
                    "score": 70
                },
                ...
            ]
        """
        try:
            translated_sections = []

            for section in sections:
                try:
                    section_copy = section.copy()
                    feedback_en = section_copy.get("feedback_en", "")

                    if feedback_en:
                        # 각 섹션 번역
                        feedback_ko = await self.translate_feedback(feedback_en)
                        section_copy["feedback_ko"] = feedback_ko
                    else:
                        section_copy["feedback_ko"] = ""

                    translated_sections.append(section_copy)

                except Exception as e:
                    logger.warning(
                        f"⚠️  [섹션 번역] 개별 섹션 번역 실패: {e}, 섹션={section.get('type')}"
                    )
                    # 개별 섹션 실패 시에도 진행 (fallback 포함)
                    section_copy = section.copy()
                    section_copy["feedback_ko"] = section.get("feedback_en", "")
                    translated_sections.append(section_copy)

            logger.info(
                f"✅ [피드백 섹션 번역] 완료: {len(translated_sections)}개 섹션"
            )
            return translated_sections

        except Exception as e:
            logger.error(
                f"❌ [피드백 섹션 번역] 전체 실패: {e}, 원본 반환"
            )
            # 전체 실패 시 feedback_ko에 feedback_en 복사
            fallback_sections = []
            for section in sections:
                section_copy = section.copy()
                section_copy["feedback_ko"] = section.get("feedback_en", "")
                fallback_sections.append(section_copy)
            return fallback_sections

    def _parse_translation_response(
        self,
        response: str,
        fallback_text: str
    ) -> str:
        """
        LLM 응답에서 한글 피드백 추출

        예상 형식:
        {"korean_feedback": "한글 피드백"}

        Args:
            response: LLM 응답 문자열
            fallback_text: 파싱 실패 시 사용할 폴백 텍스트

        Returns:
            한글 피드백 문자열
        """
        try:
            # JSON 추출 (텍스트 주변의 마크다운 제거 등)
            json_match = re.search(
                r'\{[^{}]*"korean_feedback"[^{}]*\}',
                response,
                re.DOTALL
            )
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                if isinstance(parsed, dict) and "korean_feedback" in parsed:
                    korean = parsed["korean_feedback"]
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
# 전역 인스턴스 (레거시 호환성)
# ============================================

_feedback_translator_instance: Optional["FeedbackTranslatorImpl"] = None


def get_feedback_translator_instance() -> "FeedbackTranslatorImpl":
    """레거시 코드 호환을 위한 전역 인스턴스 접근자"""
    global _feedback_translator_instance
    if _feedback_translator_instance is None:
        _feedback_translator_instance = FeedbackTranslatorImpl()
    return _feedback_translator_instance


# FastAPI 핸들러 등에서 사용하는 기본 인스턴스
feedback_translator = get_feedback_translator_instance()