"""
OpenAI Feedback Service - LLM 기반 피드백 생성 서비스

역할:
    - Azure 발음 평가 점수 기반 종합 피드백 생성
    - 문법, 어휘, 표현력 분석
    - 개선된 추천 문장 생성

출력 항목:
    1. 종합 피드백 (Azure 점수 + 문법 + 어휘 분석)
    2. 추천 문장 (부족한 부분 개선 제안)
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from app.feedback.services.azure_speech_service import PronunciationResult

logger = logging.getLogger(__name__)


@dataclass
class FeedbackResult:
    """LLM 피드백 결과"""
    overall_feedback: str  # 종합 피드백
    suggested_sentence: str  # 추천 문장
    grammar_notes: list[str]  # 문법 지적 사항
    vocabulary_suggestions: list[dict]  # 어휘 개선 제안


class OpenAIFeedbackService:
    """OpenAI 기반 피드백 생성 서비스"""

    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4.1"

    def generate_feedback(
        self,
        user_text: str,
        ai_prompt_text: str,
        pronunciation_result: Optional[PronunciationResult] = None
    ) -> FeedbackResult:
        """
        종합 피드백 및 추천 문장 생성

        Args:
            user_text: 사용자가 말한 텍스트
            ai_prompt_text: AI가 제시한 문장/질문
            pronunciation_result: Azure 발음 평가 결과 (선택)

        Returns:
            FeedbackResult: 피드백 결과
        """
        # Azure 점수 정보 구성
        score_info = ""
        if pronunciation_result:
            score_info = f"""
## Azure Speech 발음 평가 점수
- Accuracy (정확도): {pronunciation_result.accuracy_score:.1f}/100
- Fluency (유창성): {pronunciation_result.fluency_score:.1f}/100
- Completeness (완성도): {pronunciation_result.completeness_score:.1f}/100
- Pronunciation (발음): {pronunciation_result.pronunciation_score:.1f}/100

### 단어별 발음 분석
{self._format_word_analysis(pronunciation_result.words)}
"""

        prompt = f"""You are an expert English conversation coach for Korean learners. Analyze the user's spoken English response and provide detailed, constructive feedback.

## Context
AI's prompt/question: "{ai_prompt_text}"
User's response: "{user_text}"
{score_info}

## Your Task
Provide feedback in the following JSON format. ALL feedback text must be in Korean (except for English example sentences):
(주석: suggested_sentence, grammar_notes, vocabulary_suggestions는 현재 사용하지 않음)

{{
    "overall_feedback": "종합적인 피드백을 한국어로 작성. Azure 점수를 참조하여 발음, 유창성, 정확도를 분석하고, 문법적 오류, 어휘 사용, 표현의 자연스러움을 평가. 칭찬할 점과 개선이 필요한 부분을 균형있게 작성. (3-5문장)",

    "suggested_sentence": "",
    "grammar_notes": [],
    "vocabulary_suggestions": []
}}

## Guidelines
1. Be encouraging but honest about areas needing improvement
2. Focus on practical, actionable feedback
3. Consider the context of conversational English
4. If pronunciation scores are low, provide specific tips
5. Keep feedback concise but comprehensive
(주석: 5. Suggest natural, native-like expressions - 현재 사용하지 않음)

Return ONLY the JSON object, no additional text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert English coach. Always respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            content = response.choices[0].message.content.strip()

            # JSON 파싱
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            return FeedbackResult(
                overall_feedback=result.get("overall_feedback", ""),
                suggested_sentence=result.get("suggested_sentence", ""),
                grammar_notes=result.get("grammar_notes", []),
                vocabulary_suggestions=result.get("vocabulary_suggestions", [])
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._fallback_feedback(user_text)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def _format_word_analysis(self, words: list[dict]) -> str:
        """단어별 분석 결과 포맷팅"""
        if not words:
            return "단어별 분석 정보 없음"

        lines = []
        for word in words:
            error_info = f" (오류: {word['error_type']})" if word.get('error_type') else ""
            lines.append(f"- {word['word']}: {word['accuracy_score']:.0f}점{error_info}")

        return "\n".join(lines)

    def _fallback_feedback(self, user_text: str) -> FeedbackResult:
        """LLM 응답 파싱 실패 시 기본 피드백"""
        return FeedbackResult(
            overall_feedback="피드백 생성 중 오류가 발생했습니다. 다시 시도해 주세요.",
            suggested_sentence=user_text,
            grammar_notes=[],
            vocabulary_suggestions=[]
        )

    def generate_batch_feedback(
        self,
        turns: list[dict]
    ) -> list[FeedbackResult]:
        """
        여러 턴에 대한 배치 피드백 생성

        Args:
            turns: [{
                "user_text": str,
                "ai_prompt_text": str,
                "pronunciation_result": Optional[PronunciationResult]
            }]

        Returns:
            list[FeedbackResult]: 각 턴별 피드백 결과
        """
        results = []
        for turn in turns:
            result = self.generate_feedback(
                user_text=turn["user_text"],
                ai_prompt_text=turn["ai_prompt_text"],
                pronunciation_result=turn.get("pronunciation_result")
            )
            results.append(result)
        return results

    def generate_final_feedback(
        self,
        avg_scores: dict,
        turn_feedbacks: list[dict]
    ) -> str:
        """
        세션 전체에 대한 최종 종합 피드백 생성 (친근한 멘토 톤, 슬랙 메시지 스타일)

        Args:
            avg_scores: {
                "avg_accuracy": float,
                "avg_fluency": float,
                "avg_completeness": float,
                "avg_pronunciation": float,
                "overall_score": float
            }
            turn_feedbacks: [{
                "turn_index": int,
                "message_text": str,
                "feedback_sections": [
                    {"type": "pronunciation", "score": int, "feedback_en": str},
                    {"type": "grammar", "score": int, "feedback_en": str},
                    {"type": "relevance", "score": int, "feedback_en": str}
                ],
                "grammar_score": int,
                "relevance_score": int,
                "overall_score": int
            }]

        Returns:
            str: 친근한 구어체 종합 피드백 (400자 내외)
        """
        # 모든 feedback_sections를 LLM에 전달 (필터링 없이)
        # LLM이 멘토 관점에서 반복되는 핵심 패턴을 파악하여 친근하게 조언하도록 함
        all_feedback_data = []

        for fb in turn_feedbacks:
            turn_data = {
                'turn_index': fb.get('turn_index'),
                'message_text': fb.get('message_text', ''),
                'feedback_sections': fb.get('feedback_sections', [])
            }
            all_feedback_data.append(turn_data)

        # 평균 점수 계산
        pronunciation_avg = avg_scores.get('avg_pronunciation', 0)
        grammar_avg = avg_scores.get('avg_accuracy', 0)
        relevance_avg = avg_scores.get('avg_fluency', 0)
        overall = avg_scores.get('overall_score', 0)

        # feedback_sections를 JSON 형태로 포맷팅
        import json
        feedback_sections_str = json.dumps(all_feedback_data, ensure_ascii=False, indent=2)

        # IT 커뮤니케이션 멘토 스타일 프롬프트 (친근한 사수 톤)
        prompt = f"""# 1. 역할 정의 (Persona)
당신은 실리콘밸리 기업에서 10년 이상 근무한 'IT 커뮤니케이션 멘토'입니다.
딱딱한 선생님이 아니라, 사용자의 성장을 진심으로 응원하는 **친절하고 스마트한 '사수(Senior)'의 톤**으로 말해야 합니다.

# 2. 입력 데이터 (Input)
## 평균 점수
- 발음 (Pronunciation): {pronunciation_avg:.0f}/100
- 문법 (Grammar): {grammar_avg:.0f}/100
- 적합성 (Relevance): {relevance_avg:.0f}/100

## 개별 피드백 (Turn Feedback)
아래는 사용자가 말할 때마다 발생했던 문법/표현 교정 내용입니다:

{feedback_sections_str}

# 3. 작업 목표 (Objective)
사용자의 회의 롤플레잉 기록을 분석하여, **1:1 채팅을 보내듯** 자연스럽게 피드백을 제공하세요.
- 절대 번호(1, 2, 3...)를 매겨서 보고서처럼 쓰지 마세요.
- 개별 문법 오류를 나열하지 말고, **"개발자로서 더 프로페셔널해 보이는 법"** 위주로 조언하세요.

# 4. 출력 흐름 및 작성 지침 (Output Flow)
다음 흐름에 따라 **자연스러운 구어체(해요체)**로 연결해서 작성하세요.

1.  **👋 오프닝 (격려):** "오늘 회의 고생하셨어요!" 같은 인사로 시작하며, 전반적인 수행을 칭찬하세요.
2.  **👍 좋았던 점 (Strengths):** 구체적으로 어떤 기술 용어 사용이나 태도가 좋았는지 콕 집어 언급하세요.
3.  **🚀 아쉬운 점 & 팁 (Coaching):** 문법 지적보다는 비즈니스 리스크를 언급하세요.
    - *나쁜 예:* "주어를 빼먹으셨네요."
    - *좋은 예:* "주어 없이 말하면 책임 소재가 모호해져서 나중에 곤란할 수 있어요. `We`나 `I`를 명확히 써주세요!"
4.  **✨ 이 문장만은 꼭! (One-Point Lesson):** 아까 대화 중 가장 아쉬웠던 문장 하나를 골라, "이건 이렇게 말하는 게 훨씬 자연스러워요"라며 **원어민급 표현**을 알려주세요.

# 5. 제약 사항
- **말투:** "~했습니다" 보다는 "~했어요", "~인 것 같아요" 처럼 부드러운 대화체 사용.
- **길이:** 슬랙(Slack) 메시지 하나에 들어갈 정도로(공백 포함 400자 내외) 간결하게.
- **언어:** 한글로 작성하되, IT 용어(Deploy, Root Cause 등)는 영어 원문 유지."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 실리콘밸리 10년 경력의 IT 커뮤니케이션 멘토입니다. 친절한 사수처럼 구어체(해요체)로 피드백을 주세요. 슬랙 메시지처럼 자연스럽게 작성하며(400자 내외), 번호 없이 흐름에 따라 작성하세요: 👋 오프닝(격려) → 👍 좋았던 점 → 🚀 아쉬운 점 & 팁 → ✨ 이 문장만은 꼭! 비즈니스 리스크와 연결해서 조언하되, 딱딱하지 않게 대화하듯 작성하세요."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400  # 슬랙 메시지 스타일 (400자 내외)
            )

            content = response.choices[0].message.content.strip()
            logger.info("Final feedback generated successfully")
            return content

        except Exception as e:
            logger.error(f"Failed to generate final feedback: {e}")
            # 기본 피드백 반환
            return self._generate_default_final_feedback(avg_scores)

    def _generate_default_final_feedback(self, avg_scores: dict) -> str:
        """기본 최종 피드백 생성 (API 오류 시 사용) - 멘토 톤"""
        overall = avg_scores.get('overall_score', 0)

        if overall >= 90:
            return "👋 와, 정말 잘하셨어요! 90점 넘는 건 쉽지 않은데 대단해요. 👍 문법이나 유창성 모두 훌륭하고, 글로벌 팀과 일해도 전혀 문제없을 실력이에요. 🚀 이 정도면 고급 표현들만 좀 더 익히면 완벽할 것 같아요. 계속 이대로만 유지하세요! ✨ 멋져요!"

        elif overall >= 75:
            return "👋 수고하셨어요! 전반적으로 업무 소통은 잘 되는 수준이에요. 👍 문장 구조도 탄탄하고, 해외 팀과 협업하기에 충분한 실력이에요. 🚀 다만 몇 가지 표현을 좀 더 정확하게 다듬으면 더 프로페셔널해 보일 거예요. 영어 기술 팟캐스트 들으면서 자연스러운 표현 익혀보세요. ✨ 조금만 더 힘내면 상급 레벨이에요!"

        elif overall >= 60:
            return "👋 오늘도 고생하셨어요! 기본적인 업무 대화는 잘하고 계세요. 👍 간단한 소통은 문제없이 잘 해내고 있어요. 🚀 문법이랑 어휘를 좀 더 정확하게 쓰는 연습이 필요할 것 같아요. IT 영어 기사 매일 소리 내서 읽어보면 도움 될 거예요. ✨ 꾸준히만 하면 분명 늘어요!"

        elif overall >= 40:
            return "👋 도전하는 자세가 좋아요! 👍 의사소통하려는 의지가 보여요. 🚀 아직 기초 단계라 문법이랑 단어 선택을 좀 더 다져야 할 것 같아요. 'Could you please...', 'I'd like to...' 같은 기본 표현부터 확실히 익혀보세요. ✨ 포기하지 말고 계속하면 반드시 성장해요!"

        else:
            return "👋 영어 학습 시작하신 거 축하해요! 👍 도전하는 자세가 정말 멋져요. 🚀 지금은 기본 인사랑 간단한 표현부터 천천히 익혀나가면 돼요. 매일 10분씩만이라도 꾸준히 연습해보세요. ✨ 시작이 반이에요! 응원할게요!"


# 싱글톤 인스턴스
_openai_feedback_service: Optional[OpenAIFeedbackService] = None


def get_openai_feedback_service() -> OpenAIFeedbackService:
    """OpenAI Feedback Service 인스턴스 반환"""
    global _openai_feedback_service
    if _openai_feedback_service is None:
        _openai_feedback_service = OpenAIFeedbackService()
    return _openai_feedback_service
