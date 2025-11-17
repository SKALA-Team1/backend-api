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

        role_localized = {
            "Project Manager": "Project Manager",
            "Tech Lead": "Tech Lead",
            "QA Engineer": "QA Engineer"
        }

        topic_localized = {
            "overview": "Overview",
            "detail": "Detail"
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

                IMPORTANT: You MUST provide exactly 3 questions. Not 2, not 4, but exactly 3.

                The questions should:
                - Match the {ai_role}'s perspective ({role_guidance.get(ai_role, '')})
                - Be appropriate for the {topic_type} type:
                  - overview: broad, high-level questions
                  - detail: specific, technical questions
                - Help the user practice professional English conversation
                - Craft a distinctive title that:
                  - Names the {ai_role}'s perspective explicitly
                  - Highlights a concrete aspect of "{situation}" (specific metric, component, risk, or KPI)
                  - Signals whether this is an overview vs detail conversation
                  - Avoids generic phrases like "Discussion" or "Deep Dive" unless paired with unique detail
                  - Sounds like a real meeting agenda item, not a template
                - Language requirements:
                  - Provide the title in English.
                  - If you add any extra descriptive fields, they must also be written in English
                  - The three fixedQuestions must remain in English to let the learner practice English speaking

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
                        'content': 'You are a helpful assistant that creates English learning scenarios. Always respond with valid JSON and provide exactly 3 questions.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                format='json',
                options={
                    'temperature': 0.3  # 더 일관된 출력을 위해 낮은 temperature
                }
            )

            # 응답 파싱
            response_text = response['message']['content']
            response_data = json.loads(response_text)

            title = response_data.get("title", "")
            questions = response_data.get("fixedQuestions", [])

            # title 정리 (Unicode 문제 방지)
            if not title:
                localized_role = role_localized.get(ai_role, "AI Partner")
                depth_label = topic_localized.get(topic_type, "Discussion")
                title = f"{localized_role} {depth_label} Discussion"

            # title을 안전하게 처리
            title = str(title).strip()[:200]

            return {
                "title": title,
                "fixedQuestions": questions  # 검증은 slack_scenario_service에서 수행
            }

        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Failed to generate scenario for {ai_role}/{topic_type}: {e}")
            # 기본값 반환
            localized_role = role_localized.get(ai_role, "AI Partner")
            depth_label = topic_localized.get(topic_type, "Discussion")

            return {
                "title": f"{localized_role} {depth_label} Discussion",
                "fixedQuestions": [
                    f"What's your perspective on this as a {my_role}?",
                    "Can you elaborate on that?",
                    "What would be your recommended approach?"
                ]
            }

    async def summarize_messages(
        self,
        messages: List[str],
        perspective: str
    ) -> str:
        """
        Summarize a subset of Slack messages in English.
        """
        if not messages:
            return "No relevant messages."

        perspective_label = "user" if perspective == "user" else "counterpart"
        joined_messages = "\n".join(f"- {message}" for message in messages)

        prompt = f"""Summarize the following Slack messages from the {perspective_label}'s perspective.

                - Write 1-2 concise English sentences.
                - Focus on the key objectives or concerns mentioned.

                Messages:
                {joined_messages}

                Return only the English summary sentences."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that summarizes Slack conversations in concise English.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            return response['message']['content'].strip()
        except Exception as error:
            logger.error(f"Failed to summarize messages for {perspective}: {error}")
            return "Summary could not be generated."

    async def build_fixed_questions(
        self,
        user_summary: str,
        counterpart_summary: str
    ) -> List[str]:
        """
        Build exactly three English questions with specific roles for conversation flow.

        Question roles:
        - Question 1 (Turn 1): Conversation starter - greeting, introduction, opening question
        - Question 2 (Turn 5): Transition - topic shift, deeper discussion
        - Question 3 (Turn 10): Wrap-up - summary, next steps, closing
        """
        prompt = f"""You are crafting English practice questions for a professional Slack conversation.

                Use the following summaries to understand each perspective:

                User summary:
                {user_summary}

                Counterpart summary:
                {counterpart_summary}

                IMPORTANT: Generate exactly 3 questions with SPECIFIC ROLES:

                Question 1 (Turn 1 - Conversation Starter):
                - Start the conversation naturally with a greeting or introduction
                - Ask an opening question to set the context
                - Example: "Hi! Can you tell me about main problem of today's issue"

                Question 2 (Turn 5 - Transition & Deepening):
                - Transition to a deeper or different aspect of the topic
                - Shift focus to more specific or technical details
                - Example: "That's interesting. How do you plan to address the technical challenges?"

                Question 3 (Turn 10 - Wrap-up & Closure):
                - Summarize key points or ask for next steps
                - Provide closure to the conversation
                - Example: "Before we wrap up, what are the key action items you'll focus on?"

                Requirements:
                - Each question must match its designated role
                - Reflect the priorities evident in BOTH summaries
                - Avoid yes/no questions
                - Use professional, natural English

                Return ONLY a JSON array of 3 question strings in order [starter, transition, wrap-up]."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'Always respond with a JSON array of exactly 3 English questions.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                format='json'
            )
            response_text = response['message']['content']
            questions = json.loads(response_text)

            if isinstance(questions, dict) and 'questions' in questions:
                questions = questions['questions']
            elif not isinstance(questions, list):
                raise ValueError("Expected a JSON array of strings.")

            normalized: List[str] = []
            for question in questions:
                if isinstance(question, str):
                    normalized.append(question.strip())

            if len(normalized) != 3:
                raise ValueError(f"Expected 3 questions, got {len(normalized)}")

            return normalized
        except Exception as error:
            logger.error(f"Failed to build fixed questions: {error}")
            return [
                "Could you walk me through your current thinking?",
                "Where do you need the most support right now?",
                "What is the next concrete step you plan to take?"
            ]

    async def generate_additional_questions(
        self,
        existing_questions: List[str],
        count: int,
        my_role: str,
        situation: str,
        ai_role: str,
        topic_type: str
    ) -> List[str]:
        """
        기존 질문들을 참고하여 추가 질문을 생성합니다.

        Args:
            existing_questions: 이미 생성된 질문 목록
            count: 추가로 필요한 질문 개수
            my_role: 사용자의 역할
            situation: 대화 주제/상황
            ai_role: AI 역할
            topic_type: 토픽 타입 (overview, detail)

        Returns:
            추가 생성된 질문 목록
        """
        role_guidance = {
            "Project Manager": "planning, timeline, resources, business impact",
            "Tech Lead": "architecture, design patterns, implementation details",
            "QA Engineer": "testing strategy, quality assurance, edge cases"
        }

        existing_text = "\n".join([f"- {q}" for q in existing_questions])

        prompt = f"""You are creating English conversation practice questions.

                Context:
                - User's role: {my_role}
                - Conversation topic: {situation}
                - AI conversation partner: {ai_role}
                - Scenario depth: {topic_type}
                
                Already generated questions:
                {existing_text}
                
                Generate {count} additional question(s) that:
                - Complement the existing questions (don't repeat similar topics)
                - Match the {ai_role}'s perspective ({role_guidance.get(ai_role, '')})
                - Are appropriate for {topic_type} type conversation
                - Help the user practice professional English
                
                Return ONLY a JSON array of {count} question string(s):
                ["question 1"] if count is 1
                ["question 1", "question 2"] if count is 2
                etc.
                """

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant. Always respond with valid JSON array of strings.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                format='json',
                options={
                    'temperature': 0.3
                }
            )

            response_text = response['message']['content']
            questions = json.loads(response_text)

            # 배열이 아닌 경우 처리
            if isinstance(questions, dict) and 'questions' in questions:
                questions = questions['questions']
            elif not isinstance(questions, list):
                questions = [str(questions)]

            # 문자열로 정규화
            normalized = []
            for q in questions:
                if isinstance(q, str):
                    normalized.append(q.strip())

            return normalized[:count]

        except Exception as e:
            logger.error(f"Failed to generate additional questions: {e}")
            # 기본 질문 반환
            default = [
                "Can you provide more details about this?",
                "What are the main challenges you foresee?",
                "How do you plan to proceed with this?"
            ]
            return default[:count]
