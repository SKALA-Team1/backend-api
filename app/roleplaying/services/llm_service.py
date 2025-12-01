"""
LLM Service
===========
OpenAI를 사용하여 대화 분석 및 시나리오 생성을 수행하는 서비스.

역할:
    - OpenAI API를 통한 LLM 모델 호출
    - 대화 상황(situation) 분석 (myRole은 분석하지 않음)
    - 시나리오 생성 프롬프트 생성 및 실행
    - LangSmith를 통한 자동 토큰 사용량 추적

의존성:
    - langchain-openai (OpenAI API 클라이언트)
"""

import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime

from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """OpenAI 기반 LLM 서비스"""

    def __init__(self, purpose: str = "ai_response"):
        """
        Args:
            purpose: 사용 목적
                - "question_generation": 질문 생성 (OPENAI_MODEL_QUESTION_GENERATION)
                - "ai_response": AI 응답 생성 (OPENAI_MODEL_AI_RESPONSE)
                - "analysis": 대화 분석 (OPENAI_MODEL_QUESTION_GENERATION)
        """
        self.purpose = purpose
        self.llm = self._initialize_llm()
        logger.info(f"LLMService initialized for: {purpose}, model: {self.model_name}")

    def _initialize_llm(self) -> ChatOpenAI:
        """목적에 맞는 OpenAI 모델 초기화"""
        if self.purpose == "question_generation":
            self.model_name = settings.OPENAI_MODEL_QUESTION_GENERATION
        elif self.purpose == "ai_response":
            self.model_name = settings.OPENAI_MODEL_AI_RESPONSE
        elif self.purpose == "analysis":
            self.model_name = settings.OPENAI_MODEL_QUESTION_GENERATION
        else:
            self.model_name = settings.OPENAI_MODEL_AI_RESPONSE

        return ChatOpenAI(
            model=self.model_name,
            api_key=settings.openai_api_key,
            temperature=0.7
        )

    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """
        Slack 대화를 분석하여 상황(situation)을 파악합니다.

        Args:
            messages: Slack 메시지 목록
            my_role: 사용자의 역할 (컨텍스트용)
            conversation_date: 대화 날짜

        Returns:
            situation (1-2 문장 요약)
        """
        # 메시지를 읽기 쉬운 형태로 포맷팅
        formatted_messages = []
        for msg in messages:
            timestamp = msg.get("timestamp", "")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            sender = msg.get("senderName", "Unknown")
            text = msg.get("text", "")
            formatted_messages.append(f"[{timestamp}] {sender}: {text}")

        messages_text = "\n".join(formatted_messages)

        prompt = f"""You are analyzing a Slack conversation to create English practice scenarios.

The user's role is: {my_role}

Here are the messages from {conversation_date}:
{messages_text}

Based on this conversation, what is the main topic or situation being discussed?
Provide a brief summary in 1-2 sentences written in English.

Example: "Discussing authentication module refactoring priorities and implementation timeline"

Return only the English situation description as a plain string, without any extra formatting or translation."""

        try:
            logger.info("📊 [대화 상황 분석] OpenAI 호출 중...")

            # 비동기 호출
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            situation = response.content if hasattr(response, 'content') else str(response)
            situation = situation.strip()

            # 너무 길면 자르기 (2문장 정도로 제한)
            sentences = situation.split('.')
            if len(sentences) > 2:
                situation = '. '.join(sentences[:2]) + '.'

            logger.info(f"✅ [대화 상황 분석 완료] {situation[:100]}...")
            return situation

        except Exception as e:
            logger.error(f"Situation analysis failed: {e}", exc_info=True)
            return "Unable to analyze conversation situation"

    async def generate_scenario_from_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> Dict[str, Any]:
        """
        상황 기반으로 영어 학습 시나리오를 생성합니다.

        Args:
            situation: 분석된 대화 상황
            my_role: 사용자의 역할 (예: "Software Engineer")
            ai_role: AI의 역할 (예: "Project Manager")

        Returns:
            {
                "situation": str,
                "my_role": str,
                "ai_role": str,
                "opening_question": str,
                "questions": List[str]
            }
        """
        prompt = f"""Generate 3 English practice questions based on the following scenario:

Situation: {situation}
User's Role: {my_role}
AI's Role: {ai_role}

Requirements:
1. Questions should be realistic and relevant to the situation
2. Questions should encourage detailed responses
3. Each question should help the user practice English conversation
4. Questions should be different from each other (covering different aspects)

Return ONLY valid JSON with this exact structure (no extra text):
{{
    "opening_question": "The first question to start the conversation (most important, ask it first)",
    "questions": [
        "Question 2 (follow-up or related topic)",
        "Question 3 (different angle or deeper exploration)",
        "Question 4 (summary or reflection question)"
    ]
}}

Important: Ensure the JSON is valid and parseable."""

        try:
            logger.info("🔄 [시나리오 생성] OpenAI 호출 중...")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            response_text = response.content if hasattr(response, 'content') else str(response)

            # JSON 파싱
            json_match = json.loads(response_text)

            logger.info(f"✅ [시나리오 생성 완료] Opening: {json_match.get('opening_question', '')[:80]}...")

            return {
                "situation": situation,
                "my_role": my_role,
                "ai_role": ai_role,
                "opening_question": json_match.get("opening_question", ""),
                "questions": json_match.get("questions", [])
            }

        except Exception as e:
            logger.error(f"Scenario generation failed: {e}", exc_info=True)
            return {
                "situation": situation,
                "my_role": my_role,
                "ai_role": ai_role,
                "opening_question": "What would you like to discuss?",
                "questions": ["Can you tell me more?", "How does that relate to your role?", "What's the next step?"]
            }

    async def generate_next_question(
        self,
        situation: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        대화 히스토리를 기반으로 다음 질문을 생성합니다.

        Args:
            situation: 학습 상황
            conversation_history: 지금까지의 대화 내용

        Returns:
            다음 질문
        """
        # 대화 히스토리 포맷팅
        history_text = ""
        for exchange in conversation_history[-3:]:  # 최근 3개만
            history_text += f"User: {exchange.get('user', '')}\nAI: {exchange.get('ai', '')}\n"

        prompt = f"""Based on the following conversation history in an English learning scenario, generate a natural follow-up question.

Scenario: {situation}

Conversation so far:
{history_text}

Requirements:
1. Question should naturally follow from the last user response
2. Question should help deepen the conversation
3. Question should encourage detailed, natural English responses
4. Keep it concise (1-2 sentences)

Return ONLY the question text, nothing else."""

        try:
            logger.info("❓ [다음 질문 생성] OpenAI 호출 중...")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            question = response.content if hasattr(response, 'content') else str(response)
            question = question.strip()

            logger.info(f"✅ [다음 질문 생성 완료] {question[:80]}...")
            return question

        except Exception as e:
            logger.error(f"Next question generation failed: {e}", exc_info=True)
            return "Can you elaborate on that?"

    async def generate_followup_question(self, prompt: str) -> str:
        """
        사용자 정의 프롬프트로 follow-up 질문을 생성합니다.
        (ai_tutor_service와의 호환성 유지)

        Args:
            prompt: LLM에 전달할 프롬프트

        Returns:
            생성된 질문
        """
        try:
            logger.info("❓ [Follow-up 질문 생성] OpenAI 호출 중...")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            question = response.content if hasattr(response, 'content') else str(response)
            question = question.strip()

            logger.info(f"✅ [Follow-up 질문 생성 완료] {question[:80]}...")
            return question

        except Exception as e:
            logger.error(f"Follow-up question generation failed: {e}", exc_info=True)
            return "That's interesting. Could you elaborate on that?"

    async def generate_scenario_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> AsyncGenerator[str, None]:
        """
        시나리오를 스트리밍으로 생성합니다.

        Args:
            situation: 대화 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Yields:
            JSON 청크 (스트리밍)
        """
        prompt = f"""Generate 3 English practice questions based on the following scenario:

Situation: {situation}
User's Role: {my_role}
AI's Role: {ai_role}

Requirements:
1. Questions should be realistic and relevant to the situation
2. Questions should encourage detailed responses
3. Each question should help the user practice English conversation
4. Questions should be different from each other

Return ONLY valid JSON with this exact structure:
{{
    "opening_question": "The first question to start the conversation",
    "questions": [
        "Question 2",
        "Question 3",
        "Question 4"
    ]
}}"""

        try:
            logger.info("🔄 [시나리오 스트리밍 생성] OpenAI 호출 중...")

            # OpenAI 스트리밍 호출
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            response_text = response.content if hasattr(response, 'content') else str(response)

            # 청크 단위로 반환
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                yield response_text[i:i + chunk_size]
                await asyncio.sleep(0)  # 이벤트 루프에 양보

            logger.info("✅ [시나리오 스트리밍 생성 완료]")

        except Exception as e:
            logger.error(f"Scenario streaming generation failed: {e}", exc_info=True)
            yield json.dumps({
                "opening_question": "What would you like to discuss?",
                "questions": ["Can you tell me more?", "How does that relate to your role?", "What's the next step?"]
            })

    async def generate_ai_response(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        AI 역할을 수행하여 응답을 생성합니다.

        Args:
            situation: 학습 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할
            conversation_history: 대화 내용

        Returns:
            AI의 응답
        """
        # 대화 히스토리 포맷팅
        history_text = ""
        for exchange in conversation_history:
            if isinstance(exchange, dict):
                user_text = exchange.get('user', exchange.get('text', ''))
                ai_text = exchange.get('ai', '')
                history_text += f"{my_role}: {user_text}\n{ai_role}: {ai_text}\n"

        prompt = f"""You are playing the role of {ai_role} in an English conversation practice scenario.

Scenario: {situation}
Your Role: {ai_role}
User's Role: {my_role}

Conversation so far:
{history_text}

{my_role}'s last response: {conversation_history[-1].get('text', conversation_history[-1].get('user', '')) if conversation_history else '[waiting for user]'}

Requirements:
1. Respond naturally as {ai_role} in English
2. Keep responses concise but meaningful (2-4 sentences)
3. Ask a follow-up question or continue the conversation naturally
4. Use professional but friendly language
5. Stay in character as {ai_role}

Respond with ONLY the {ai_role}'s response, no labels or formatting."""

        try:
            logger.info(f"💬 [AI 응답 생성 중] 역할: {ai_role}")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            ai_response = response.content if hasattr(response, 'content') else str(response)
            ai_response = ai_response.strip()

            logger.info(f"✅ [AI 응답 생성 완료] {ai_response[:80]}...")
            return ai_response

        except Exception as e:
            logger.error(f"AI response generation failed: {e}", exc_info=True)
            return f"Thank you for that input. Could you elaborate on that a bit more?"

    async def generate_ai_response_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        AI 응답을 스트리밍으로 생성합니다.

        Args:
            situation: 학습 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할
            conversation_history: 대화 내용

        Yields:
            응답 텍스트 청크 (스트리밍)
        """
        # 대화 히스토리 포맷팅
        history_text = ""
        for exchange in conversation_history:
            if isinstance(exchange, dict):
                user_text = exchange.get('user', exchange.get('text', ''))
                ai_text = exchange.get('ai', '')
                history_text += f"{my_role}: {user_text}\n{ai_role}: {ai_text}\n"

        prompt = f"""You are playing the role of {ai_role} in an English conversation practice scenario.

Scenario: {situation}
Your Role: {ai_role}
User's Role: {my_role}

Conversation so far:
{history_text}

{my_role}'s last response: {conversation_history[-1].get('text', conversation_history[-1].get('user', '')) if conversation_history else '[waiting for user]'}

Respond naturally as {ai_role} in English (2-4 sentences). ONLY return the response text."""

        try:
            logger.info(f"💬 [AI 응답 스트리밍 생성] 역할: {ai_role}")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            response_text = response.content if hasattr(response, 'content') else str(response)

            # 청크 단위로 반환
            chunk_size = 20
            for i in range(0, len(response_text), chunk_size):
                yield response_text[i:i + chunk_size]
                await asyncio.sleep(0)

            logger.info("✅ [AI 응답 스트리밍 생성 완료]")

        except Exception as e:
            logger.error(f"AI response streaming generation failed: {e}", exc_info=True)
            yield "Thank you for that input. Could you elaborate on that a bit more?"

    async def generate_followup_question_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        사용자 정의 프롬프트로 follow-up 질문을 스트리밍으로 생성합니다.
        (ai_tutor_service와의 호환성 유지)

        Args:
            prompt: LLM에 전달할 프롬프트

        Yields:
            생성된 질문 청크
        """
        try:
            logger.info("❓ [Follow-up 질문 스트리밍] OpenAI 호출 중...")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self.llm.invoke,
                prompt
            )

            response_text = response.content if hasattr(response, 'content') else str(response)

            # 청크 단위로 반환
            chunk_size = 20
            for i in range(0, len(response_text), chunk_size):
                yield response_text[i:i + chunk_size]
                await asyncio.sleep(0)

            logger.info("✅ [Follow-up 질문 스트리밍 완료]")

        except Exception as e:
            logger.error(f"Follow-up question streaming generation failed: {e}", exc_info=True)
            fallback = "That's interesting. Could you elaborate on that a bit more?"
            yield fallback
