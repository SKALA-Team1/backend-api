"""
종합 피드백 생성 서비스

역할:
- 세션의 모든 발화에서 피드백 점수 수집
- 평균 점수 계산
- 종합 피드백 텍스트 생성 (장문 + 단문)
"""

import logging
from typing import Optional
from pydantic import BaseModel

from app.config import settings
from app.feedback.prompts.constants import FINAL_FEEDBACK_SYSTEM_PROMPT
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.services.llm.llm_base import LLMServiceBase

logger = logging.getLogger(__name__)


# Fallback 메시지 상수
DEFAULT_FEEDBACK_LONG = "롤플레잉 세션을 완료하셨습니다. 영어 커뮤니케이션 실력 향상을 위해 계속 연습하세요!"
DEFAULT_FEEDBACK_SHORT = "수고하셨습니다!"

EMPTY_FEEDBACK_LONG = "세션이 완료되었습니다. 피드백 데이터가 충분하지 않습니다."
EMPTY_FEEDBACK_SHORT = "세션 완료."


class SessionFeedback(BaseModel):
    """세션 종합 피드백"""
    total_pronunciation: float
    total_grammar: float
    total_diversity: float
    final_feedback_long: str
    final_feedback_short: str


class FeedbackService:
    """종합 피드백 생성 서비스"""

    def __init__(self):
        self.llm = LLMServiceBase(
            api_key=settings.openai_api_key,
            model_name=settings.OPENAI_MODEL_FEEDBACK,  # gpt-4o
            temperature=0.7
        ).llm

    async def get_session_feedback(
        self,
        session_id: str,
        scenario_id: int
    ) -> SessionFeedback:
        """
        세션의 종합 피드백 생성

        Args:
            session_id: 세션 ID
            scenario_id: 시나리오 ID

        Returns:
            SessionFeedback: 평균 점수 + 피드백 텍스트
        """
        try:
            # Step 1: Spring 2에서 세션의 모든 발화 조회
            logger.info(f"📊 Fetching session messages: session={session_id}")
            messages = await spring2_client.get_session_messages(
                session_id=session_id,
                speaker="user"  # 사용자 발화만 조회
            )

            if not messages:
                logger.warning(f"No messages found for session {session_id}")
                return self._create_empty_feedback()

            # Step 2: 평균 점수 계산
            pronunciation_scores = []
            grammar_scores = []
            diversity_scores = []

            for msg in messages:
                if msg.get("pronunciation_score") is not None:
                    pronunciation_scores.append(msg["pronunciation_score"])
                if msg.get("grammar_score") is not None:
                    grammar_scores.append(msg["grammar_score"])
                if msg.get("relevance_score") is not None:
                    diversity_scores.append(msg["relevance_score"])

            total_pronunciation = sum(pronunciation_scores) / len(pronunciation_scores) if pronunciation_scores else 0.0
            total_grammar = sum(grammar_scores) / len(grammar_scores) if grammar_scores else 0.0
            total_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0

            logger.info(
                f"📊 Calculated averages: pronunciation={total_pronunciation:.1f}, "
                f"grammar={total_grammar:.1f}, diversity={total_diversity:.1f}"
            )

            # Step 3: 종합 피드백 텍스트 생성
            feedback_long, feedback_short = await self._generate_feedback_text(
                messages=messages,
                total_pronunciation=total_pronunciation,
                total_grammar=total_grammar,
                total_diversity=total_diversity
            )

            return SessionFeedback(
                total_pronunciation=total_pronunciation,
                total_grammar=total_grammar,
                total_diversity=total_diversity,
                final_feedback_long=feedback_long,
                final_feedback_short=feedback_short
            )

        except Exception as e:
            logger.error(f"Failed to generate session feedback: {e}", exc_info=True)
            return self._create_empty_feedback()

    async def _generate_feedback_text(
        self,
        messages: list,
        total_pronunciation: float,
        total_grammar: float,
        total_diversity: float
    ) -> tuple[str, str]:
        """
        종합 피드백 텍스트 생성 (GPT-4)

        Returns:
            (final_feedback_long, final_feedback_short)
        """
        try:
            # 대화 로그 생성 (전체 회의 내용)
            conversation_log = []
            for msg in messages:
                speaker = msg.get('speaker', 'unknown')
                text = msg.get('text', '')
                if speaker == 'user':
                    conversation_log.append(f"User: {text}")
                elif speaker == 'ai':
                    conversation_log.append(f"AI: {text}")

            conversation_text = "\n".join(conversation_log)

            # 개별 피드백 데이터 (Turn Feedback)
            turn_feedback_list = []
            for msg in messages:
                if msg.get("pronunciation_score") is not None or msg.get("grammar_score") is not None or msg.get("relevance_score") is not None:
                    feedback_sections = msg.get("feedback_sections", [])
                    if feedback_sections:
                        for section in feedback_sections:
                            turn_feedback_list.append(
                                f"- {section.get('type', 'N/A')}: {section.get('feedback_ko', 'N/A')}"
                            )

            turn_feedback_text = "\n".join(turn_feedback_list) if turn_feedback_list else "피드백 없음"

            logger.info(f"📝 대화 로그와 개별 피드백을 기반으로 종합 피드백 생성")

            # Generate prompt from template
            prompt = FINAL_FEEDBACK_SYSTEM_PROMPT.format(
                conversation_text=conversation_text,
                turn_feedback_text=turn_feedback_text
            )

            logger.info("🤖 Generating final feedback text with GPT-4...")
            response = await self.llm.invoke(prompt)

            # JSON 파싱
            import json
            import re
            json_match = re.search(r'\{[^{}]*"final_feedback_(long|short)"[^{}]*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                feedback_long = parsed.get("final_feedback_long", DEFAULT_FEEDBACK_LONG)
                feedback_short = parsed.get("final_feedback_short", DEFAULT_FEEDBACK_SHORT)
            else:
                feedback_long = DEFAULT_FEEDBACK_LONG
                feedback_short = DEFAULT_FEEDBACK_SHORT

            logger.info("✅ Final feedback text generated successfully")
            return feedback_long, feedback_short

        except Exception as e:  
            logger.error(f"Failed to generate feedback text: {e}", exc_info=True)
            return (
                DEFAULT_FEEDBACK_LONG,
                DEFAULT_FEEDBACK_SHORT
            )

    def _create_empty_feedback(self) -> SessionFeedback:
        """빈 피드백 반환 (데이터 없을 때)"""
        return SessionFeedback(
            total_pronunciation=0.0,
            total_grammar=0.0,
            total_diversity=0.0,
            final_feedback_long=EMPTY_FEEDBACK_LONG,
            final_feedback_short=EMPTY_FEEDBACK_SHORT
        )


# 전역 인스턴스
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """FeedbackService 싱글톤 반환"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service


async def generate_and_save_final_feedback(
    session_id: str,
    scenario_id: int
) -> None:
    """
    종합 피드백 생성 및 Spring 2 API에 저장

    이 함수는 세션 종료 후 백그라운드에서 실행됩니다.

    Args:
        session_id: 세션 ID
        scenario_id: 시나리오 ID

    흐름:
        1. 종합 피드백 생성 (평균 점수 + 텍스트)
        2. Spring 2 API에 저장
    """
    try:
        feedback_service = get_feedback_service()

        logger.info(f"🔄 [Background] Generating final feedback: session={session_id}, scenario_id={scenario_id}")

        # 종합 피드백 생성
        session_feedback = await feedback_service.get_session_feedback(
            session_id=session_id,
            scenario_id=scenario_id
        )

        logger.info(
            f"📊 [Background] Final feedback generated: session={session_id}, "
            f"total_pronunciation={session_feedback.total_pronunciation}, "
            f"total_grammar={session_feedback.total_grammar}, "
            f"total_diversity={session_feedback.total_diversity}"
        )

        # DB에 저장 (Spring 2 API)
        await spring2_client.save_final_feedback(
            session_id=session_id,
            final_feedback_long=session_feedback.final_feedback_long,
            final_feedback_short=session_feedback.final_feedback_short,
            total_pronunciation=session_feedback.total_pronunciation,
            total_grammar=session_feedback.total_grammar,
            total_diversity=session_feedback.total_diversity,
        )
        logger.info(f"✅ [Background] Final feedback saved to DB: session={session_id}")

    except Exception as e:
        logger.error(
            f"❌ [Background] Failed to generate/save final feedback: session={session_id}, error={e}",
            exc_info=True
        )
