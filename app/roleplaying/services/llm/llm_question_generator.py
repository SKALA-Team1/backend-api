"""
LLM Question Generator Service
==============================
대화 기반 질문 생성

역할:
- 시나리오 및 대화 히스토리 기반 다음 질문 생성
- Follow-up 질문 생성 (수동 프롬프트 입력용)
- 동적 질문 생성으로 자연스러운 대화 유지

예시:
    generator = QuestionGeneratorImpl()
    question = await generator.generate_next_question(
        situation="Product launch discussion",
        conversation_history=[...]
    )
    # "What timeline are you thinking for the release?"

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
    - app.roleplaying.services.utils (대화 히스토리 포맷팅)
"""

import logging
from typing import Dict, Any, List

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import FOLLOWUP_QUESTION_PROMPT
from app.roleplaying.services.utils.service_utils import format_conversation_history_korean

logger = logging.getLogger(__name__)


class QuestionGeneratorImpl(LLMServiceBase):
    """
    질문 생성 서비스

    대화 컨텍스트 기반으로 자연스러운 follow-up 질문을 생성합니다.

    책임:
        - 대화 히스토리를 포맷팅
        - LLM을 통해 자연스러운 질문 생성
        - 단일 질문 또는 수동 프롬프트로 유연하게 대응

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - FOLLOWUP_QUESTION_PROMPT (프롬프트 상수)
        - format_conversation_history_korean (히스토리 포맷팅 유틸)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        질문 생성기 초기화

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

    async def generate_next_question(
        self,
        situation: str,
        conversation_history: List[Dict[str, str]],
        role: str = "AI",
        user_text: str = None
    ) -> str:
        """
        다음 질문 생성 (대화 히스토리 기반)

        최근 대화 히스토리를 고려하여 자연스러운 follow-up 질문을 생성합니다.

        Args:
            situation: 시나리오 상황 (예: "Product launch planning")
            conversation_history: 이전 대화 히스토리 (리스트)
                                 각 항목: {"speaker": "user|ai", "text": "..."}
            role: AI의 역할 (기본값: "AI")
            user_text: 사용자의 최근 메시지 (None이면 conversation_history에서 자동 추출)

        Returns:
            생성된 질문 문자열

        예시:
            question = await generator.generate_next_question(
                situation="Product launch",
                conversation_history=[...],
                role="Product Manager",
                user_text="We need to launch next quarter"
            )
            # "What timeline are you thinking for the release?"
        """
        try:
            # ====================================
            # Step 1: 대화 히스토리 포맷팅
            # ====================================
            # 최근 4개 메시지만 사용 (2턴)
            formatted_history = format_conversation_history_korean(
                conversation_history,
                max_turns=4
            )

            # ====================================
            # Step 2: 사용자 최근 메시지 추출
            # ====================================
            if user_text is None and conversation_history:
                # conversation_history에서 마지막 사용자 메시지 찾기
                for msg in reversed(conversation_history):
                    if msg.get("speaker", "").lower() in ["user", "사용자"]:
                        user_text = msg.get("text", "")
                        break

            user_text = user_text or "Tell me more about your situation"

            # ====================================
            # Step 3: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = FOLLOWUP_QUESTION_PROMPT.format(
                role=role,
                scenario_context=situation,
                conversation_history=formatted_history,
                user_text=user_text
            )

            # ====================================
            # Step 4: LLM 호출
            # ====================================

            question = await self.llm.invoke(prompt)
            question = question.strip()


            return question

        except Exception as e:
            logger.error(f"Next question generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 질문 반환
            # ====================================
            return "Could you tell me more about that?"

    async def generate_followup_question(self, prompt: str) -> str:
        """
        Follow-up 질문 생성 (수동 프롬프트 입력)

        사용자가 제공한 프롬프트를 사용하여 follow-up 질문을 생성합니다.

        Args:
            prompt: LLM에 전달할 완전한 프롬프트 문자열

        Returns:
            생성된 질문 문자열

        예시:
            prompt = "Ask a follow-up question about ..."
            question = await generator.generate_followup_question(prompt)
        """
        try:
            # ====================================
            # Step 1: LLM 호출
            # ====================================
            logger.info("🟣 [Follow-up 질문 생성] LLM 호출 중...")
            question = await self.llm.invoke(prompt)
            question = question.strip()


            return question

        except Exception as e:
            logger.error(f"Follow-up question generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 질문 반환
            # ====================================
            return "Could you tell me more about that?"

    async def generate_followup_question_stream(self, prompt: str):
        """
        Follow-up 질문 스트리밍 생성

        프롬프트를 받아 질문을 단어 단위로 스트리밍 생성합니다.

        Args:
            prompt: LLM에 전달할 완전한 프롬프트 문자열

        Yields:
            생성된 텍스트 청크 (단어 단위)

        예시:
            async for chunk in generator.generate_followup_question_stream(prompt):
                print(chunk, end="", flush=True)
        """
        try:
            # ====================================
            # Step 1: LLM 호출 (스트리밍)
            # ====================================
            logger.info("🟣 [Follow-up 질문 스트리밍] LLM 호출 중...")

            # 마크다운 스트리밍 메서드 사용
            if hasattr(self.llm, 'stream'):
                async for chunk in self.llm.stream(prompt):
                    # 빈 chunk는 필터링 (유효하지 않은 JSON 에러 방지)
                    if chunk and chunk.strip():
                        yield chunk
            else:
                # 스트리밍 미지원 시 일반 호출
                response = await self.llm.invoke(prompt)
                words = response.split()
                for word in words:
                    if word.strip():  # 빈 word 필터링
                        yield word + " "



        except Exception as e:
            logger.error(f"Follow-up question streaming failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본 질문 반환
            # ====================================
            fallback = "Could you tell me more about that?"
            yield fallback
