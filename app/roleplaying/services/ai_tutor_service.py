"""
AI Tutor Service
=================
실시간 롤플레잉 대화에서 AI 응답을 생성하는 서비스.

역할:
- 대화 컨텍스트 기반 AI 응답 생성
- 고정 질문 처리 (턴 1, 4, 7)
- LLM 동적 질문 생성
- 대화 흐름 관리

지원 LLM:
- OpenAI GPT-4
- Anthropic Claude
- Ollama (로컬)

의존성:
- app.roleplaying.session_manager (세션 상태)
- app.roleplaying.services.llm_service (LLM 호출)
"""

import logging
from typing import AsyncGenerator, Tuple, Optional

from app.roleplaying.session_manager import SessionState
from app.roleplaying.services.interfaces import QuestionGenerator
from app.roleplaying.prompts.constants import FOLLOWUP_QUESTION_PROMPT
from app.roleplaying.services.utils import format_conversation_history

logger = logging.getLogger(__name__)


class AITutorService:
    """
    AI 튜터 서비스

    대화 컨텍스트를 분석하고 적절한 AI 응답을 생성합니다.

    의존성 주입:
        question_generator: QuestionGenerator 구현체 (질문 생성 담당)
    """

    def __init__(self, question_generator: QuestionGenerator):
        """
        AITutorService 초기화

        Args:
            question_generator: QuestionGenerator 인터페이스 구현체
        """
        self.question_generator = question_generator
        logger.info("AITutorService initialized with injected dependencies")

    async def generate_reply(
        self,
        session_state: SessionState,
        user_text: str
    ) -> Tuple[str, bool]:
        """
        사용자 발화에 대한 AI 응답 생성 (스트리밍 버전을 감싼 헬퍼)

        Args:
            session_state: 세션 상태 (대화 히스토리, 시나리오 정보 포함)
            user_text: 사용자 발화 텍스트

        Returns:
            (ai_response, is_fixed_question)
            - ai_response: AI 응답 텍스트
            - is_fixed_question: 고정 질문 여부 (True/False)
        """
        full_response = ""
        is_fixed = False

        async for chunk, is_fixed_q in self.generate_reply_stream(session_state, user_text):
            full_response += chunk
            is_fixed = is_fixed_q

        return (full_response, is_fixed)

    async def generate_reply_stream(
        self,
        session_state: SessionState,
        user_text: str
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        사용자 발화에 대한 AI 응답을 스트리밍으로 생성

        Args:
            session_state: 세션 상태 (대화 히스토리, 시나리오 정보 포함)
            user_text: 사용자 발화 텍스트

        Yields:
            (chunk: str, is_fixed_question: bool)
            - chunk: 청크 단위로 생성된 텍스트
            - is_fixed_question: 고정 질문 여부
        """
        try:
            # 다음 AI 턴 번호 확인
            next_turn = session_state.get_ai_turn_number()

            logger.info(
                f"Generating AI reply stream: session={session_state.session_id}, "
                f"turn={next_turn}, user_text='{user_text[:30]}...'"
            )

            # ========================================
            # Step 1: 고정 질문 턴 확인 (턴 1, 4, 7)
            # ========================================
            if session_state.should_use_fixed_question():
                fixed_index = session_state.get_fixed_question_index()
                if fixed_index is not None and fixed_index < len(session_state.fixed_questions):
                    fixed_question = session_state.fixed_questions[fixed_index]
                    logger.info(
                        f"Using fixed question stream (turn {next_turn}): {fixed_question[:50]}..."
                    )
                    # 고정 질문은 한 번에 반환 (스트리밍이 필요 없음)
                    yield (fixed_question, True)
                    return

            # ========================================
            # Step 2: 동적 질문 생성 (LLM 스트리밍)
            # ========================================
            logger.debug(f"Starting dynamic question stream (turn {next_turn})")

            async for chunk in self._generate_dynamic_question_stream(
                session_state=session_state,
                user_text=user_text
            ):
                yield (chunk, False)

            logger.info(f"Dynamic question stream completed (turn {next_turn})")

        except Exception as e:
            logger.error(f"Failed to generate AI reply stream: {e}", exc_info=True)
            # Fallback: 기본 질문 반환
            fallback_question = "Could you tell me more about that?"
            yield (fallback_question, False)

    async def _generate_dynamic_question_stream(
        self,
        session_state: SessionState,
        user_text: str
    ) -> AsyncGenerator[str, None]:
        """
        LLM을 사용하여 동적 질문을 스트리밍으로 생성

        Args:
            session_state: 세션 상태
            user_text: 사용자 발화

        Yields:
            청크 단위로 생성된 질문 텍스트
        """
        # ========================================
        # Step 1: 시나리오 & 대화 컨텍스트 구성
        # ========================================
        scenario_context = self._build_scenario_context(session_state)
        conversation_history = self._build_conversation_history(session_state)

        # ========================================
        # Step 2: 프롬프트 구성
        # ========================================
        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            role=session_state.ai_role,
            scenario_context=scenario_context,
            conversation_history=conversation_history,
            user_text=user_text
        )

        try:
            # ========================================
            # Step 3: LLM 스트리밍 호출 (의존성 주입)
            # ========================================
            async for chunk in self.question_generator.generate_followup_question_stream(prompt):
                yield chunk

        except Exception as e:
            logger.error(f"LLM streaming call failed: {e}", exc_info=True)
            # Fallback: 기본 질문 반환
            fallback = (
                f"That's interesting. As a {session_state.ai_role}, "
                "I'd like to know more. Could you elaborate?"
            )
            yield fallback

    def _build_scenario_context(self, session_state: SessionState) -> str:
        """
        시나리오 컨텍스트 문자열 구성

        Returns:
            시나리오 설명 문자열
        """
        return (
            f"User role: {session_state.my_role}\n"
            f"AI role: {session_state.ai_role}\n"
            f"Subject ID: {session_state.subject_id}"
        )

    def _build_conversation_history(
        self,
        session_state: SessionState,
        max_turns: int = 5
    ) -> str:
        """
        대화 히스토리 문자열 구성 (유틸리티 함수를 래퍼)

        Args:
            session_state: 세션 상태
            max_turns: 최대 포함할 턴 수 (기본 5턴)

        Returns:
            대화 히스토리 문자열
        """
        # SessionState의 history를 딕셔너리 리스트로 변환
        if not session_state.history:
            return "(No conversation yet)"

        history_dicts = [
            {"speaker": "ai" if turn.speaker == "ai" else "user", "text": turn.text}
            for turn in session_state.history
        ]

        return format_conversation_history(history_dicts, max_turns)


# ============================================
# 전역 인스턴스 (레거시 호환성)
# ============================================

_ai_tutor_service_instance: Optional["AITutorService"] = None


def get_ai_tutor_service_instance() -> "AITutorService":
    """레거시 코드 호환을 위한 전역 인스턴스 접근자"""
    global _ai_tutor_service_instance
    if _ai_tutor_service_instance is None:
        from app.roleplaying.services.dependencies import get_question_generator

        _ai_tutor_service_instance = AITutorService(
            question_generator=get_question_generator()
        )
    return _ai_tutor_service_instance


# FastAPI WebSocket 핸들러 등에서 사용하는 기본 인스턴스
ai_tutor_service = get_ai_tutor_service_instance()