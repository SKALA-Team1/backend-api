"""
Feedback Service - 피드백 통합 서비스

역할:
    - Azure Speech 평가 + OpenAI 피드백을 통합하여 처리
    - 턴 단위 피드백 생성
    - Spring API를 통해 DB에 저장
    - 세션 전체 피드백 집계

출력 (6개 항목):
    1. Accuracy (정확도) - Azure
    2. Fluency (유창성) - Azure
    3. Completeness (완성도) - Azure
    4. Pronunciation (발음) - Azure
    5. Overall Feedback (종합 피드백) - OpenAI
    6. Suggested Sentence (추천 문장) - OpenAI

흐름:
    FastAPI (피드백 생성) → Spring API (DB 저장) → MySQL
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.feedback.schemas import (
    TurnFeedbackRequest,
    TurnFeedbackResponse,
    SessionFeedbackResponse,
    ScoreDetail,
    VocabularySuggestion
)
from app.feedback.services.azure_speech_service import (
    AzureSpeechService,
    PronunciationResult,
    get_azure_speech_service
)
from app.feedback.services.openai_feedback_service import (
    OpenAIFeedbackService,
    FeedbackResult,
    get_openai_feedback_service
)
from app.integrations.clients.spring2_client import spring2_client

logger = logging.getLogger(__name__)


def _score_to_level(score: float) -> str:
    """점수를 레벨로 변환"""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Fair"
    elif score >= 40:
        return "Poor"
    else:
        return "VeryPoor"


class FeedbackService:
    """피드백 통합 서비스"""

    def __init__(self):
        self.azure_service: Optional[AzureSpeechService] = None
        self.openai_service: Optional[OpenAIFeedbackService] = None

    def _get_azure_service(self) -> AzureSpeechService:
        """Azure 서비스 lazy loading"""
        if self.azure_service is None:
            self.azure_service = get_azure_speech_service()
        return self.azure_service

    def _get_openai_service(self) -> OpenAIFeedbackService:
        """OpenAI 서비스 lazy loading"""
        if self.openai_service is None:
            self.openai_service = get_openai_feedback_service()
        return self.openai_service

    async def generate_turn_feedback(
        self,
        request: TurnFeedbackRequest
    ) -> TurnFeedbackResponse:
        """
        턴 단위 피드백 생성 (6개 항목)

        흐름:
        1. Azure Speech로 발음 평가
        2. OpenAI로 종합 피드백 + 추천 문장 생성
        3. Spring API를 통해 DB에 저장

        Args:
            request: 피드백 요청

        Returns:
            TurnFeedbackResponse: 6개 항목 피드백 응답
        """
        # 1. Azure 발음 평가 (오디오 파일이 있는 경우)
        pronunciation_result: Optional[PronunciationResult] = None

        if request.audio_file_path:
            try:
                azure_service = self._get_azure_service()
                pronunciation_result = azure_service.evaluate_pronunciation_from_file(
                    audio_file_path=request.audio_file_path,
                    reference_text=request.user_message
                )
                logger.info(f"Azure evaluation completed for turn {request.turn_number}")
            except Exception as e:
                logger.error(f"Azure evaluation failed: {e}")

        # 2. OpenAI 피드백 생성
        openai_service = self._get_openai_service()
        feedback_result: FeedbackResult = openai_service.generate_feedback(
            user_text=request.user_message,
            ai_prompt_text=request.system_message,
            pronunciation_result=pronunciation_result
        )

        # 3. 점수 설정
        if pronunciation_result:
            accuracy_score = pronunciation_result.accuracy_score
            fluency_score = pronunciation_result.fluency_score
            completeness_score = pronunciation_result.completeness_score
            pronunciation_score = pronunciation_result.pronunciation_score
        else:
            # Azure 평가 없는 경우 기본값
            accuracy_score = 0.0
            fluency_score = 0.0
            completeness_score = 0.0
            pronunciation_score = 0.0

        # 4. 어휘 제안 변환 (주석처리: 종합피드백과 Azure 평가만 사용)
        # vocab_suggestions = [
        #     VocabularySuggestion(
        #         original=v.get("original", "") if isinstance(v, dict) else getattr(v, "original", ""),
        #         suggested=v.get("suggested", "") if isinstance(v, dict) else getattr(v, "suggested", ""),
        #         reason=v.get("reason", "") if isinstance(v, dict) else getattr(v, "reason", "")
        #     )
        #     for v in feedback_result.vocabulary_suggestions
        # ]
        vocab_suggestions = []  # 빈 리스트로 대체

        # vocab_suggestions_dict = [
        #     {
        #         "original": v.original,
        #         "suggested": v.suggested,
        #         "reason": v.reason
        #     }
        #     for v in vocab_suggestions
        # ]
        vocab_suggestions_dict = []  # 빈 리스트로 대체

        # 5. Spring API로 DB 저장 (주석처리: grammar_notes, vocabulary_suggestions, suggested_sentence 제외)
        evaluation_json = json.dumps({
            "words": pronunciation_result.words if pronunciation_result else []
            # "grammar_notes": feedback_result.grammar_notes,
            # "vocabulary_suggestions": vocab_suggestions_dict,
            # "suggested_sentence": feedback_result.suggested_sentence
        }, ensure_ascii=False)

        try:
            spring_response = await spring2_client.save_turn_feedback(
                session_id=request.session_id,
                scenario_id=request.scenario_id,
                turn_number=request.turn_number,
                user_message=request.user_message,
                system_message=request.system_message,
                accuracy_score=accuracy_score,
                accuracy_level=_score_to_level(accuracy_score),
                fluency_score=fluency_score,
                fluency_level=_score_to_level(fluency_score),
                completeness_score=completeness_score,
                completeness_level=_score_to_level(completeness_score),
                pronunciation_score=pronunciation_score,
                pronunciation_level=_score_to_level(pronunciation_score),
                overall_feedback=feedback_result.overall_feedback,
                # 주석처리: suggested_sentence, grammar_notes, vocabulary_suggestions 제외
                suggested_sentence="",  # feedback_result.suggested_sentence,
                grammar_notes=[],  # feedback_result.grammar_notes,
                vocabulary_suggestions=[],  # vocab_suggestions_dict,
                evaluation_json=evaluation_json
            )
            turn_feedback_id = spring_response.get("turnFeedbackId", 0)
            logger.info(f"Feedback saved via Spring: turn_feedback_id={turn_feedback_id}")
        except Exception as e:
            logger.error(f"Failed to save feedback via Spring: {e}")
            turn_feedback_id = 0

        # 6. 응답 생성 (주석처리: suggested_sentence, grammar_notes, vocabulary_suggestions 제외)
        return TurnFeedbackResponse(
            turn_feedback_id=turn_feedback_id,
            turn_number=request.turn_number,
            accuracy=ScoreDetail(score=accuracy_score, level=_score_to_level(accuracy_score)),
            fluency=ScoreDetail(score=fluency_score, level=_score_to_level(fluency_score)),
            completeness=ScoreDetail(score=completeness_score, level=_score_to_level(completeness_score)),
            pronunciation=ScoreDetail(score=pronunciation_score, level=_score_to_level(pronunciation_score)),
            overall_feedback=feedback_result.overall_feedback,
            # suggested_sentence=feedback_result.suggested_sentence,
            suggested_sentence="",  # 주석처리
            user_message=request.user_message,
            system_message=request.system_message,
            # grammar_notes=feedback_result.grammar_notes,
            grammar_notes=[],  # 주석처리
            # vocabulary_suggestions=vocab_suggestions,
            vocabulary_suggestions=[],  # 주석처리
            created_at=datetime.utcnow()
        )

    async def get_session_feedback(
        self,
        session_id: int,
        scenario_id: int
    ) -> SessionFeedbackResponse:
        """
        세션 전체 피드백 조회 (Spring API를 통해)

        Args:
            session_id: 세션 ID
            scenario_id: 시나리오 ID

        Returns:
            SessionFeedbackResponse: 세션 전체 피드백
        """
        # Spring에서 턴 피드백 조회
        try:
            spring_feedbacks = await spring2_client.get_session_feedbacks(session_id)
        except Exception as e:
            logger.error(f"Failed to get feedbacks from Spring: {e}")
            spring_feedbacks = []

        # 턴별 응답 생성
        turn_responses = []
        total_accuracy = 0.0
        total_fluency = 0.0
        total_completeness = 0.0
        total_pronunciation = 0.0

        for tf in spring_feedbacks:
            accuracy_data = tf.get("accuracy", {})
            fluency_data = tf.get("fluency", {})
            completeness_data = tf.get("completeness", {})
            pronunciation_data = tf.get("pronunciation", {})

            accuracy_score = float(accuracy_data.get("score", 0))
            fluency_score = float(fluency_data.get("score", 0))
            completeness_score = float(completeness_data.get("score", 0))
            pronunciation_score = float(pronunciation_data.get("score", 0))

            total_accuracy += accuracy_score
            total_fluency += fluency_score
            total_completeness += completeness_score
            total_pronunciation += pronunciation_score

            vocab_suggestions = [
                VocabularySuggestion(
                    original=v.get("original", ""),
                    suggested=v.get("suggested", ""),
                    reason=v.get("reason", "")
                )
                for v in tf.get("vocabularySuggestions", [])
            ]

            turn_responses.append(TurnFeedbackResponse(
                turn_feedback_id=tf.get("turnFeedbackId", 0),
                turn_number=tf.get("turnNumber", 0),
                accuracy=ScoreDetail(
                    score=accuracy_score,
                    level=accuracy_data.get("level", "N/A")
                ),
                fluency=ScoreDetail(
                    score=fluency_score,
                    level=fluency_data.get("level", "N/A")
                ),
                completeness=ScoreDetail(
                    score=completeness_score,
                    level=completeness_data.get("level", "N/A")
                ),
                pronunciation=ScoreDetail(
                    score=pronunciation_score,
                    level=pronunciation_data.get("level", "N/A")
                ),
                overall_feedback=tf.get("overallFeedback", ""),
                suggested_sentence=tf.get("suggestedSentence", ""),
                user_message=tf.get("userMessage", ""),
                system_message=tf.get("systemMessage", ""),
                grammar_notes=tf.get("grammarNotes", []),
                vocabulary_suggestions=vocab_suggestions,
                created_at=datetime.fromisoformat(tf["createdAt"].replace("Z", "+00:00")) if tf.get("createdAt") else datetime.utcnow()
            ))

        # 평균 점수 계산
        total_turns = len(spring_feedbacks)
        if total_turns > 0:
            avg_accuracy = round(total_accuracy / total_turns, 2)
            avg_fluency = round(total_fluency / total_turns, 2)
            avg_completeness = round(total_completeness / total_turns, 2)
            avg_pronunciation = round(total_pronunciation / total_turns, 2)
            overall_score = round((avg_accuracy + avg_fluency + avg_completeness + avg_pronunciation) / 4, 2)
        else:
            avg_accuracy = avg_fluency = avg_completeness = avg_pronunciation = overall_score = 0.0

        avg_scores = {
            "avg_accuracy": avg_accuracy,
            "avg_fluency": avg_fluency,
            "avg_completeness": avg_completeness,
            "avg_pronunciation": avg_pronunciation,
            "overall_score": overall_score,
            "total_turns": total_turns
        }

        # 전체 요약 코멘트 생성
        summary_comment = self._generate_summary_comment(avg_scores)

        return SessionFeedbackResponse(
            session_id=session_id,
            scenario_id=scenario_id,
            total_turns=total_turns,
            avg_accuracy=avg_accuracy,
            avg_fluency=avg_fluency,
            avg_completeness=avg_completeness,
            avg_pronunciation=avg_pronunciation,
            overall_score=overall_score,
            turn_feedbacks=turn_responses,
            summary_comment=summary_comment,
            created_at=datetime.utcnow()
        )

    def _generate_summary_comment(self, avg_scores: dict) -> str:
        """세션 전체 요약 코멘트 생성"""
        overall = avg_scores["overall_score"]

        if overall >= 90:
            return "훌륭합니다! 발음과 유창성 모두 뛰어난 실력을 보여주셨습니다."
        elif overall >= 75:
            return "잘하셨습니다! 전반적으로 좋은 영어 실력입니다. 몇 가지 부분만 개선하면 더 좋아질 거예요."
        elif overall >= 60:
            return "괜찮은 수준입니다. 발음과 유창성을 조금 더 연습하면 크게 향상될 수 있습니다."
        elif overall >= 40:
            return "기초적인 의사소통은 가능하지만, 꾸준한 연습이 필요합니다. 추천 문장을 참고해 보세요."
        else:
            return "영어 학습을 시작하는 단계입니다. 기본 발음부터 차근차근 연습해 보세요."

    async def get_session_messages(
        self,
        session_id: str,
        scenario_id: int
    ) -> list[dict]:
        """
        세션의 메시지 조회 (Spring API를 통해)

        scenario_message 테이블에서 해당 세션의 모든 메시지를 가져옵니다.
        turn_index 순으로 정렬되어 반환됩니다.

        Args:
            session_id: 세션 ID (UUID 문자열)
            scenario_id: 시나리오 ID

        Returns:
            list[dict]: 메시지 목록
                - turn_index: 턴 인덱스
                - content: 메시지 내용
                - speaker: 발화자 (user/ai)
        """
        try:
            messages = await spring2_client.get_session_messages(session_id)
            logger.info(f"Session messages retrieved: session={session_id}, count={len(messages)}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get session messages: {e}")
            raise


def get_feedback_service() -> FeedbackService:
    """Feedback Service 인스턴스 반환"""
    return FeedbackService()
