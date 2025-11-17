"""
Slack Scenario Service
=====================
Slack 대화 분석 및 시나리오 생성 비즈니스 로직을 담당하는 서비스.

역할:
    - LLM 서비스를 조율하여 대화 분석 및 시나리오 생성
    - 4개 시나리오 생성 (1 overview + 3 detail per AI role)
    - 최종 응답 DTO 구성

중요:
    - situation만 LLM으로 분석
    - FastAPI는 READ-ONLY (데이터베이스 저장 안 함)

의존성:
    - LLMService
    - Pydantic schemas
"""

import logging
import asyncio
from dataclasses import dataclass
from typing import List, Optional

from app.roleplaying.services.llm_service import LLMService
from app.roleplaying.schemas import (
    AnalysisRequestDto,
    AnalysisResultDto,
    SubjectInfoDto,
    ScenarioInfoDto,
    MessageRole
)


@dataclass
class ConversationSummary:
    my_messages: List[str]
    others_messages: List[str]
    user_summary: str
    counterpart_summary: str

logger = logging.getLogger(__name__)


class SlackScenarioService:
    """Slack 대화 기반 시나리오 생성 서비스"""

    def __init__(self, model_name: str = "llama3.2"):
        """
        Args:
            model_name: Ollama 모델 이름
        """
        self.llm_service = LLMService(model_name=model_name)

    async def analyze_and_generate(
        self,
        request: AnalysisRequestDto,
        conversation_roles: Optional[List[MessageRole]] = None
    ) -> AnalysisResultDto:
        """
        Slack 대화를 분석하고 4개의 시나리오를 생성합니다.

        Args:
            request: 분석 요청 DTO

        Returns:
            분석 결과 DTO (subject + 4 scenarios: 1 overview + 3 detail)
        """
        # Step 1: situation만 분석 (myRole은 요청에서 이미 제공됨)
        logger.info(f"Analyzing conversation for user {request.userId} on {request.conversationDate}")

        if conversation_roles is None:
            conversation_roles = [
                MessageRole(
                    content=msg.text,
                    sender=msg.senderName,
                    mine=False
                )
                for msg in request.messages
            ]

        messages_dict = [msg.model_dump() for msg in request.messages]

        situation = await self.llm_service.analyze_situation(
            messages=messages_dict,
            my_role=request.myRole,
            conversation_date=str(request.conversationDate)
        )

        logger.info(f"Situation analyzed: {situation}")

        # 메시지 요약 (사용자/상대) 선계산
        conversation_summary = await self._build_conversation_summary(conversation_roles)

        # Step 2: 4개 시나리오 생성 (1 overview + 3 detail)
        # 병렬로 생성하여 속도 향상
        scenario_tasks = []

        # 1개의 overview 시나리오 (첫 번째 AI role 사용)
        if request.aiRoles:
            task = self._generate_single_scenario(
                my_role=request.myRole,
                situation=situation,
                ai_role=request.aiRoles[0],  # 첫 번째 AI role 사용
                topic_type="overview",
                summary=conversation_summary
            )
            scenario_tasks.append(task)

        # 3개의 detail 시나리오 (각 AI role별)
        for ai_role in request.aiRoles:
            task = self._generate_single_scenario(
                my_role=request.myRole,
                situation=situation,
                ai_role=ai_role,
                topic_type="detail",
                summary=conversation_summary
            )
            scenario_tasks.append(task)

        logger.info(f"Generating {len(scenario_tasks)} scenarios...")
        scenarios = await asyncio.gather(*scenario_tasks)

        # Step 3: 최종 응답 구성
        result = AnalysisResultDto(
            subject=SubjectInfoDto(
                myRole=request.myRole,  # Echo unchanged
                situation=situation,
                conversationDate=request.conversationDate,
                messageCount=len(request.messages)
            ),
            scenarios=scenarios
        )

        logger.info(f"Analysis complete: {len(scenarios)} scenarios generated")
        return result

    async def _generate_single_scenario(
        self,
        my_role: str,
        situation: str,
        ai_role: str,
        topic_type: str,
        summary: ConversationSummary
    ) -> ScenarioInfoDto:
        """
        단일 시나리오를 생성합니다.

        Args:
            my_role: 사용자 역할
            situation: 대화 상황
            ai_role: AI 역할
            topic_type: 토픽 타입 (overview/detail)

        Returns:
            생성된 시나리오 DTO
        """
        logger.debug(f"Generating scenario: {ai_role} - {topic_type}")

        scenario_data = await self.llm_service.generate_scenario(
            my_role=my_role,
            situation=situation,
            ai_role=ai_role,
            topic_type=topic_type
        )

        base_questions = scenario_data.get("fixedQuestions", [])

        questions = await self._generate_fixed_questions(
            summary=summary,
            my_role=my_role,
            situation=situation,
            ai_role=ai_role,
            topic_type=topic_type,
            fallback_questions=base_questions
        )

        formatted_title = self._format_title(scenario_data.get("title"), ai_role, topic_type)

        return ScenarioInfoDto(
            aiRole=ai_role,
            topicType=topic_type,
            title=formatted_title,
            fixedQuestions=questions
        )

    async def _build_conversation_summary(
        self,
        conversation_roles: List[MessageRole]
    ) -> ConversationSummary:
        """
        Split messages into my vs. others to create separate summaries for the question prompt.
        """
        my_messages = [msg.content for msg in conversation_roles if msg.mine]
        others_messages = [msg.content for msg in conversation_roles if not msg.mine]

        user_summary = await self.llm_service.summarize_messages(
            messages=my_messages,
            perspective="user"
        )
        counterpart_summary = await self.llm_service.summarize_messages(
            messages=others_messages,
            perspective="counterpart"
        )

        return ConversationSummary(
            my_messages=my_messages,
            others_messages=others_messages,
            user_summary=user_summary,
            counterpart_summary=counterpart_summary
        )

    async def _generate_fixed_questions(
        self,
        summary: ConversationSummary,
        my_role: str,
        situation: str,
        ai_role: str,
        topic_type: str,
        fallback_questions: List
    ) -> List[str]:
        """
        Generate fixed questions using the separated summaries. Falls back to the original
        scenario questions or safe defaults if generation fails.
        """
        formatted_user_summary = self._format_summary_text(
            summary=summary.user_summary,
            perspective_label="User summary",
            my_role=my_role,
            ai_role=ai_role,
            topic_type=topic_type,
            situation=situation
        )
        formatted_counterpart_summary = self._format_summary_text(
            summary=summary.counterpart_summary,
            perspective_label="Counterpart summary",
            my_role=my_role,
            ai_role=ai_role,
            topic_type=topic_type,
            situation=situation
        )

        fallback_questions = fallback_questions or []

        try:
            generated_questions = await self.llm_service.build_fixed_questions(
                user_summary=formatted_user_summary,
                counterpart_summary=formatted_counterpart_summary
            )
            return self._normalize_questions(generated_questions)
        except Exception as error:
            logger.error(
                "Failed to build fixed questions for %s/%s: %s",
                ai_role,
                topic_type,
                error
            )
            try:
                return self._normalize_questions(fallback_questions)
            except Exception as fallback_error:
                logger.error(
                    "Fallback questions from scenario invalid for %s/%s: %s",
                    ai_role,
                    topic_type,
                    fallback_error
                )
                return self._default_questions(my_role)

    def _format_summary_text(
        self,
        *,
        summary: str,
        perspective_label: str,
        my_role: str,
        ai_role: str,
        topic_type: str,
        situation: str
    ) -> str:
        """Attach contextual metadata to the summaries so downstream prompts stay role-aware."""
        clean_summary = (summary or "").strip() or "Not enough related messages."
        depth_label = "overview" if topic_type == "overview" else "detail"
        return (
            f"[{perspective_label}] "
            f"[User role: {my_role}] "
            f"[AI role: {ai_role}] "
            f"[Topic type: {depth_label}] "
            f"[Situation: {situation}] "
            f"{clean_summary}"
        )

    def _normalize_questions(self, questions: List) -> List[str]:
        """Ensure fixed questions are returned as plain strings and exactly 3 entries."""
        normalized: List[str] = []

        for question in questions:
            if isinstance(question, dict):
                text = question.get("text")
                if isinstance(text, str):
                    normalized.append(text.strip())
            elif isinstance(question, str):
                normalized.append(question.strip())

        normalized = [q for q in normalized if q]

        if len(normalized) != 3:
            raise ValueError(f"LLM must return exactly 3 questions, got {len(normalized)}")

        return normalized

    def _default_questions(self, my_role: str) -> List[str]:
        """Fallback questions when both generation and scenario-provided questions fail."""
        return [
            f"Can you walk me through this from your perspective as a {my_role}?",
            "What are the blockers you're most concerned about?",
            "How would you like your counterpart to support you next?"
        ]

    def _format_title(self, title: str, ai_role: str, topic_type: str) -> str:
        """
        Post-process LLM titles so each scenario clearly communicates the role perspective and depth.
        This helps the scenario table feel more varied even when the LLM returns similar base phrases.
        """
        base_title = (title or "").strip() or "Scenario"
        role_label_map = {
            "Project Manager": "Project Manager",
            "Tech Lead": "Tech Lead",
            "QA Engineer": "QA Engineer"
        }
        role_label = (role_label_map.get(ai_role) or "AI Partner").strip()
        depth_label = "Overview Sync" if topic_type == "overview" else "Deep Dive Focus"
        prefix = f"{role_label} {depth_label}"

        lowered_base = base_title.lower()
        if role_label.lower() in lowered_base and depth_label.lower() in lowered_base:
            formatted = base_title
        else:
            formatted = f"{prefix} | {base_title}"

        return formatted[:200]
