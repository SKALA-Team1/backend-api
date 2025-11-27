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
Create a mobile-friendly feedback (iPhone 16 screen) that is concise but impactful.

## 점수 분석
- 종합: {overall:.0f}점
- 강점: {best_category} ({scores[best_category]:.0f}점)
- 약점: {worst_category} ({scores[worst_category]:.0f}점)

## 출력 형식 (정확히 3줄, 각 줄 25자 이내)
1줄: [레벨 이모지] + 한 줄 총평 (예: "🌟 중급 실력, 기초 탄탄!")
2줄: [강점 이모지] + 강점 키워드 (예: "💪 발음 정확도 우수")
3줄: [팁 이모지] + 개선 팁 (예: "📝 억양 연습 추천")

## 레벨 기준
- 90점 이상: 🏆 상급
- 75-89점: 🌟 중급
- 60-74점: 📚 초중급
- 40-59점: 🌱 초급
- 40점 미만: 🔰 입문

## 규칙
- 한국어로 작성
- 이모지는 줄 시작에만 1개
- 핵심 키워드 중심으로 간결하게
- 격려 톤 유지

출력은 3줄만, 다른 설명 없이."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert English coach. Write exactly 3 lines of concise feedback in Korean for mobile display."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            logger.info("Final feedback generated successfully")
            return content

        except Exception as e:
            logger.error(f"Failed to generate final feedback: {e}")
            # 기본 피드백 반환
            return self._generate_default_final_feedback(avg_scores)

    def _generate_default_final_feedback(self, avg_scores: dict) -> str:
        """기본 최종 피드백 생성 (iPhone 16 최적화 - 3줄)"""
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
            return f"""🏆 상급 실력, 원어민급 표현력!
💪 {best} 특히 뛰어남
📈 다양한 주제로 실력 확장 추천"""
        elif overall >= 75:
            return f"""🌟 중급 실력, 자연스러운 대화!
💪 {best} 우수
📝 {worst} 보완하면 상급 도달"""
        elif overall >= 60:
            return f"""📚 초중급, 의사소통 가능!
💪 {best} 강점으로 활용
📝 {worst} 집중 연습 필요"""
        elif overall >= 40:
            return f"""🌱 초급, 꾸준히 성장 중!
💪 {best} 좋은 시작점
📝 매일 10분 발화 연습 추천"""
        else:
            return f"""🔰 입문, 첫걸음 시작!
💪 도전하는 자세가 최고
📝 짧은 문장부터 천천히"""


# 싱글톤 인스턴스
_openai_feedback_service: Optional[OpenAIFeedbackService] = None


def get_openai_feedback_service() -> OpenAIFeedbackService:
    """OpenAI Feedback Service 인스턴스 반환"""
    global _openai_feedback_service
    if _openai_feedback_service is None:
        _openai_feedback_service = OpenAIFeedbackService()
    return _openai_feedback_service
