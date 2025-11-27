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
from typing import List, Dict, Any, AsyncGenerator
from datetime import datetime
import asyncio
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

        prompt = f"""Create an English conversation practice scenario.

                Context:
                - User's role: {my_role}
                - Conversation topic: {situation}
                - AI conversation partner: {ai_role}
                - Scenario depth: {topic_type}

                Instructions:
                - {topic_instructions.get(topic_type, '')}

                Generate:
                1. A compact English title for this scenario (max 50 characters) that does NOT mention the user's role ("{my_role}") or the AI role ("{ai_role}"). Focus the wording only on the situation/topic.
                2. Exactly 3 questions that the {ai_role} would naturally ask in this conversation

                IMPORTANT: You MUST provide exactly 3 questions. Not 2, not 4, but exactly 3.

                The questions should:
                - Match the {ai_role}'s perspective ({role_guidance.get(ai_role, '')})
                - Be appropriate for the {topic_type} type:
                  - overview: broad, high-level questions
                  - detail: specific, technical questions
                - Help the user practice professional English conversation
                - Language requirements:
                  - Provide the title in English only.
                  - Keep every question in English and make them concise but natural.

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
                fallback_title = "Key Discussion Points" if topic_type == "overview" else "Focused Detail Review"
                title = fallback_title

            # title을 안전하게 처리
            title = str(title).strip()[:50]

            return {
                "title": title,
                "fixedQuestions": questions  # 검증은 slack_scenario_service에서 수행
            }

        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error(f"Failed to generate scenario for {ai_role}/{topic_type}: {e}")
            # 기본값 반환
            return {
                "title": "Key Discussion Points" if topic_type == "overview" else "Focused Detail Review",
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

    async def generate_followup_question(self, prompt: str) -> str:
        """
        General helper to generate a single conversational follow-up question.

        Args:
            prompt: 이미 구성된 사용자 프롬프트 (역할/히스토리 포함)
        """
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful AI tutor that only outputs one concise English question.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            return response['message']['content'].strip()
        except Exception as error:
            logger.error(f"Failed to generate follow-up question: {error}")
            raise

    async def generate_followup_question_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        스트리밍으로 AI 답변 생성 (청크 단위로 즉시 반환)

        ✅ 진정한 실시간 스트리밍:
        - Ollama의 동기 스트리밍을 executor에서 실행
        - 청크가 생성되는대로 즉시 asyncio.Queue에 추가
        - 메인 루프에서 큐를 모니터링하며 청크를 즉시 yield

        Args:
            prompt: 이미 구성된 사용자 프롬프트 (역할/히스토리 포함)

        Yields:
            청크 단위로 생성된 텍스트 (한 단어 또는 여러 단어) - 실시간
        """
        from asyncio import Queue

        # 비동기 큐 (executor와 메인 루프 간 통신용)
        queue: Queue = Queue()
        stream_error = None

        def _stream_question_to_queue() -> None:
            """
            동기 스트리밍 호출 (executor에서 실행)
            생성되는 청크를 큐에 추가 (논블로킹 방식)
            """
            nonlocal stream_error

            try:
                stream = ollama.chat(
                    model=self.model_name,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You are a helpful AI tutor that only outputs one concise English question.'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    stream=True  # ✅ 스트리밍 활성화
                )

                # 스트림 반복 (executor에서 실행)
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        # ✅ 논블로킹 방식으로 큐에 추가
                        try:
                            queue.put_nowait(content)
                        except Exception as e:
                            logger.warning(f"Failed to put chunk to queue: {e}")

                # 스트림 완료 신호
                queue.put_nowait(None)

            except Exception as error:
                logger.error(f"Failed to generate follow-up question stream: {error}")
                stream_error = error
                queue.put_nowait(None)  # 종료 신호

        try:
            # ✅ executor에서 스트리밍 시작 (논블로킹)
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _stream_question_to_queue)

            # ✅ 큐에서 청크를 꺼내며 즉시 yield
            while True:
                try:
                    # 타임아웃 설정으로 무한 대기 방지 (30초)
                    chunk = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning("Stream timeout: no data received for 30 seconds")
                    break

                # None은 스트림 완료 신호
                if chunk is None:
                    break

                # 청크를 즉시 yield (블로킹 없음)
                yield chunk

            # 에러 확인
            if stream_error:
                raise stream_error

        except Exception as error:
            logger.error(f"Failed to generate follow-up question stream: {error}")
            raise

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

    async def enhance_situation_from_prompt(
        self,
        user_input: str,
        my_role: str,
        ai_role: str,
        context: List[Dict[str, Any]] = None
    ) -> str:
        """
        사용자 입력으로부터 구체화된 상황을 생성합니다.

        Args:
            user_input: 사용자가 입력한 상황 (추상적)
            my_role: 사용자의 역할
            ai_role: AI의 역할
            context: 과거 시나리오 컨텍스트

        Returns:
            구체화된 상황 설명 (1-2문장)
        """
        context_text = ""
        if context:
            context_text = "\n[User's past scenarios context]\n"
            for idx, ctx in enumerate(context[:3], 1):
                situation = ctx.get("situation", "")
                context_text += f"{idx}. {situation}\n"

        prompt = f"""You are an expert at creating detailed business scenarios for English practice in IT companies.
Consider the terminology and conversations used in IT companies when creating roleplay scenarios.
Note: Since this is real-time roleplay, please ensure questions are concise and not overly lengthy.

User's role: {my_role}
AI's role: {ai_role}
Situation provided by user: {user_input}

{context_text}

Based on the above information, please:
1. Expand the user's abstract input into a concrete business situation
2. Clarify the relationship and goals between {my_role} and {ai_role}
3. Write a 1-2 sentence situation description

Example format:
"{my_role} discussing {{detail}} related to project with {ai_role} for {{objective}}"

Response: Return only the enhanced situation description (no other text)"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are an expert at creating detailed business scenarios for English practice.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            situation = response['message']['content'].strip()

            # 너무 길면 자르기
            sentences = situation.split('.')
            if len(sentences) > 2:
                situation = '. '.join(sentences[:2]) + '.'

            return situation

        except Exception as error:
            logger.error(f"Failed to enhance situation: {error}")
            raise

    async def generate_title_for_prompt(
        self,
        situation: str,
        ai_role: str,
        topic_type: str,
        my_role: str
    ) -> str:
        """
        시나리오 제목을 생성합니다.

        Args:
            situation: 구체화된 상황
            ai_role: AI의 역할
            topic_type: 토픽 타입 (direct, overview, detail)
            my_role: 사용자의 역할 (제거 대상)

        Returns:
            생성된 시나리오 제목 (최대 50자)
        """
        prompt = f"""You are creating an engaging title for an English roleplay scenario.

Situation: {situation}
AI role: {ai_role}
Topic type: {topic_type}

Generate a concise English title (max 50 characters) that:
- Focuses only on the situation/topic details
- Does NOT mention the user's role ("{my_role}") or the AI role ("{ai_role}")
- Sounds like a real meeting agenda item
- Uses only English words

Response: Return only the title without any quotes or special formatting (no other text)."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are an expert at creating engaging titles for roleplay scenarios. Always return the title without quotes or asterisks.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            title = response['message']['content'].strip()

            # 따옴표 제거
            title = title.strip('"\'')

            # 길이 제한
            if len(title) > 50:
                title = title[:50].rstrip()

            return title

        except Exception as error:
            logger.error(f"Failed to generate title: {error}")
            raise

    async def generate_fixed_questions_for_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> List[str]:
        """
        프롬프트 기반 시나리오용 고정 질문을 생성합니다. (정확히 3개)

        Slack 기반과 동일한 역할의 질문:
        - Question 1 (Turn 1): Conversation Starter
        - Question 2 (Turn 5): Transition & Deepening
        - Question 3 (Turn 10): Wrap-up & Closure

        Args:
            situation: 구체화된 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            정확히 3개의 고정 질문

        Raises:
            ValueError: 질문 생성 실패
        """
        prompt = f"""You are creating fixed questions for an English roleplay scenario.

Situation: {situation}
User's role: {my_role}
AI's role: {ai_role}

Generate exactly 3 DIFFERENT questions that {ai_role} would naturally ask {my_role} in this situation.

IMPORTANT - Each question must have a SPECIFIC ROLE:

Question 1 (Turn 1 - Conversation Starter):
- Start the conversation naturally with a greeting or introduction
- Ask an opening question to set the context and build rapport

Question 2 (Turn 5 - Transition & Deepening):
- Transition to a deeper or different aspect of the topic
- Shift focus to more specific or technical details related to the situation

Question 3 (Turn 10 - Wrap-up & Closure):
- Ask about next steps, action items, or how to move forward
- Provide closure to the conversation

Requirements:
- Each question must match its designated role and turn number
- Create ORIGINAL questions specific to this situation, not generic questions
- Reflect both {my_role} and {ai_role} perspectives
- Avoid yes/no questions
- Use professional, natural English

Return ONLY a JSON array of exactly 3 question strings in this format:
["question 1 text", "question 2 text", "question 3 text"]"""

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
            logger.error(f"Failed to generate fixed questions for prompt: {error}")
            raise
