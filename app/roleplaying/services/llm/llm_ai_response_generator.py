"""
LLM AI Response Generator Service
=================================
시나리오 기반 AI 응답 생성

역할:
- 시나리오 역할 설정에 따라 자연스러운 AI 응답 생성
- 대화 히스토리와 상황 컨텍스트 고려
- 전문적이고 실무적인 응답 제공

예시:
    generator = AIResponseGeneratorImpl()
    response = await generator.generate_ai_response(
        situation="Project discussion",
        ai_role="Senior PM",
        my_role="Team Member",
        conversation_history=[...]
    )
    # "That's a great point. Let me think about the timeline..."

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
    - app.roleplaying.services.utils (대화 히스토리 포맷팅)
"""

import logging
from typing import Dict, Any, List

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import AI_RESPONSE_PROMPT
from app.roleplaying.services.utils.service_utils import format_conversation_history_korean

logger = logging.getLogger(__name__)


class AIResponseGeneratorImpl(LLMServiceBase):
    """
    AI 응답 생성 서비스

    시나리오 컨텍스트 내에서 자연스러운 AI 응답을 생성합니다.

    책임:
        - 역할에 맞는 응답 생성
        - 대화 히스토리와 상황 반영
        - 전문적이고 실무적인 톤 유지

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - AI_RESPONSE_PROMPT (프롬프트 상수)
        - format_conversation_history_korean (히스토리 포맷팅 유틸)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        AI 응답 생성기 초기화

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

    async def generate_ai_response(
        self,
        situation: str,
        ai_role: str,
        my_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        AI 응답 생성

        시나리오 컨텍스트와 대화 히스토리를 고려하여 AI 응답을 생성합니다.

        Args:
            situation: 시나리오 상황 (예: "Product launch planning")
            ai_role: AI가 맡을 역할 (예: "Senior Product Manager")
            my_role: 사용자의 역할 (예: "Junior Engineer")
            conversation_history: 이전 대화 히스토리 (리스트)
                                 각 항목: {"speaker": "user|ai", "text": "..."}

        Returns:
            생성된 AI 응답 문자열

        예시:
            response = await generator.generate_ai_response(
                situation="Discussing new feature",
                ai_role="Team Lead",
                my_role="Developer",
                conversation_history=[...]
            )
            # "That's an interesting approach. Have you considered..."
        """
        try:
            # ====================================
            # Step 1: 대화 히스토리 포맷팅
            # ====================================
            # 최근 4개 메시지만 사용 (2턴)
            history_text = format_conversation_history_korean(
                conversation_history,
                max_turns=4
            )

            # ====================================
            # Step 2: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = AI_RESPONSE_PROMPT.format(
                ai_role=ai_role,
                my_role=my_role,
                situation=situation,
                history_text=history_text
            )

            # ====================================
            # Step 3: LLM 호출
            # ====================================
            logger.info("🔵 [AI 응답 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)
            response = response.strip()

            logger.info(f"✅ [AI 응답 생성 완료] {response[:80]}...")
            return response

        except Exception as e:
            logger.error(f"AI response generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 응답 반환
            # ====================================
            return "I appreciate your input. Could you clarify further?"
