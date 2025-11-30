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
        self.model = "gpt-4o-mini"

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
        turn_summaries: list[dict]
    ) -> str:
        """
        세션 전체에 대한 최종 종합 피드백 생성 (5줄 정도)

        Args:
            avg_scores: {
                "avg_accuracy": float,
                "avg_fluency": float,
                "avg_completeness": float,
                "avg_pronunciation": float,
                "overall_score": float
            }
            turn_summaries: [{
                "turn_number": int,
                "user_message": str,
                "suggested_sentence": str,
                "grammar_notes": list[str]
            }]

        Returns:
            str: 5줄 정도의 최종 종합 피드백
        """
        # 턴별 요약 구성
        turns_text = ""
        for t in turn_summaries:
            grammar = ", ".join(t.get("grammar_notes", [])) or "없음"
            turns_text += f"""
- Turn {t['turn_number']}: "{t['user_message'][:50]}..."
  추천 문장: "{t.get('suggested_sentence', '')[:50]}..."
  문법 노트: {grammar}
"""

        # 가장 높은 점수와 낮은 점수 항목 찾기
        scores = {
            "정확도": avg_scores.get('avg_accuracy', 0),
            "유창성": avg_scores.get('avg_fluency', 0),
            "완성도": avg_scores.get('avg_completeness', 0),
            "발음": avg_scores.get('avg_pronunciation', 0)
        }
        best_category = max(scores, key=scores.get)
        worst_category = min(scores, key=scores.get)
        overall = avg_scores.get('overall_score', 0)

        prompt = f"""You are an expert English conversation coach for Korean learners.
사용자의 영어 회화 세션 전체를 분석하여 상세하고 따뜻한 종합 피드백을 작성해주세요.

## 점수 분석
- 종합 점수: {overall:.0f}점
- 정확도(Accuracy): {scores['정확도']:.0f}점
- 유창성(Fluency): {scores['유창성']:.0f}점
- 완성도(Completeness): {scores['완성도']:.0f}점
- 발음(Pronunciation): {scores['발음']:.0f}점
- 강점 영역: {best_category}
- 개선 필요 영역: {worst_category}

## 출력 형식
다음 구조로 한국어 피드백을 작성하세요:

1. **레벨 판정** (1줄): 종합 점수 기반으로 현재 실력 레벨을 알려주세요
   - 90점 이상: 상급 (Advanced)
   - 75-89점: 중급 (Intermediate)
   - 60-74점: 초중급 (Pre-Intermediate)
   - 40-59점: 초급 (Elementary)
   - 40점 미만: 입문 (Beginner)

2. **강점 분석** (2-3줄): 가장 잘한 부분을 구체적으로 칭찬해주세요

3. **개선 포인트** (2-3줄): 부족한 부분과 구체적인 개선 방법을 제안해주세요

4. **학습 팁** (1-2줄): 실력 향상을 위한 실용적인 조언을 해주세요

5. **응원 메시지** (1줄): 따뜻한 격려로 마무리해주세요

## 규칙
- 반드시 한국어로 작성
- 격려하면서도 솔직한 피드백
- 구체적이고 실용적인 조언 포함
- 전체 5-8줄 정도로 작성"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert English conversation coach for Korean learners. Provide detailed, warm, and constructive feedback in Korean."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            content = response.choices[0].message.content.strip()
            logger.info("Final feedback generated successfully")
            return content

        except Exception as e:
            logger.error(f"Failed to generate final feedback: {e}")
            # 기본 피드백 반환
            return self._generate_default_final_feedback(avg_scores)

    def _generate_default_final_feedback(self, avg_scores: dict) -> str:
        """기본 최종 피드백 생성 (API 오류 시 사용)"""
        overall = avg_scores.get('overall_score', 0)

        # 강점/약점 분석
        scores = {
            "정확도": avg_scores.get('avg_accuracy', 0),
            "유창성": avg_scores.get('avg_fluency', 0),
            "완성도": avg_scores.get('avg_completeness', 0),
            "발음": avg_scores.get('avg_pronunciation', 0)
        }
        best = max(scores, key=scores.get)
        worst = min(scores, key=scores.get)

        if overall >= 90:
            return f"""[레벨: 상급 (Advanced)] 종합 {overall:.0f}점

훌륭합니다! 원어민에 가까운 영어 실력을 보여주셨습니다. 특히 {best} 영역에서 뛰어난 능력을 발휘하셨네요.

현재 실력을 유지하면서 다양한 주제의 대화에 도전해보세요. 비즈니스 영어나 학술적인 표현도 시도해보시면 좋겠습니다.

앞으로도 꾸준히 영어를 사용하시면서 실력을 더욱 발전시켜 나가세요!"""

        elif overall >= 75:
            return f"""[레벨: 중급 (Intermediate)] 종합 {overall:.0f}점

잘하고 계십니다! 영어로 자연스러운 의사소통이 가능한 수준입니다. {best} 영역이 특히 우수하네요.

{worst} 부분을 조금 더 연습하시면 상급 레벨로 도약할 수 있습니다. 매일 영어 뉴스나 팟캐스트를 듣는 것을 추천드립니다.

꾸준한 노력이 빛을 발하고 있습니다. 조금만 더 힘내세요!"""

        elif overall >= 60:
            return f"""[레벨: 초중급 (Pre-Intermediate)] 종합 {overall:.0f}점

좋은 진전을 보이고 계십니다! 기본적인 영어 의사소통이 가능한 단계입니다. {best} 영역에서 강점을 보여주셨어요.

{worst} 부분에 집중해서 연습하시면 빠르게 실력이 향상될 거예요. 짧은 영어 문장을 매일 따라 말하는 연습을 해보세요.

지금처럼 꾸준히 노력하시면 분명 목표를 달성하실 수 있습니다!"""

        elif overall >= 40:
            return f"""[레벨: 초급 (Elementary)] 종합 {overall:.0f}점

영어 학습을 잘 시작하셨습니다! {best} 영역에서 가능성을 보여주셨어요.

기초 문장 패턴을 반복해서 연습하고, 매일 10분씩 영어로 말하는 습관을 들여보세요. 처음엔 어렵지만 점점 나아질 거예요.

모든 전문가도 처음엔 초보였습니다. 포기하지 마시고 꾸준히 도전하세요!"""

        else:
            return f"""[레벨: 입문 (Beginner)] 종합 {overall:.0f}점

영어 학습의 첫 걸음을 내딛으셨군요! 도전하는 자세가 정말 멋집니다.

기본 인사말과 자기소개부터 천천히 시작해보세요. 짧고 쉬운 문장을 자신감 있게 말하는 것이 중요합니다.

매일 조금씩 연습하면 분명 실력이 늘 거예요. 응원합니다!"""


# 싱글톤 인스턴스
_openai_feedback_service: Optional[OpenAIFeedbackService] = None


def get_openai_feedback_service() -> OpenAIFeedbackService:
    """OpenAI Feedback Service 인스턴스 반환"""
    global _openai_feedback_service
    if _openai_feedback_service is None:
        _openai_feedback_service = OpenAIFeedbackService()
    return _openai_feedback_service
