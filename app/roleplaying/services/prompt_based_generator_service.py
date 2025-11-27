"""
Prompt-Based Scenario Service
============================
사용자 프롬프트 기반 시나리오 생성을 담당하는 서비스.

역할:
    - 사용자 입력(my_role, ai_role, situation)으로부터 시나리오 생성
    - DB에서 사용자의 과거 시나리오 조회 (컨텍스트)
    - LLM을 통한 상황 구체화, 제목 생성, 질문 생성
    - 생성된 데이터를 DTO로 반환 (DB 저장 안 함)

의존성:
    - LLMService
    - SQLAlchemy Session
    - Pydantic schemas
"""

import logging
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.roleplaying.services.llm_service import LLMService
from app.roleplaying.schemas import ScenarioInfoDto
from app.roleplaying.services.title_utils import compact_title

logger = logging.getLogger(__name__)


class PromptBasedScenarioService:
    """프롬프트 기반 시나리오 생성 서비스"""

    def __init__(self, model_name: str = "llama3.2"):
        """
        Args:
            model_name: Ollama 모델 이름
        """
        self.llm_service = LLMService(model_name=model_name)

    async def generate_from_prompt(
        self,
        user_id: int,
        my_role: str,
        ai_role: str,
        situation: str,
        db: Session
    ) -> ScenarioInfoDto:
        """
        사용자 프롬프트로부터 시나리오를 생성합니다.

        Args:
            user_id: 사용자 ID
            my_role: 사용자의 역할
            ai_role: AI의 역할
            situation: 롤플레이 상황
            db: DB 세션

        Returns:
            생성된 시나리오 DTO

        Raises:
            ValueError: 시나리오 생성 실패
        """
        logger.info(
            f"Generating scenario from prompt for user {user_id}: "
            f"my_role={my_role}, ai_role={ai_role}"
        )

        # Step 1: DB에서 사용자의 과거 시나리오 조회 (컨텍스트)
        context = await self._fetch_user_context(user_id, db)
        logger.debug(f"Fetched {len(context)} past scenarios for context")

        # Step 2: 상황 구체화
        concrete_situation = await self.llm_service.enhance_situation_from_prompt(
            user_input=situation,
            my_role=my_role,
            ai_role=ai_role,
            context=context
        )
        logger.debug(f"Enhanced situation: {concrete_situation}")

        # Step 3: 제목 생성
        title = await self.llm_service.generate_title_for_prompt(
            situation=concrete_situation,
            ai_role=ai_role,
            topic_type="direct",
            my_role=my_role
        )
        title = compact_title(
            raw_title=title,
            banned_phrases=[ai_role, my_role],
            fallback="Direct Dialogue Focus",
            max_length=50
        )
        logger.debug(f"Generated title: {title}")

        # Step 4: 고정 질문 생성
        fixed_questions = await self._generate_fixed_questions(
            situation=concrete_situation,
            my_role=my_role,
            ai_role=ai_role
        )
        logger.debug(f"Generated {len(fixed_questions)} fixed questions")

        # Step 5: 응답 구성
        result = ScenarioInfoDto(
            aiRole=ai_role,
            topicType="direct",
            title=title,
            fixedQuestions=fixed_questions
        )

        logger.info(f"Successfully generated scenario for user {user_id}")
        return result

    async def _fetch_user_context(
        self,
        user_id: int,
        db: Session
    ) -> List[Dict[str, Any]]:
        """
        사용자의 과거 시나리오를 DB에서 조회합니다.

        Args:
            user_id: 사용자 ID
            db: DB 세션

        Returns:
            과거 시나리오 목록 (situation, fixed_questions 포함)
        """
        try:
            query = text("""
                SELECT s.situation, s.fixed_questions
                FROM subject s
                WHERE s.user_id = :user_id
                ORDER BY s.created_at DESC
                LIMIT 5
            """)

            result = db.execute(query, {"user_id": user_id})
            rows = result.fetchall()

            context = []
            for row in rows:
                situation = row.situation or ""
                fixed_questions_raw = row.fixed_questions

                # fixed_questions 파싱
                if fixed_questions_raw:
                    if isinstance(fixed_questions_raw, str):
                        try:
                            fixed_questions = json.loads(fixed_questions_raw)
                        except json.JSONDecodeError:
                            fixed_questions = []
                    else:
                        fixed_questions = fixed_questions_raw
                else:
                    fixed_questions = []

                context.append({
                    "situation": situation,
                    "fixedQuestions": fixed_questions
                })

            return context

        except Exception as e:
            logger.warning(f"Failed to fetch user context: {e}")
            return []

    async def _generate_fixed_questions(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> List[str]:
        """
        고정 질문을 생성합니다. (정확히 3개)

        Slack 기반 시나리오와 동일한 역할의 질문을 생성:
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
        try:
            questions = await self.llm_service.generate_fixed_questions_for_prompt(
                situation=situation,
                my_role=my_role,
                ai_role=ai_role
            )

            # 검증
            validated = self._normalize_questions(questions)
            return validated

        except Exception as error:
            logger.error(
                f"Failed to generate fixed questions for {ai_role}: {error}",
                exc_info=True
            )
            # Fallback: 기본 질문
            return self._default_questions(my_role, ai_role)

    def _normalize_questions(self, questions: List) -> List[str]:
        """
        질문들을 정규화하고 정확히 3개인지 검증합니다.

        Args:
            questions: 정규화할 질문 목록

        Returns:
            정규화된 3개의 질문

        Raises:
            ValueError: 질문 개수가 3개가 아님
        """
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

    def _default_questions(self, my_role: str, ai_role: str) -> List[str]:
        """
        LLM 생성 실패시 사용할 기본 질문들입니다.

        Args:
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            3개의 기본 질문
        """
        return [
            f"Hi! Could you walk me through your perspective on this as a {ai_role}?",
            f"What are your main concerns or priorities that we should address?",
            f"Before we wrap up, what would be your recommended next steps?"
        ]
