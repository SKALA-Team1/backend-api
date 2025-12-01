"""
LLM Service Refactored (SOLID 준수)
====================================
기존 LLMService를 4개의 단일 책임 클래스로 분리했습니다.

변경 이유:
- SRP 위반: 기존 LLMService는 526 라인, 14개 메서드
- 4가지 책임 혼재: 대화분석, 시나리오생성, 질문생성, AI응답생성
- 변경 영향도 증가, 테스트 어려움

솔루션:
- 각 책임을 별도 클래스로 분리
- 같은 인터페이스로 통합 (ConversationAnalyzer, ScenarioGenerator 등)
- 테스트 가능, 재사용 가능한 구조

구조:
    ConversationAnalyzerImpl     → 대화 상황 분석만 담당
    ScenarioGeneratorImpl        → 시나리오 생성만 담당
    QuestionGeneratorImpl        → 질문 생성만 담당
    AIResponseGeneratorImpl      → AI 응답 생성만 담당
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, AsyncGenerator, Optional, List

from app.config import settings
from app.roleplaying.services.llm_providers import create_llm_provider

logger = logging.getLogger(__name__)


# ============================================
# ConversationAnalyzerImpl
# ============================================

class ConversationAnalyzerImpl:
    """대화 상황 분석만 담당하는 클래스

    Slack 대화를 분석하여 상황 요약을 생성합니다.
    책임: 대화 분석만
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
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type=settings.FEEDBACK_LLM_PROVIDER
            if settings.FEEDBACK_LLM_PROVIDER == "ollama"
            else "openai",
            api_key=self.api_key if settings.FEEDBACK_LLM_PROVIDER != "ollama" else None,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL if settings.FEEDBACK_LLM_PROVIDER == "ollama" else None,
            temperature=self.temperature
        )

        logger.info(f"ConversationAnalyzerImpl initialized with {self.model_name}")

    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """
        대화 상황 분석

        Args:
            messages: 사용자-AI 메시지 리스트
            my_role: 사용자의 역할 (예: 'Software Engineer')
            conversation_date: 대화 날짜

        Returns:
            상황 분석 결과 텍스트
        """
        try:
            # 메시지 포맷팅
            formatted_messages = []
            for msg in messages:
                sender = msg.get("senderName", "Unknown")
                text = msg.get("text", "")
                formatted_messages.append(f"{sender}: {text}")

            conversation_text = "\n".join(formatted_messages)

            prompt = f"""
분석할 대화:
{conversation_text}

역할: {my_role}
날짜: {conversation_date}

위 대화의 핵심 상황을 2-3문장으로 간단히 분석해주세요.
주요 주제와 상황을 파악하는 것이 목적입니다.
"""

            logger.info("🔵 [대화 분석] LLM 호출 중...")
            situation = await self.llm.invoke(prompt)
            situation = situation.strip()

            logger.info(f"✅ [대화 분석 완료] {situation[:100]}...")
            return situation

        except Exception as e:
            logger.error(f"Conversation analysis failed: {e}", exc_info=True)
            return "Unable to analyze conversation"


# ============================================
# ScenarioGeneratorImpl
# ============================================

class ScenarioGeneratorImpl:
    """시나리오 생성만 담당하는 클래스

    상황 기반으로 학습 시나리오를 생성합니다.
    책임: 시나리오 생성만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        시나리오 생성기 초기화

        Args:
            api_key: OpenAI API 키
            model_name: 모델명
            temperature: 창의성 레벨 (기본값: 0.7)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"ScenarioGeneratorImpl initialized with {self.model_name}")

    async def generate_scenario_from_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> Dict[str, Any]:
        """
        프롬프트 기반 시나리오 생성

        Returns:
            {
                "opening_question": str,
                "questions": [str, str, str],  # 정확히 3개
                "context": str
            }
        """
        try:
            prompt = f"""
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황에서 영어 연습을 위한 시나리오를 생성해주세요.

JSON 형식으로 다음을 포함해주세요:
1. opening_question: 대화 시작 질문
2. questions: 정확히 3개의 follow-up 질문 (배열)
3. context: 시나리오 배경 설명

응답은 유효한 JSON만 포함하세요.
"""

            logger.info("🟡 [시나리오 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # JSON 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # questions 정규화 (정확히 3개)
                questions = result.get("questions", [])
                if not isinstance(questions, list):
                    questions = [questions]
                questions = questions[:3]  # 최대 3개
                while len(questions) < 3:
                    questions.append(f"Tell me more about {ai_role.lower()}")

                result["questions"] = questions

                logger.info(f"✅ [시나리오 생성 완료] {len(questions)} 질문 생성")
                return result

            # 폴백: 기본 시나리오
            logger.warning("Failed to parse scenario JSON, returning default")
            return {
                "opening_question": f"Hello, I'm a {ai_role}. How can I help you today?",
                "questions": [
                    "Can you tell me more about your project?",
                    "What are your main concerns?",
                    "How do you plan to move forward?"
                ],
                "context": situation
            }

        except Exception as e:
            logger.error(f"Scenario generation failed: {e}", exc_info=True)
            return {
                "opening_question": "What would you like to discuss?",
                "questions": [
                    "Can you provide more details?",
                    "What's your perspective?",
                    "How can we solve this?"
                ],
                "context": "Unable to analyze situation"
            }

    async def generate_scenario_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 시나리오 생성"""
        # LangChain의 스트리밍 API가 필요하면 구현
        # 현재는 일반 버전 사용
        result = await self.generate_scenario_from_prompt(situation, my_role, ai_role)
        yield json.dumps(result, ensure_ascii=False)


# ============================================
# QuestionGeneratorImpl
# ============================================

class QuestionGeneratorImpl:
    """질문 생성만 담당하는 클래스

    대화 히스토리 기반으로 다음 질문을 생성합니다.
    책임: 질문 생성만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """질문 생성기 초기화"""
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"QuestionGeneratorImpl initialized with {self.model_name}")

    async def generate_next_question(
        self,
        situation: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        다음 질문 생성

        Args:
            situation: 시나리오 상황
            conversation_history: 이전 대화 히스토리

        Returns:
            생성된 질문
        """
        try:
            # 대화 히스토리 포맷팅
            history_text = ""
            for msg in conversation_history[-4:]:  # 최근 2턴만 포함
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                history_text += f"{speaker}: {text}\n"

            prompt = f"""
상황: {situation}

대화 히스토리:
{history_text}

자연스러운 follow-up 질문을 한 개 생성해주세요.
질문만 출력하고 다른 설명은 포함하지 마세요.
"""

            logger.info("🟢 [다음 질문 생성] LLM 호출 중...")
            question = await self.llm.invoke(prompt)
            question = question.strip()

            logger.info(f"✅ [다음 질문 생성 완료] {question[:80]}...")
            return question

        except Exception as e:
            logger.error(f"Next question generation failed: {e}", exc_info=True)
            return "Could you tell me more about that?"

    async def generate_followup_question(self, prompt: str) -> str:
        """Follow-up 질문 생성"""
        try:
            logger.info("🟣 [Follow-up 질문 생성] LLM 호출 중...")
            question = await self.llm.invoke(prompt)
            question = question.strip()

            logger.info(f"✅ [Follow-up 질문 생성 완료] {question[:80]}...")
            return question

        except Exception as e:
            logger.error(f"Follow-up question generation failed: {e}", exc_info=True)
            return "What else would you like to discuss?"

    async def generate_followup_question_stream(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 Follow-up 질문 생성"""
        question = await self.generate_followup_question(prompt)
        # 단어 단위로 스트리밍
        words = question.split()
        for word in words:
            yield word + " "


# ============================================
# AIResponseGeneratorImpl
# ============================================

class AIResponseGeneratorImpl:
    """AI 응답 생성만 담당하는 클래스

    시나리오 기반으로 AI의 응답을 생성합니다.
    책임: AI 응답 생성만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """AI 응답 생성기 초기화"""
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_AI_RESPONSE
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"AIResponseGeneratorImpl initialized with {self.model_name}")

    async def generate_ai_response(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        AI 응답 생성

        Args:
            situation: 시나리오 상황
            my_role: 사용자 역할
            ai_role: AI 역할
            conversation_history: 이전 대화 히스토리

        Returns:
            AI 응답
        """
        try:
            # 대화 히스토리 포맷팅
            history_text = ""
            for msg in conversation_history[-4:]:
                speaker = msg.get("speaker", "Unknown")
                text = msg.get("text", "")
                history_text += f"{speaker}: {text}\n"

            prompt = f"""
역할 설정:
- 당신은 {ai_role}입니다.
- 상대방은 {my_role}입니다.

상황: {situation}

대화:
{history_text}

{my_role}의 발언에 자연스럽게 응답하세요.
전문적이고 도움이 되는 응답을 작성해주세요.
"""

            logger.info("🔵 [AI 응답 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)
            response = response.strip()

            logger.info(f"✅ [AI 응답 생성 완료] {response[:80]}...")
            return response

        except Exception as e:
            logger.error(f"AI response generation failed: {e}", exc_info=True)
            return "I appreciate your input. Could you clarify further?"

    async def generate_ai_response_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 AI 응답 생성"""
        response = await self.generate_ai_response(
            situation, my_role, ai_role, conversation_history
        )
        # 단어 단위로 스트리밍
        words = response.split()
        for word in words:
            yield word + " "


# ============================================
# MessageSummarizerImpl
# ============================================

class MessageSummarizerImpl:
    """메시지 요약만 담당하는 클래스

    메시지 리스트를 요약합니다.
    책임: 메시지 요약만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3
    ):
        """메시지 요약기 초기화"""
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"MessageSummarizerImpl initialized with {self.model_name}")

    async def summarize_messages(
        self,
        messages: List[str],
        perspective: str
    ) -> str:
        """
        메시지 요약

        Args:
            messages: 요약할 메시지 리스트
            perspective: 관점 ("user" 또는 "counterpart")

        Returns:
            요약된 텍스트
        """
        try:
            if not messages:
                return "No relevant messages."

            messages_text = "\n".join(messages)

            prompt = f"""
다음은 {perspective} 관점의 메시지들입니다:

{messages_text}

위 메시지들을 간단히 요약해주세요. 핵심 내용만 2-3문장으로 정리하세요.
"""

            logger.info(f"📝 [메시지 요약] {perspective} 관점 요약 중...")
            summary = await self.llm.invoke(prompt)
            summary = summary.strip()

            logger.info(f"✅ [메시지 요약 완료] {summary[:80]}...")
            return summary

        except Exception as e:
            logger.error(f"Message summarization failed: {e}", exc_info=True)
            return "Messages could not be summarized."


# ============================================
# FixedQuestionBuilderImpl
# ============================================

class FixedQuestionBuilderImpl:
    """고정 질문 생성만 담당하는 클래스

    메시지 요약을 기반으로 고정 질문을 생성합니다.
    책임: 고정 질문 생성만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """고정 질문 생성기 초기화"""
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"FixedQuestionBuilderImpl initialized with {self.model_name}")

    async def build_fixed_questions(
        self,
        user_summary: str,
        counterpart_summary: str
    ) -> List[str]:
        """
        고정 질문 생성

        Args:
            user_summary: 사용자 메시지 요약
            counterpart_summary: 상대방 메시지 요약

        Returns:
            정확히 3개의 질문 리스트
        """
        try:
            prompt = f"""
사용자 요약: {user_summary}

상대방 요약: {counterpart_summary}

위 대화를 기반으로 영어 연습을 위한 정확히 3개의 follow-up 질문을 생성해주세요.
각 질문은 자연스럽고 실용적이어야 합니다.

JSON 형식으로 다음과 같이 응답하세요:
{{"questions": ["질문1", "질문2", "질문3"]}}

응답은 유효한 JSON만 포함하세요.
"""

            logger.info("❓ [고정 질문 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # JSON 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                questions = result.get("questions", [])

                if isinstance(questions, list) and len(questions) == 3:
                    questions = [q.strip() for q in questions if isinstance(q, str)]
                    if len(questions) == 3:
                        logger.info(f"✅ [고정 질문 생성 완료] 3개 질문 생성")
                        return questions

            # 폴백: 기본 질문 생성
            logger.warning("Failed to parse questions JSON, returning default")
            return [
                "Can you walk me through this from your perspective?",
                "What are the key blockers you're facing?",
                "How would you like to move forward?"
            ]

        except Exception as e:
            logger.error(f"Fixed question building failed: {e}", exc_info=True)
            return [
                "Can you provide more context?",
                "What's your main concern?",
                "How can we address this?"
            ]


# ============================================
# ScenarioEnhancerImpl
# ============================================

class ScenarioEnhancerImpl:
    """시나리오 강화만 담당하는 클래스

    사용자 입력을 구체화하고 제목 생성, 질문 생성합니다.
    책임: 프롬프트 기반 시나리오 생성만
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """시나리오 강화기 초기화"""
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_QUESTION_GENERATION
        self.temperature = temperature

        self.llm = create_llm_provider(
            provider_type="openai" if self.api_key else "ollama",
            api_key=self.api_key,
            model_name=self.model_name,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=self.temperature
        )

        logger.info(f"ScenarioEnhancerImpl initialized with {self.model_name}")

    async def enhance_situation(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        상황 구체화

        Args:
            situation: 사용자 입력 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할
            context: 과거 시나리오 컨텍스트 (선택사항)

        Returns:
            구체화된 상황 텍스트
        """
        try:
            context_text = ""
            if context:
                context_text = "\n과거 시나리오 참고:\n"
                for scenario in context[:3]:  # 최근 3개만
                    situation_text = scenario.get("situation", "")
                    if situation_text:
                        context_text += f"- {situation_text}\n"

            prompt = f"""
사용자 역할: {my_role}
AI 역할: {ai_role}

사용자 입력: {situation}

{context_text}

위 정보를 바탕으로 더 구체적인 롤플레이 상황을 만들어주세요.
2-3문장으로 자연스럽고 실무적인 상황을 작성해주세요.
"""

            logger.info("🎬 [상황 구체화] LLM 호출 중...")
            enhanced = await self.llm.invoke(prompt)
            enhanced = enhanced.strip()

            logger.info(f"✅ [상황 구체화 완료] {enhanced[:80]}...")
            return enhanced

        except Exception as e:
            logger.error(f"Situation enhancement failed: {e}", exc_info=True)
            return situation  # 실패 시 원본 반환

    async def generate_title(
        self,
        situation: str,
        ai_role: str,
        my_role: str
    ) -> str:
        """
        시나리오 제목 생성

        Args:
            situation: 상황 텍스트
            ai_role: AI의 역할
            my_role: 사용자의 역할

        Returns:
            생성된 제목
        """
        try:
            prompt = f"""
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황의 핵심을 담은 짧은 제목(5-10단어)을 만들어주세요.
제목만 출력하고 다른 설명은 포함하지 마세요.
"""

            logger.info("📝 [제목 생성] LLM 호출 중...")
            title = await self.llm.invoke(prompt)
            title = title.strip()

            logger.info(f"✅ [제목 생성 완료] {title}")
            return title

        except Exception as e:
            logger.error(f"Title generation failed: {e}", exc_info=True)
            return "Roleplay Scenario"  # 실패 시 기본값

    async def generate_prompt_questions(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> List[str]:
        """
        프롬프트 기반 고정 질문 생성

        Args:
            situation: 상황 텍스트
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            정확히 3개의 질문 리스트
        """
        try:
            prompt = f"""
상황: {situation}
사용자 역할: {my_role}
AI 역할: {ai_role}

위 상황에서 영어 연습을 위한 정확히 3개의 질문을 생성해주세요.
1. 대화 시작 질문
2. 중간 심화 질문
3. 마무리 질문

JSON 형식으로 다음과 같이 응답하세요:
{{"questions": ["질문1", "질문2", "질문3"]}}

응답은 유효한 JSON만 포함하세요.
"""

            logger.info("❓ [프롬프트 질문 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # JSON 추출
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                questions = result.get("questions", [])

                if isinstance(questions, list) and len(questions) == 3:
                    questions = [q.strip() for q in questions if isinstance(q, str)]
                    if len(questions) == 3:
                        logger.info(f"✅ [프롬프트 질문 생성 완료] 3개 질문 생성")
                        return questions

            # 폴백
            logger.warning("Failed to parse questions JSON, returning default")
            return [
                f"Hi! Could you walk me through your perspective on this as a {ai_role}?",
                f"What are your main concerns or priorities that we should address?",
                f"Before we wrap up, what would be your recommended next steps?"
            ]

        except Exception as e:
            logger.error(f"Prompt question generation failed: {e}", exc_info=True)
            return [
                f"Hi! Could you walk me through your perspective on this as a {ai_role}?",
                f"What are your main concerns or priorities that we should address?",
                f"Before we wrap up, what would be your recommended next steps?"
            ]
