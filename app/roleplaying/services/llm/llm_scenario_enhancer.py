"""
LLM Scenario Enhancer Service
============================
시나리오 상황 구체화 및 관련 정보 생성

역할:
- 사용자 입력 상황을 구체적인 롤플레이 상황으로 변환
- 과거 시나리오 컨텍스트를 고려한 확장
- 시나리오 제목 생성
- 프롬프트 기반 질문 생성

예시:
    enhancer = ScenarioEnhancerImpl()
    enhanced = await enhancer.enhance_situation(
        situation="Team meeting",
        ai_role="Manager",
        my_role="Engineer",
        context=[...]
    )
    # "전 분기 성과를 바탕으로 새로운 프로젝트를..."

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
    - app.roleplaying.services.utils (JSON 추출, 질문 정규화)
"""

import logging
from typing import Dict, Any, List

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import (
    SITUATION_ENHANCEMENT_PROMPT,
    TITLE_GENERATION_PROMPT,
    PROMPT_QUESTIONS_PROMPT,
)
from app.roleplaying.services.utils.service_utils import (
    extract_json_from_response,
    normalize_questions,
)

logger = logging.getLogger(__name__)


class ScenarioEnhancerImpl(LLMServiceBase):
    """
    시나리오 향상 서비스

    시나리오 상황을 구체화하고 관련 정보를 생성합니다.

    책임:
        - 상황 설명을 구체적인 롤플레이 상황으로 변환
        - 시나리오 제목 생성
        - 프롬프트 기반 고정 질문 생성
        - 과거 컨텍스트 반영

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - SITUATION_ENHANCEMENT_PROMPT (상황 구체화 프롬프트)
        - TITLE_GENERATION_PROMPT (제목 생성 프롬프트)
        - PROMPT_QUESTIONS_PROMPT (프롬프트 기반 질문 프롬프트)
        - extract_json_from_response (JSON 추출 유틸)
        - normalize_questions (질문 정규화 유틸)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        시나리오 향상기 초기화

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

    async def enhance_situation(
        self,
        situation: str,
        ai_role: str,
        my_role: str,
        context: List[Dict[str, str]] = None
    ) -> str:
        """
        상황 구체화

        사용자 입력 상황을 더 구체적인 롤플레이 상황으로 변환합니다.

        Args:
            situation: 사용자 입력 상황 (예: "Team meeting")
            ai_role: AI의 역할 (예: "Manager")
            my_role: 사용자의 역할 (예: "Engineer")
            context: 과거 시나리오 컨텍스트 (옵션)
                    각 항목: {"situation": "..."}

        Returns:
            구체화된 상황 텍스트 (2-3문장)

        예시:
            enhanced = await enhancer.enhance_situation(
                situation="Team meeting",
                ai_role="Manager",
                my_role="Engineer",
                context=[{"situation": "New project launch"}]
            )
            # "지난주 론칭한 프로젝트의 진행 상황을 논의하는..."
        """
        try:
            # ====================================
            # Step 1: 컨텍스트 포맷팅
            # ====================================
            context_text = ""
            if context:
                context_text = "이전 시나리오:\n"
                for scenario in context[:3]:  # 최근 3개만
                    situation_text = scenario.get("situation", "")
                    if situation_text:
                        context_text += f"- {situation_text}\n"

            # ====================================
            # Step 2: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = SITUATION_ENHANCEMENT_PROMPT.format(
                my_role=my_role,
                ai_role=ai_role,
                situation=situation,
                context_text=context_text
            )

            # ====================================
            # Step 3: LLM 호출
            # ====================================
            logger.info("🎬 [상황 구체화] LLM 호출 중...")
            enhanced = await self.llm.invoke(prompt)
            enhanced = enhanced.strip()

            logger.info(f"✅ [상황 구체화 완료] {enhanced[:80]}...")
            return enhanced

        except Exception as e:
            logger.error(f"Situation enhancement failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 원본 상황 반환
            # ====================================
            return situation

    async def generate_title(
        self,
        situation: str,
        ai_role: str,
        my_role: str
    ) -> str:
        """
        시나리오 제목 생성

        상황을 기반으로 5-10단어의 간결한 제목을 생성합니다.

        Args:
            situation: 시나리오 상황 설명
            ai_role: AI의 역할
            my_role: 사용자의 역할

        Returns:
            생성된 제목 (5-10단어)

        예시:
            title = await enhancer.generate_title(
                situation="Product launch planning meeting",
                ai_role="Product Manager",
                my_role="Developer"
            )
            # "새로운 제품 출시 계획 회의"
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = TITLE_GENERATION_PROMPT.format(
                situation=situation,
                my_role=my_role,
                ai_role=ai_role
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info("📝 [제목 생성] LLM 호출 중...")
            title = await self.llm.invoke(prompt)
            title = title.strip()

            logger.info(f"✅ [제목 생성 완료] {title}")
            return title

        except Exception as e:
            logger.error(f"Title generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본값 반환
            # ====================================
            return "Roleplay Scenario"

    async def generate_prompt_questions(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> List[str]:
        """
        프롬프트 기반 고정 질문 생성

        사용자 입력 상황에서 정확히 3개의 질문을 생성합니다.
        (대화 시작/중간/마무리 질문)

        Args:
            situation: 상황 텍스트
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            정확히 3개의 질문 리스트

        예시:
            questions = await enhancer.generate_prompt_questions(
                situation="New project planning",
                my_role="Developer",
                ai_role="Project Manager"
            )
            # ["시작 질문", "중간 질문", "마무리 질문"]
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = PROMPT_QUESTIONS_PROMPT.format(
                situation=situation,
                my_role=my_role,
                ai_role=ai_role
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info("❓ [프롬프트 질문 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # ====================================
            # Step 3: JSON 추출 및 검증
            # ====================================
            result = extract_json_from_response(response)

            if result:
                questions = result.get("questions", [])
                normalized_questions = normalize_questions(questions, expected_count=3)

                # 부족한 질문 채우기
                while len(normalized_questions) < 3:
                    normalized_questions.append(
                        f"Tell me more about {ai_role.lower()}"
                    )

                logger.info(f"✅ [프롬프트 질문 생성 완료] {len(normalized_questions)} 질문 생성")
                return normalized_questions[:3]

            # ====================================
            # Step 4: 폴백 (기본 질문)
            # ====================================
            logger.warning("Failed to parse prompt questions, using defaults")
            return [
                "Can you start by explaining the situation?",
                "What are the key priorities?",
                "How do we move forward from here?",
            ]

        except Exception as e:
            logger.error(f"Prompt question generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 질문 반환
            # ====================================
            return [
                "Can you explain more?",
                "What's your view on this?",
                "How should we proceed?",
            ]
