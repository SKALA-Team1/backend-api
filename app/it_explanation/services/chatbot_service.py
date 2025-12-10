"""
IT Chatbot Service
==================
IT 용어를 쉽게 설명해주는 챗봇 서비스

역할:
- 사용자 질문에 대해 쉽고 명확한 설명 제공
- 대화 히스토리를 고려한 컨텍스트 기반 응답
- 최근 3-5턴의 대화만 유지 (메모리 효율)
"""

import logging
from typing import List, Dict, Optional

from app.config import settings
from app.roleplaying.services.llm.llm_provider_factory import create_llm_provider
from app.it_explanation.prompts.constants import IT_CHATBOT_PROMPT

logger = logging.getLogger(__name__)


class ChatbotService:
    """IT 용어 설명 챗봇 서비스"""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        챗봇 서비스 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_AI_RESPONSE)
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_AI_RESPONSE
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai",
            api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature
        )

        # 최근 5턴만 유지 (총 10개 메시지: 사용자 5개 + AI 5개)
        self.max_history_turns = 5

        logger.info(f"ChatbotService initialized with model: {self.model_name}")

    async def get_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        current_question: Optional[Dict[str, str]] = None
    ) -> str:
        """
        챗봇 응답 생성

        Args:
            user_message: 사용자 질문
            conversation_history: 대화 히스토리
                                 [{"role": "user", "content": "..."},
                                  {"role": "assistant", "content": "..."}]
            current_question: 현재 연습 중인 질문
                            {"question_text": "...", "question_text_ko": "..."}

        Returns:
            챗봇 응답 텍스트
        """
        try:
            # 히스토리 포맷팅 (최근 5턴만, 총 10개 메시지)
            if conversation_history:
                # 최근 10개 메시지만 유지
                history = conversation_history[-(self.max_history_turns * 2):]
                history_text = "\n".join([
                    f"{msg['role'].capitalize()}: {msg['content']}"
                    for msg in history
                ])
            else:
                history_text = "(No previous conversation)"

            # 첫 질문인지 추가 질문인지 판단
            is_first_question = not conversation_history or len(conversation_history) == 0

            # 현재 질문 컨텍스트 추가
            question_context = ""
            if current_question:
                question_text = current_question.get("question_text", "")
                question_text_ko = current_question.get("question_text_ko", "")
                question_context = f"""
현재 사용자는 다음 질문에 답변을 준비하고 있습니다:
- 영문: "{question_text}"
- 한글: "{question_text_ko}"

사용자가 "답변 추천해줘", "어떻게 답하면 돼?" 같은 요청을 하면,
위 질문에 대한 답변을 추천해주세요.
"""

            # 프롬프트 구성
            prompt = IT_CHATBOT_PROMPT.format(
                question_context=question_context,
                conversation_history=history_text,
                user_message=user_message,
                is_first_question="true" if is_first_question else "false"
            )

            logger.info("💬 [IT 챗봇] LLM 호출 중...")
            logger.debug(f"User message: {user_message[:100]}...")

            # LLM 호출
            response = await self.llm.invoke(prompt)
            response_text = response if isinstance(response, str) else str(response)

            # 응답 정리 (앞뒤 공백 제거)
            response_text = response_text.strip()

            logger.info(f"✅ [챗봇 응답 생성 완료] {response_text[:60]}...")

            return response_text

        except Exception as e:
            logger.error(f"Chatbot response generation failed: {e}", exc_info=True)
            return "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요."

    async def get_response_stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        챗봇 응답 스트리밍 생성 (토큰 단위)

        Args:
            user_message: 사용자 질문
            conversation_history: 대화 히스토리

        Yields:
            각 토큰 문자열
        """
        try:
            # 히스토리 포맷팅
            if conversation_history:
                history = conversation_history[-(self.max_history_turns * 2):]
                history_text = "\n".join([
                    f"{msg['role'].capitalize()}: {msg['content']}"
                    for msg in history
                ])
            else:
                history_text = "(No previous conversation)"

            # 프롬프트 구성
            prompt = IT_CHATBOT_PROMPT.format(
                conversation_history=history_text,
                user_message=user_message
            )

            logger.info("💬 [IT 챗봇 스트리밍] LLM 스트리밍 중...")

            # LLM 스트리밍
            if hasattr(self.llm, 'stream'):
                async for token in self.llm.stream(prompt):
                    if token and token.strip():
                        yield token
            else:
                # 스트리밍 미지원 시 일반 호출 후 단어 단위로 반환
                response = await self.llm.invoke(prompt)
                words = response.split()
                for word in words:
                    if word.strip():
                        yield word + " "

            logger.info("✅ [챗봇 스트리밍 완료]")

        except Exception as e:
            logger.error(f"Chatbot streaming failed: {e}", exc_info=True)
            yield "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요."
