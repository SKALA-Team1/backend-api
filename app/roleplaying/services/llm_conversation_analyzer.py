"""
LLM Conversation Analyzer Service
==================================
대화 상황 분석 및 상황 요약 생성

역할:
- Slack 등의 메시지 대화를 분석
- 핵심 상황을 2-3문장으로 요약
- 시나리오 생성의 기초 데이터 제공

예시:
    analyzer = ConversationAnalyzerImpl()
    situation = await analyzer.analyze_situation(
        messages=[{"senderName": "John", "text": "..."}],
        my_role="Software Engineer",
        conversation_date="2024-01-01"
    )

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
"""

import logging
from typing import Dict, Any, List

from app.config import settings
from app.roleplaying.services.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import CONVERSATION_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class ConversationAnalyzerImpl(LLMServiceBase):
    """
    대화 상황 분석 서비스

    Slack 대화를 분석하여 핵심 상황을 요약합니다.

    책임:
        - 메시지 리스트를 받아 정제
        - LLM을 통해 상황 분석
        - 2-3문장의 요약 생성

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - CONVERSATION_ANALYSIS_PROMPT (프롬프트 상수)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        대화 분석기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_QUESTION_GENERATION)
            temperature: 창의성 레벨 (기본값: 0.3, 분석에는 낮은 값 추천)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
            temperature=temperature
        )

    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """
        대화 상황 분석

        메시지 리스트를 분석하여 핵심 상황을 요약합니다.

        Args:
            messages: 사용자-AI 메시지 리스트
                     각 항목: {"senderName": str, "text": str}
            my_role: 사용자의 역할 (예: 'Software Engineer')
            conversation_date: 대화 날짜 (예: '2024-01-01')

        Returns:
            상황 분석 결과 텍스트 (2-3문장)

        예시:
            situation = await analyzer.analyze_situation(
                messages=[...],
                my_role="Software Engineer",
                conversation_date="2024-01-01"
            )
            # "John과 Mary가 새로운 프로젝트의 기술 스택을 논의하고 있습니다..."
        """
        try:
            # ====================================
            # Step 1: 메시지 포맷팅
            # ====================================
            formatted_messages = []
            for msg in messages:
                sender = msg.get("senderName", "Unknown")
                text = msg.get("text", "")
                formatted_messages.append(f"{sender}: {text}")

            conversation_text = "\n".join(formatted_messages)

            # ====================================
            # Step 2: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = CONVERSATION_ANALYSIS_PROMPT.format(
                conversation_text=conversation_text,
                my_role=my_role,
                conversation_date=conversation_date
            )

            # ====================================
            # Step 3: LLM 호출
            # ====================================
            logger.info("🔵 [대화 분석] LLM 호출 중...")
            situation = await self.llm.invoke(prompt)
            situation = situation.strip()

            logger.info(f"✅ [대화 분석 완료] {situation[:100]}...")
            return situation

        except Exception as e:
            logger.error(f"Conversation analysis failed: {e}", exc_info=True)
            return "Unable to analyze conversation"
