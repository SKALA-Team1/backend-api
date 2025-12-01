"""
Slack Scenario Service (SOLID 준수)
===================================
Slack 대화 분석 및 시나리오 생성 비즈니스 로직을 담당하는 서비스.

역할:
    - 대화 분석기, 시나리오 생성기, 메시지 요약기, 질문 생성기를 조율
    - 4개 시나리오 생성 (1 overview + 3 detail per AI role)
    - 최종 응답 DTO 구성

중요:
    - situation만 분석
    - FastAPI는 READ-ONLY (데이터베이스 저장 안 함)

의존성:
    - ConversationAnalyzer (대화 분석)
    - ScenarioGenerator (시나리오 생성)
    - MessageSummarizer (메시지 요약)
    - FixedQuestionBuilder (질문 생성)
    - Pydantic schemas
"""

import logging
import asyncio
from dataclasses import dataclass
from typing import List, Optional

from app.roleplaying.services.interfaces import (
    ConversationAnalyzer,
    ScenarioGenerator,
    MessageSummarizer,
    FixedQuestionBuilder
)
from app.roleplaying.services.title_utils import compact_title
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
    """Slack 대화 기반 시나리오 생성 서비스 (SOLID 준수)

    의존성 주입:
        analyzer: ConversationAnalyzer 구현체 (대화 분석)
        generator: ScenarioGenerator 구현체 (시나리오 생성)
        summarizer: MessageSummarizer 구현체 (메시지 요약)
        question_builder: FixedQuestionBuilder 구현체 (질문 생성)
    """

    def __init__(
        self,
        analyzer: ConversationAnalyzer,
        generator: ScenarioGenerator,
        summarizer: MessageSummarizer,
        question_builder: FixedQuestionBuilder
    ):
        """
        Args:
            analyzer: ConversationAnalyzer 구현체
            generator: ScenarioGenerator 구현체
            summarizer: MessageSummarizer 구현체
            question_builder: FixedQuestionBuilder 구현체
        """
        self.analyzer = analyzer
        self.generator = generator
        self.summarizer = summarizer
        self.question_builder = question_builder

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

        situation = await self.analyzer.analyze_situation(
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

        scenario_data = await self.generator.generate_scenario_from_prompt(
            my_role=my_role,
            situation=situation,
            ai_role=ai_role
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

        formatted_title = self._format_title(
            title=scenario_data.get("title"),
            ai_role=ai_role,
            topic_type=topic_type,
            my_role=my_role
        )

        return ScenarioInfoDto(
            aiRole=ai_role,
            topicType=topic_type,
            title=formatted_title,
            fixedQuestions=questions,
            creationType="slack"
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

        user_summary = await self.summarizer.summarize_messages(
            messages=my_messages,
            perspective="user"
        )
        counterpart_summary = await self.summarizer.summarize_messages(
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
            generated_questions = await self.question_builder.build_fixed_questions(
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

    def _format_title(self, *, title: str, ai_role: str, topic_type: str, my_role: str) -> str:
        """Normalize scenario titles to exclude explicit role names and keep them short."""
        fallback = "Focused Overview" if topic_type == "overview" else "Focused Detail"
        banned_phrases = [
            ai_role,
            my_role,
            "Project Manager",
            "Tech Lead",
            "QA Engineer"
        ]
        return compact_title(
            raw_title=title,
            banned_phrases=banned_phrases,
            fallback=fallback,
            max_length=50
        )
