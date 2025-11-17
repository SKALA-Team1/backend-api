"""
LLM Service
===========
Ollama를 사용하여 대화 분석 및 시나리오 생성을 수행하는 서비스.

역할:
    - Ollama 라이브러리를 통한 LLM 모델 호출
    - 대화 상황(situation) 분석 (myRole은 분석하지 않음)
    - 시나리오 생성 프롬프트 생성 및 실행

의존성:
    - ollama (로컬 또는 원격 Ollama 서버 필요)
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime
import ollama

logger = logging.getLogger(__name__)


class LLMService:
    """Ollama 기반 LLM 서비스"""

    def __init__(self, model_name: str = "llama3.2"):
        """
        Args:
            model_name: 사용할 모델 이름 (예: llama3.2, llama2, mistral)
        """
        self.model_name = model_name

    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """
        Slack 대화를 분석하여 상황(situation)을 파악합니다.

        주의: myRole은 분석하지 않습니다! 요청에서 이미 제공됨.

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
Provide a brief summary in 1-2 sentences.

Example: "Discussing authentication module refactoring priorities and implementation timeline"

Return only the situation description as a string, without any extra formatting."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that analyzes conversations. Provide concise summaries.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )

            # 응답 파싱
            situation = response['message']['content'].strip()

            # 너무 길면 자르기 (2문장 정도로 제한)
            sentences = situation.split('.')
            if len(sentences) > 2:
                situation = '. '.join(sentences[:2]) + '.'

            return situation

        except Exception as e:
            logger.error(f"Failed to analyze situation: {e}")
            # 기본값 반환
            return "Professional workplace discussion"

    async def generate_scenario(
        self,
        my_role: str,
        situation: str,
        ai_role: str,
        topic_type: str
    ) -> Dict[str, Any]:
        """
        특정 AI 역할과 토픽 타입에 대한 시나리오를 생성합니다.

        Args:
            my_role: 사용자의 역할
            situation: 대화 주제/상황
            ai_role: AI 역할 (Project Manager, Tech Lead, QA Engineer)
            topic_type: 토픽 타입 (overview, detail)

        Returns:
            {"title": "...", "fixedQuestions": ["...", "...", "..."]}
        """
        topic_instructions = {
            "overview": "Create a high-level, general discussion scenario",
            "detail": "Create a deep-dive, technical/specific scenario"
        }

        role_guidance = {
            "Project Manager": "planning, timeline, resources, business impact",
            "Tech Lead": "architecture, design patterns, implementation details",
            "QA Engineer": "testing strategy, quality assurance, edge cases"
        }

        prompt = f"""Create an English conversation practice scenario.

Context:
- User's role: {my_role}
- Conversation topic: {situation}
- AI conversation partner: {ai_role}
- Scenario depth: {topic_type}

Instructions:
- {topic_instructions.get(topic_type, '')}

Generate:
1. A descriptive title for this scenario (max 200 characters)
2. Exactly 3 questions that the {ai_role} would naturally ask in this conversation

The questions should:
- Match the {ai_role}'s perspective ({role_guidance.get(ai_role, '')})
- Be appropriate for the {topic_type} type:
  - overview: broad, high-level questions
  - detail: specific, technical questions
- Help the user practice professional English conversation

Return ONLY valid JSON format:
{{
  "title": "...",
  "fixedQuestions": ["question 1", "question 2", "question 3"]
}}"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that creates English learning scenarios. Always respond with valid JSON.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                format='json'
            )

            # 응답 파싱
            response_text = response['message']['content']
            response_data = json.loads(response_text)

            title = response_data.get("title", f"{ai_role} - {topic_type.capitalize()} Discussion")
            questions = response_data.get("fixedQuestions", [])

            return {
                "title": title[:200],  # 최대 200자
                "fixedQuestions": questions
            }

        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Failed to generate scenario for {ai_role}/{topic_type}: {e}")
            # 기본값 반환
            return {
                "title": f"{ai_role} - {topic_type.capitalize()} Discussion",
                "fixedQuestions": [
                    f"What's your perspective on this as a {my_role}?",
                    "Can you elaborate on that?",
                    "What would be your recommended approach?"
                ]
            }
