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
        self.model = "gpt-3.5-turbo"

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
        세션 전체에 대한 최종 종합 피드백 생성 (교육학적 구조 + IT 업무 특화)

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
            str: 교육학적으로 구조화된 종합 피드백
        """
        # 턴별 피드백 정리
        turn_feedbacks_text = ""
        for t in turn_summaries:
            turn_num = t.get('turn_number', 0)
            user_msg = t.get('user_message', '')
            suggested = t.get('suggested_sentence', '')
            grammar = t.get('grammar_notes', [])

            feedback_lines = [f"Turn {turn_num}:"]
            feedback_lines.append(f"  학습자 발화: \"{user_msg}\"")
            if suggested:
                feedback_lines.append(f"  개선 제안: \"{suggested}\"")
            if grammar:
                feedback_lines.append(f"  문법 노트: {', '.join(grammar)}")

            turn_feedbacks_text += "\n".join(feedback_lines) + "\n\n"

        # 점수 분석
        scores = {
            "정확도": avg_scores.get('avg_accuracy', 0),
            "유창성": avg_scores.get('avg_fluency', 0),
            "완성도": avg_scores.get('avg_completeness', 0),
            "발음": avg_scores.get('avg_pronunciation', 0)
        }
        best_category = max(scores, key=scores.get)
        worst_category = min(scores, key=scores.get)
        overall = avg_scores.get('overall_score', 0)

        prompt = f"""You are an English education expert evaluating a Korean employee's business English performance in an IT company meeting with a Vietnamese colleague.

## Context
- Scenario: Business meeting between Korean employee (learner) and Vietnamese colleague
- Focus: Real workplace communication effectiveness, not just grammar checking
- Evaluation perspective: Educational expert analyzing practical business English skills
- Task: Synthesize individual turn-by-turn feedback into comprehensive final feedback

## Performance Data
- Overall Score: {overall:.0f}/100
- Pronunciation: {scores['발음']:.0f}/100 - Clarity and accuracy
- Fluency: {scores['유창성']:.0f}/100 - Natural flow and smoothness
- Completeness: {scores['완성도']:.0f}/100 - Sentence completion
- Accuracy: {scores['정확도']:.0f}/100 - Grammar and vocabulary precision
- Strength Area: {best_category}
- Needs Improvement: {worst_category}

## Turn-by-Turn Feedback (Individual evaluations already completed)
{turn_feedbacks_text}

**Note:** Each turn has already been individually evaluated. Your job is to analyze these individual feedbacks and synthesize them into comprehensive final feedback.

## Your Task: Synthesize Individual Feedbacks

Based on the turn-by-turn feedback above, provide comprehensive final feedback by:
1. Identifying **common patterns** across multiple turns
2. Highlighting **recurring strengths** and **repeated mistakes**
3. Providing **actionable next steps** for improvement

## Output Format (in Korean)

### 📊 전반적 평가
[Overall assessment based on {overall:.0f} score and turn-by-turn patterns]
- 90+: 글로벌 프로젝트를 주도할 수 있는 수준
- 75-89: 해외 팀과 원활하게 협업 가능한 수준
- 60-74: 기본적인 업무 소통이 가능한 수준
- 60 미만: 기초 비즈니스 표현 학습이 필요한 수준

### 🎯 반복된 패턴 분석
[Analyze patterns that appeared across multiple turns]
- 자주 나타난 강점 (예: 특정 표현을 잘 사용함)
- 반복적으로 나타난 약점 (예: 같은 문법 실수가 여러 턴에서 발생)

### 💼 실무 커뮤니케이션 효과
[How well did the learner communicate with Vietnamese colleague in business context?]
- 베트남 동료가 이해하기 쉬웠는지
- 업무 맥락에 적절했는지
- 더 전문적으로 개선할 부분

### 📈 우선순위 개선 사항
[Based on {worst_category} and repeated issues in turn feedbacks]
- 가장 먼저 고쳐야 할 습관 (턴별 피드백에서 반복된 것)
- 다음 회의에서 시도할 구체적 표현

### 💪 격려
[Positive reinforcement with specific growth points]

## Guidelines
- Write in Korean (한국어)
- Focus on **patterns** across turns, not individual turns
- Be specific: reference actual examples from turn feedbacks
- Actionable: what should learner do differently next time?
- Length: 8-12 lines total, each section 1-2 lines"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 IT 업무 영어 전문 교육 코치입니다. 개별 턴별 피드백들을 분석하여 반복된 패턴을 찾고, 이를 바탕으로 종합적인 최종 피드백을 한국어로 제공합니다. 턴별 피드백에서 반복적으로 나타난 강점과 약점을 중심으로 실무에 적용 가능한 구체적인 조언을 제공하세요."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            content = response.choices[0].message.content.strip()
            logger.info("Final feedback generated successfully")
            return content

        except Exception as e:
            logger.error(f"Failed to generate final feedback: {e}")
            # 기본 피드백 반환
            return self._generate_default_final_feedback(avg_scores)

    def _generate_default_final_feedback(self, avg_scores: dict) -> str:
        """기본 최종 피드백 생성 (API 오류 시 사용) - IT 업무 특화"""
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
            return f"""📊 **학습 성취도**: 종합 {overall:.0f}점 - 글로벌 프로젝트 리드 가능 수준
특히 {best} 영역에서 뛰어난 역량을 보여주셨습니다.

🎯 **학습 목표 달성도**: 영어로 복잡한 기술적 내용도 명확하게 전달할 수 있는 수준입니다.

💼 **IT 실무 적용**: 해외 클라이언트와의 미팅, 기술 프레젠테이션, 글로벌 팀 리딩에 자신감을 가지세요.

📈 **다음 단계**: 고급 비즈니스 협상 표현이나 기술 논문 발표 영어에 도전해보세요.

💪 글로벌 IT 리더로서의 역량이 충분합니다. 계속해서 성장해 나가세요!"""

        elif overall >= 75:
            return f"""📊 **학습 성취도**: 종합 {overall:.0f}점 - 해외 팀과 원활한 협업 가능
{best} 영역이 특히 우수합니다.

🎯 **학습 목표 달성도**: 업무 관련 영어 소통에 큰 무리가 없는 수준입니다.

💼 **IT 실무 적용**: 영어 이메일 작성, 화상 미팅, 코드 리뷰 코멘트 작성에 활용하세요.

📈 **다음 단계**: {worst} 영역을 보완하면 글로벌 프로젝트 리더로 성장할 수 있습니다. 영어 기술 팟캐스트 청취를 추천드립니다.

💪 꾸준한 성장이 돋보입니다. 조금만 더 노력하면 상급 레벨에 도달할 수 있어요!"""

        elif overall >= 60:
            return f"""📊 **학습 성취도**: 종합 {overall:.0f}점 - 기본적인 업무 소통 가능
{best} 영역에서 강점을 보여주셨습니다.

🎯 **학습 목표 달성도**: 간단한 업무 대화와 이메일 소통이 가능한 수준입니다.

💼 **IT 실무 적용**: 정형화된 이메일 템플릿과 기본 회의 표현부터 실무에 적용해보세요.

📈 **다음 단계**: {worst} 부분을 집중 연습하세요. 매일 IT 관련 영어 기사를 소리 내어 읽는 연습을 추천드립니다.

💪 좋은 기반을 다지고 계십니다. 꾸준히 연습하면 분명 더 성장할 수 있어요!"""

        elif overall >= 40:
            return f"""📊 **학습 성취도**: 종합 {overall:.0f}점 - 기초 표현 학습 단계
{best} 영역에서 가능성이 보입니다.

🎯 **학습 목표 달성도**: 기본적인 인사와 간단한 표현 사용이 가능합니다.

💼 **IT 실무 적용**: "Could you please...", "I'd like to..." 같은 기본 업무 표현부터 익혀보세요.

📈 **다음 단계**: IT 업무에서 자주 쓰는 기본 문장 패턴 20개를 암기하는 것부터 시작해보세요.

💪 모든 전문가도 처음엔 초보였습니다. 꾸준히 도전하면 반드시 성장합니다!"""

        else:
            return f"""📊 **학습 성취도**: 종합 {overall:.0f}점 - 영어 학습 시작 단계
도전하는 자세가 정말 멋집니다!

🎯 **학습 목표 달성도**: 영어 학습의 첫 걸음을 내딛으셨습니다.

💼 **IT 실무 적용**: 먼저 "Hello", "Thank you", "I understand" 같은 기본 표현에 익숙해지세요.

📈 **다음 단계**: 짧은 자기소개와 간단한 인사말부터 연습해보세요. 매일 10분씩 꾸준히 하는 것이 중요합니다.

💪 시작이 반입니다! 매일 조금씩 연습하면 분명 실력이 늘 거예요. 응원합니다!"""


# 싱글톤 인스턴스
_openai_feedback_service: Optional[OpenAIFeedbackService] = None


def get_openai_feedback_service() -> OpenAIFeedbackService:
    """OpenAI Feedback Service 인스턴스 반환"""
    global _openai_feedback_service
    if _openai_feedback_service is None:
        _openai_feedback_service = OpenAIFeedbackService()
    return _openai_feedback_service
