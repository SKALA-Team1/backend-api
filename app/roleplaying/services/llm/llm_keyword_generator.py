"""
LLM Recommended Keywords Generator Service
===========================================
AI 질문과 Slack 메시지 기반 추천 키워드 생성

역할:
- Slack 메시지에서 추출한 기술 키워드 생성
- 사용자 역할과 시나리오에 맞는 맥락-인식형 키워드 생성
- 3개의 도메인-특화 키워드 생성 (데이터베이스 마이그레이션, 레이턴시 최적화 등)

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (RECOMMENDED_KEYWORDS_PROMPT)
"""

import logging
import json
import re
from typing import List, Optional, Dict, Any

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import RECOMMENDED_KEYWORDS_PROMPT

logger = logging.getLogger(__name__)


class KeywordGeneratorImpl(LLMServiceBase):
    """
    추천 키워드 생성 서비스

    AI 질문과 Slack 메시지 컨텍스트 기반으로 사용자가 답변할 때 참고할
    도메인-특화 키워드를 생성합니다.

    책임:
        - 질문과 시나리오 컨텍스트 기반 키워드 생성
        - Slack 메시지에서 기술 용어 추출
        - LLM을 통한 자동 키워드 생성
        - JSON 파싱 및 오류 처리

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - RECOMMENDED_KEYWORDS_PROMPT (프롬프트 상수)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        키워드 생성기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_FEEDBACK)
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_FEEDBACK,
            temperature=temperature
        )

    async def generate_recommended_keywords(
        self,
        question: str,
        user_role: str,
        ai_role: str,
        scenario_context: str,
        slack_message: Optional[str] = None,
        conversation_summary: Optional[str] = None,
    ) -> List[str]:
        """
        AI 질문에 대한 추천 키워드 생성

        Slack 메시지 기반으로 사용자가 답변할 때 참고할 수 있는
        도메인-특화 키워드 3개를 생성합니다.

        Args:
            question: AI가 생성한 질문 (영문)
            user_role: 사용자 역할 (예: "Software Engineer", "Product Manager")
            ai_role: AI 역할 (예: "Tech Lead", "QA")
            scenario_context: 시나리오 배경 설명
            slack_message: 원본 Slack 메시지 (선택사항)
                          이를 기반으로 키워드 추출
            conversation_summary: 최근 대화 요약 (선택사항)

        Returns:
            추천 키워드 리스트 (최대 3개)
            예: ["database migration", "latency optimization", "connection pooling"]

        Examples:
            keywords = await generator.generate_recommended_keywords(
                question="How will you handle the latency issues?",
                user_role="Backend Engineer",
                ai_role="Tech Lead",
                scenario_context="Database migration project",
                slack_message="We're migrating to PostgreSQL and need to fix latency in the reports endpoint..."
            )
            # ["database migration", "latency optimization", "query profiling"]
        """
        try:
            # Slack 메시지가 없으면 기본값 사용
            slack_msg = slack_message or question
            conv_summary = conversation_summary or ""

            # ====================================
            # Step 1: 프롬프트 구성
            # ====================================
            prompt = RECOMMENDED_KEYWORDS_PROMPT.format(
                slack_message=slack_msg,
                question=question,
                user_role=user_role,
                ai_role=ai_role,
                scenario_context=scenario_context,
                conversation_summary=conv_summary
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info(
                f"🟢 [추천 키워드 생성] LLM 호출 중... "
                f"role={user_role}, question='{question[:50]}...'"
            )
            response = await self.llm.invoke(prompt)
            response = response.strip()

            # ====================================
            # Step 3: JSON 파싱
            # ====================================
            keywords = self._parse_keywords_response(response)

            logger.info(f"✅ [추천 키워드 생성 완료] keywords={keywords}")
            return keywords

        except Exception as e:
            logger.error(f"Recommended keywords generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 빈 리스트 반환
            # ====================================
            return []

    def _parse_keywords_response(self, response: str) -> List[str]:
        """
        LLM 응답에서 키워드 추출

        LLM이 반환한 JSON 형식의 응답에서 keywords 배열을 추출합니다.

        예상 형식:
        {"keywords": ["keyword1", "keyword2", "keyword3"]}

        Args:
            response: LLM 응답 문자열

        Returns:
            키워드 리스트 (최대 3개)
        """
        try:
            # JSON 추출 (텍스트 주변의 마크다운 제거 등)
            json_match = re.search(r'\{[^{}]*"keywords"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                if isinstance(parsed, dict) and "keywords" in parsed:
                    keywords = parsed["keywords"]
                    if isinstance(keywords, list):
                        # 최대 3개까지만 반환
                        return [kw for kw in keywords[:3] if isinstance(kw, str) and kw.strip()]

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from keywords response: {e}")
        except Exception as e:
            logger.warning(f"Error parsing keywords response: {e}")

        # Fallback: 빈 리스트 반환
        logger.debug(f"Falling back to empty keywords list. Response was: {response[:100]}...")
        return []


# ============================================
# 전역 인스턴스 (레거시 호환성)
# ============================================

_keyword_generator_instance: Optional["KeywordGeneratorImpl"] = None


def get_keyword_generator_instance() -> "KeywordGeneratorImpl":
    """레거시 코드 호환을 위한 전역 인스턴스 접근자"""
    global _keyword_generator_instance
    if _keyword_generator_instance is None:
        _keyword_generator_instance = KeywordGeneratorImpl()
    return _keyword_generator_instance


# FastAPI 핸들러 등에서 사용하는 기본 인스턴스
keyword_generator = get_keyword_generator_instance()