"""
Slack Scenario Service
=====================
Slack 대화 분석 및 시나리오 생성 비즈니스 로직을 담당하는 서비스.

역할:
    - LLM 서비스를 조율하여 대화 분석 및 시나리오 생성
    - 6개 시나리오 생성 (3 AI roles × 2 topic types)
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
from typing import List

from app.roleplaying.services.llm_service import LLMService
from app.roleplaying.schemas import (
    AnalysisRequestDto,
    AnalysisResultDto,
    SubjectInfoDto,
    ScenarioInfoDto,
    SlackMessageDto
)

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
        request: AnalysisRequestDto
    ) -> AnalysisResultDto:
        """
        Slack 대화를 분석하고 6개의 시나리오를 생성합니다.

        Args:
            request: 분석 요청 DTO

        Returns:
            분석 결과 DTO (subject + 6 scenarios)
        """
        # Step 1: situation만 분석 (myRole은 요청에서 이미 제공됨)
        logger.info(f"Analyzing conversation for user {request.userId} on {request.conversationDate}")

        messages_dict = [msg.model_dump() for msg in request.messages]

        situation = await self.llm_service.analyze_situation(
            messages=messages_dict,
            my_role=request.myRole,
            conversation_date=str(request.conversationDate)
        )

        logger.info(f"Situation analyzed: {situation}")

        # Step 2: 6개 시나리오 생성 (3 roles × 2 types)
        # 병렬로 생성하여 속도 향상
        scenario_tasks = []
        for ai_role in request.aiRoles:
            for topic_type in ["overview", "detail"]:
                task = self._generate_single_scenario(
                    my_role=request.myRole,
                    situation=situation,
                    ai_role=ai_role,
                    topic_type=topic_type
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
        topic_type: str
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

        normalized_questions = self._normalize_questions(scenario_data.get("fixedQuestions", []))

        return ScenarioInfoDto(
            aiRole=ai_role,
            topicType=topic_type,
            title=scenario_data["title"],
            fixedQuestions=normalized_questions
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
