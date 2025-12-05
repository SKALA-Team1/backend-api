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
        # 주석처리: 롤플레잉에서 이미 생성한 피드백을 가져오므로 음성 평가 비활성화
        pronunciation_result: Optional[PronunciationResult] = None

        # if request.audio_file_path:
        #     try:
        #         azure_service = self._get_azure_service()
        #         pronunciation_result = azure_service.evaluate_pronunciation_from_file(
        #             audio_file_path=request.audio_file_path,
        #             reference_text=request.user_message
        #         )
        #         logger.info(f"Azure evaluation completed for turn {request.turn_number}")
        #     except Exception as e:
        #         logger.error(f"Azure evaluation failed: {e}")

        # 2. OpenAI 피드백 생성
        # 주석처리: 롤플레잉에서 이미 생성한 피드백을 가져오므로 OpenAI 피드백 생성 비활성화
        # openai_service = self._get_openai_service()
        # feedback_result: FeedbackResult = openai_service.generate_feedback(
        #     user_text=request.user_message,
        #     ai_prompt_text=request.system_message,
        #     pronunciation_result=pronunciation_result
        # )

        # 임시로 빈 FeedbackResult 생성 (실제로는 롤플레잉에서 가져온 데이터 사용)
        from app.feedback.services.openai_feedback_service import FeedbackResult
        feedback_result = FeedbackResult(
            overall_feedback="",
            suggested_sentence="",
            grammar_notes=[],
            vocabulary_suggestions=[]
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
        session_id: str,
        scenario_id: int
    ) -> SessionFeedbackResponse:
        """
        세션 전체 피드백 조회 및 생성

        scenario_message 테이블에서 메시지를 가져와서 평균 점수 계산 후 종합 피드백 생성

        Args:
            session_id: 세션 ID (UUID 문자열)
            scenario_id: 시나리오 ID

        Returns:
            SessionFeedbackResponse: 세션 전체 피드백
        """
        # Spring2에서 사용자 메시지만 조회 (scenario_message 테이블, speaker="user" 필터링)
        try:
            user_messages = await spring2_client.get_session_messages(session_id, speaker="user")
            logger.info(f"Retrieved {len(user_messages)} user messages for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to get messages from Spring: {e}")
            user_messages = []

        # 턴별 응답 생성 (scenario_message의 점수 필드 사용)
        turn_responses = []
        total_accuracy = 0.0
        total_fluency = 0.0
        total_completeness = 0.0
        total_pronunciation = 0.0

        # 점수가 있는 메시지만 필터링해서 평균 계산
        scored_count = 0

        for msg in user_messages:
            # scenario_message의 점수 필드 (NULL 처리)
            pronunciation_raw = msg.get("pronunciation_score")
            grammar_raw = msg.get("grammar_score")
            relevance_raw = msg.get("relevance_score")

            # NULL이 아닌 값만 사용 (0은 유효한 점수)
            pronunciation_score = float(pronunciation_raw) if pronunciation_raw is not None else 0.0
            grammar_score = float(grammar_raw) if grammar_raw is not None else 0.0
            relevance_score = float(relevance_raw) if relevance_raw is not None else 0.0

            # 점수가 하나라도 있으면 카운트
            if pronunciation_raw is not None or grammar_raw is not None or relevance_raw is not None:
                scored_count += 1

                # Azure 4가지 평가 항목으로 매핑
                accuracy_score = grammar_score  # 문법 = 정확도
                fluency_score = relevance_score  # 적합성 = 유창성 (근사값)
                completeness_score = relevance_score  # 적합성 = 완성도

                total_accuracy += accuracy_score
                total_fluency += fluency_score
                total_completeness += completeness_score
                total_pronunciation += pronunciation_score
            else:
                # 점수가 없으면 기본값 사용
                accuracy_score = 0.0
                fluency_score = 0.0
                completeness_score = 0.0
                pronunciation_score = 0.0

            # feedback_sections에서 상세 피드백 추출 (있으면)
            feedback_sections = msg.get("feedback_sections", [])
            overall_feedback = ""
            if feedback_sections and isinstance(feedback_sections, list):
                # 피드백 섹션들을 하나의 문자열로 결합
                feedback_texts = [f.get("feedback_en", "") for f in feedback_sections if isinstance(f, dict)]
                overall_feedback = " ".join([t for t in feedback_texts if t])

            # 점수를 레벨로 변환
            def score_to_level(score: float) -> str:
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

            turn_responses.append(TurnFeedbackResponse(
                turn_feedback_id=msg.get("message_id", 0),
                turn_number=msg.get("turn_index", 0),
                accuracy=ScoreDetail(
                    score=accuracy_score,
                    level=score_to_level(accuracy_score)
                ),
                fluency=ScoreDetail(
                    score=fluency_score,
                    level=score_to_level(fluency_score)
                ),
                completeness=ScoreDetail(
                    score=completeness_score,
                    level=score_to_level(completeness_score)
                ),
                pronunciation=ScoreDetail(
                    score=pronunciation_score,
                    level=score_to_level(pronunciation_score)
                ),
                overall_feedback=overall_feedback or "No feedback available",
                suggested_sentence="",  # scenario_message에는 suggested_sentence 없음
                user_message=msg.get("message_text", ""),
                system_message="",  # AI 메시지는 별도 조회 필요
                grammar_notes=[],
                vocabulary_suggestions=[],
                created_at=datetime.fromisoformat(msg["created_at"].replace("Z", "+00:00")) if msg.get("created_at") else datetime.utcnow()
            ))

        # 평균 점수 계산 (점수가 있는 메시지만)
        total_turns = len(user_messages)
        if scored_count > 0:
            avg_accuracy = round(total_accuracy / scored_count, 2)
            avg_fluency = round(total_fluency / scored_count, 2)
            avg_completeness = round(total_completeness / scored_count, 2)
            avg_pronunciation = round(total_pronunciation / scored_count, 2)
            overall_score = round((avg_accuracy + avg_fluency + avg_completeness + avg_pronunciation) / 4, 2)
            logger.info(f"Calculated averages from {scored_count} scored messages out of {total_turns} total messages")
        else:
            avg_accuracy = avg_fluency = avg_completeness = avg_pronunciation = overall_score = 0.0
            logger.warning(f"No scored messages found in {total_turns} total messages")

        avg_scores = {
            "avg_accuracy": avg_accuracy,
            "avg_fluency": avg_fluency,
            "avg_completeness": avg_completeness,
            "avg_pronunciation": avg_pronunciation,
            "overall_score": overall_score,
            "total_turns": total_turns
        }

        # 현재 세션의 feedback_sections만 사용
        turn_feedbacks = []
        for msg in user_messages:
            feedback_sections = msg.get("feedback_sections", [])
            if feedback_sections:
                turn_feedbacks.append({
                    "turn_index": msg.get("turn_index", 0),
                    "message_text": msg.get("content", ""),
                    "feedback_sections": feedback_sections
                })
        logger.info(f"Using {len(turn_feedbacks)} feedback_sections from current session {session_id}")

        # OpenAI로 멘토 스타일 종합 피드백 생성 (슬랙 메시지 톤)
        try:
            openai_service = self._get_openai_service()
            feedback_dict = openai_service.generate_final_feedback(
                avg_scores=avg_scores,
                turn_feedbacks=turn_feedbacks  # 현재 세션의 feedback_sections만
            )
            # 짧은 버전과 긴 버전 모두 추출
            final_feedback_short = feedback_dict.get("short", "")
            final_feedback_long = feedback_dict.get("long", "")
            summary_comment = final_feedback_short  # summary_comment는 짧은 버전 사용
            logger.info(f"Final feedback generated via LLM for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to generate LLM final feedback: {e}")
            # LLM 실패 시 기본 코멘트 사용
            summary_comment = self._generate_summary_comment(avg_scores)
            final_feedback_short = summary_comment
            final_feedback_long = ""

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
            final_feedback_short=final_feedback_short,
            final_feedback_long=final_feedback_long,
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

    async def get_all_feedbacks(self) -> list[dict]:
        """
        모든 세션의 모든 피드백 조회 (세션 구분 없이 통합)

        scenario_message 테이블에서 feedback_sections가 있는 모든 user 메시지를 가져옵니다.
        FastAPI는 READ-ONLY이므로 직접 DB에서 읽어옵니다.

        Returns:
            list[dict]: 피드백 목록
                - turn_index: 턴 인덱스
                - message_text: 메시지 내용
                - feedback_sections: 피드백 섹션들
                - grammar_score, relevance_score, overall_score
        """
        import pymysql
        import json

        try:
            # DATABASE_URL 파싱: mysql+pymysql://root:9799@localhost:3306/skuseme_db_2
            db_url = settings.DATABASE_URL
            # 'mysql+pymysql://' 제거
            db_url = db_url.replace('mysql+pymysql://', '')
            # 'root:9799@localhost:3306/skuseme_db_2' 형태
            user_pass, host_db = db_url.split('@')
            user, password = user_pass.split(':')
            host_port, database = host_db.split('/')
            host, port = host_port.split(':')

            # DB 연결
            conn = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=int(port)
            )

            cursor = conn.cursor()

            # scenario_message에서 feedback_sections가 있는 모든 user 메시지 조회
            cursor.execute('''
                SELECT
                    turn_index, message_text,
                    pronunciation_score, grammar_score, relevance_score, overall_score,
                    feedback_sections
                FROM scenario_message
                WHERE speaker = 'user' AND feedback_sections IS NOT NULL
                ORDER BY created_at, turn_index
            ''')

            results = cursor.fetchall()

            feedbacks = []
            for row in results:
                feedback_sections = json.loads(row[6]) if row[6] else []
                feedbacks.append({
                    'turn_index': row[0],
                    'message_text': row[1],
                    'pronunciation_score': row[2],
                    'grammar_score': row[3],
                    'relevance_score': row[4],
                    'overall_score': row[5],
                    'feedback_sections': feedback_sections
                })

            conn.close()

            logger.info(f"All feedbacks retrieved from DB (READ-ONLY): count={len(feedbacks)}")
            return feedbacks

        except Exception as e:
            logger.error(f"Failed to get all feedbacks from DB: {e}")
            return []


def get_feedback_service() -> FeedbackService:
    """Feedback Service 인스턴스 반환"""
    return FeedbackService()
