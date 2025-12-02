"""
LLM Message Summarizer Service
==============================
메시지 목록 요약

역할:
- 사용자 또는 상대방의 메시지 목록을 2-3문장으로 요약
- 관점별(사용자/상대방) 요약 생성
- 고정 질문 생성의 기초 데이터 제공

예시:
    summarizer = MessageSummarizerImpl()
    user_summary = await summarizer.summarize_messages(
        messages=[...],
        perspective="user"
    )
    # "사용자는 새로운 기능의 필요성을..."

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
"""

import logging
from typing import Dict, Any, List

from app.config import settings
from app.roleplaying.services.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import MESSAGE_SUMMARY_PROMPT

logger = logging.getLogger(__name__)


class MessageSummarizerImpl(LLMServiceBase):
    """
    메시지 요약 서비스

    메시지 목록을 간결하게 요약합니다.

    책임:
        - 메시지 리스트를 포맷팅
        - LLM을 통해 요약 생성
        - 2-3문장의 핵심 내용 추출

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - MESSAGE_SUMMARY_PROMPT (프롬프트 상수)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """
        메시지 요약기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_QUESTION_GENERATION)
            temperature: 창의성 레벨 (기본값: 0.3, 요약에는 낮은 값 추천)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
            temperature=temperature
        )

    async def summarize_messages(
        self,
        messages: List[str],
        perspective: str = "user"
    ) -> str:
        """
        메시지 요약

        메시지 목록을 2-3문장으로 요약합니다.

        Args:
            messages: 요약할 메시지 목록 (리스트)
            perspective: 관점 ("user" 또는 "counterpart")
                        - "user": 사용자 관점으로 요약
                        - "counterpart": 상대방 관점으로 요약

        Returns:
            요약된 텍스트 (2-3문장)

        예시:
            user_summary = await summarizer.summarize_messages(
                messages=["I think...", "Based on...", "Therefore..."],
                perspective="user"
            )
            # "사용자는 새로운 기능의 필요성을 강조하고 구현 방안을 제시했습니다."
        """
        try:
            # ====================================
            # Step 1: 메시지 포맷팅
            # ====================================
            messages_text = "\n".join(messages) if messages else ""

            # ====================================
            # Step 2: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = MESSAGE_SUMMARY_PROMPT.format(
                perspective=perspective,
                messages_text=messages_text
            )

            # ====================================
            # Step 3: LLM 호출
            # ====================================
            logger.info(f"📝 [메시지 요약] {perspective} 관점 요약 중...")
            summary = await self.llm.invoke(prompt)
            summary = summary.strip()

            logger.info(f"✅ [메시지 요약 완료] {summary[:80]}...")
            return summary

        except Exception as e:
            logger.error(f"Message summarization failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본값 반환
            # ====================================
            return "Messages could not be summarized."
