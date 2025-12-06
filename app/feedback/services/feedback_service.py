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
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.services.llm.llm_base import LLMServiceBase

logger = logging.getLogger(__name__)


class SessionFeedback(BaseModel):
    """세션 종합 피드백"""
    avg_pronunciation: float
    avg_accuracy: float  # grammar
    avg_fluency: float  # relevance
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
            accuracy_scores = []  # grammar
            fluency_scores = []  # relevance

            for msg in messages:
                if msg.get("pronunciation_score") is not None:
                    pronunciation_scores.append(msg["pronunciation_score"])
                if msg.get("grammar_score") is not None:
                    accuracy_scores.append(msg["grammar_score"])
                if msg.get("relevance_score") is not None:
                    fluency_scores.append(msg["relevance_score"])

            avg_pronunciation = sum(pronunciation_scores) / len(pronunciation_scores) if pronunciation_scores else 0.0
            avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0
            avg_fluency = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 0.0

            logger.info(
                f"📊 Calculated averages: pronunciation={avg_pronunciation:.1f}, "
                f"accuracy={avg_accuracy:.1f}, fluency={avg_fluency:.1f}"
            )

            # Step 3: 종합 피드백 텍스트 생성
            feedback_long, feedback_short = await self._generate_feedback_text(
                messages=messages,
                avg_pronunciation=avg_pronunciation,
                avg_accuracy=avg_accuracy,
                avg_fluency=avg_fluency
            )

            return SessionFeedback(
                avg_pronunciation=avg_pronunciation,
                avg_accuracy=avg_accuracy,
                avg_fluency=avg_fluency,
                final_feedback_long=feedback_long,
                final_feedback_short=feedback_short
            )

        except Exception as e:
            logger.error(f"Failed to generate session feedback: {e}", exc_info=True)
            return self._create_empty_feedback()

    async def _generate_feedback_text(
        self,
        messages: list,
        avg_pronunciation: float,
        avg_accuracy: float,
        avg_fluency: float
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
                if msg.get("grammar_score") is not None or msg.get("relevance_score") is not None:
                    feedback_sections = msg.get("feedback_sections", [])
                    if feedback_sections:
                        for section in feedback_sections:
                            turn_feedback_list.append(
                                f"- {section.get('type', 'N/A')}: {section.get('feedback_ko', 'N/A')}"
                            )

            turn_feedback_text = "\n".join(turn_feedback_list) if turn_feedback_list else "피드백 없음"

            logger.info(f"📝 대화 로그와 개별 피드백을 기반으로 종합 피드백 생성")

            prompt = f"""# 1. 역할 정의 (Persona)

당신은 실리콘밸리 기업에서 10년 이상 근무한 'IT 커뮤니케이션 멘토'입니다.
딱딱한 선생님이 아니라, 사용자의 성장을 진심으로 응원하는 **친절하고 스마트한 '사수(Senior)'의 톤**으로 말해야 합니다.

# 2. 입력 데이터 (Input)

1. 대화 로그(Log): 사용자와 AI의 전체 회의 내용
{conversation_text}

2. 개별 피드백(Turn Feedback): 문법 및 표현 교정 내역
{turn_feedback_text}

# 3. 작업 목표 (Objective)

사용자의 회의 롤플레잉 기록을 분석하여, **1:1 채팅을 보내듯** 자연스럽게 피드백을 제공하세요.

- 절대 번호(1, 2, 3...)를 매겨서 보고서처럼 쓰지 마세요.
- 개별 문법 오류를 나열하지 말고, **"개발자로서 더 프로페셔널해 보이는 법"** 위주로 조언하세요.

# 4. 출력 흐름 및 작성 지침 (Output Flow)

다음 흐름에 따라 **자연스러운 구어체(해요체)**로 연결해서 작성하세요.

**긴 피드백 (final_feedback_long):**
1. **👋 오프닝 (격려):** "오늘 회의 고생하셨어요!" 같은 인사로 시작하며, 전반적인 수행을 칭찬하세요.
2. **👍 좋았던 점 (Strengths):** 구체적으로 어떤 기술 용어 사용이나 태도가 좋았는지 콕 집어 언급하세요.
3. **🚀 아쉬운 점 & 팁 (Coaching):** 문법 지적보다는 비즈니스 리스크를 언급하세요.
    - *나쁜 예:* "주어를 빼먹으셨네요."
    - *좋은 예:* "주어 없이 말하면 책임 소재가 모호해져서 나중에 곤란할 수 있어요. `We`나 `I`를 명확히 써주세요!"
4. **✨ 이 문장만은 꼭! (One-Point Lesson):** 아까 대화 중 사용자가 자주 틀리는 표현을 하나 골라, "이건 이렇게 말하는 게 훨씬 자연스러워요"라며 **원어민급 표현을 영어로 제시하고, 바로 뒤에 괄호를 쳐서 한국어 해석**을 함께 알려주세요.
   - 예: "We need to deploy the new version." (새 버전을 배포해야 합니다.)

**짧은 피드백 (final_feedback_short):**
- 1-2문장으로 주요 성취를 강조하는 격려 메시지. "~했어요" 톤으로.

# 5. 제약 사항

- **말투:** "~했습니다" 보다는 "~했어요", "~인 것 같아요" 처럼 부드러운 대화체 사용.
- **길이:** 긴 피드백은 공백 포함 600자 내외, 간결하게
- **언어:** 한글로 작성하되, IT 용어(Deploy, Root Cause 등)는 영어 원문 유지.

**JSON 형식으로 응답:**
{{
  "final_feedback_long": "해요체로 작성된 자연스러운 피드백 (600자 내외)...",
  "final_feedback_short": "격려 메시지 (1-2문장)..."
}}
"""

            logger.info("🤖 Generating final feedback text with GPT-4...")
            response = await self.llm.invoke(prompt)

            # JSON 파싱
            import json
            import re
            json_match = re.search(r'\{[^{}]*"final_feedback_(long|short)"[^{}]*\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                feedback_long = parsed.get("final_feedback_long", "롤플레잉 세션을 완료하셨습니다!")
                feedback_short = parsed.get("final_feedback_short", "수고하셨습니다!")
            else:
                feedback_long = "롤플레잉 세션을 완료하셨습니다. 영어 커뮤니케이션 실력 향상을 위해 계속 연습하세요!"
                feedback_short = "수고하셨습니다!"

            logger.info("✅ Final feedback text generated successfully")
            return feedback_long, feedback_short

        except Exception as e:
            logger.error(f"Failed to generate feedback text: {e}", exc_info=True)
            return (
                "롤플레잉 세션을 완료하셨습니다. 계속 연습하세요!",
                "수고하셨습니다!"
            )

    def _create_empty_feedback(self) -> SessionFeedback:
        """빈 피드백 반환 (에러 시)"""
        return SessionFeedback(
            avg_pronunciation=0.0,
            avg_accuracy=0.0,
            avg_fluency=0.0,
            final_feedback_long="세션이 완료되었습니다. 피드백 데이터가 없습니다.",
            final_feedback_short="세션 완료."
        )


# 전역 인스턴스
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """FeedbackService 싱글톤 반환"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
