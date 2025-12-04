"""
📄 파일명: schemas.py
📌 역할: Pydantic 기반의 요청/응답 DTO 정의.
        - 피드백, 요약, 제안문, 점수 등 API 데이터 구조를 명세.
🧩 관련 모듈:
  - models.py: DB 모델 구조와 매핑
  - router.py: API 응답 및 요청 데이터 검증
🧠 주요 클래스:
  - FeedbackSummaryResponse: 피드백 요약 응답 DTO
  - MessageFeedbackResponse: 발화별 피드백 DTO
  - SuggestionDetailResponse: 교정 제안문 상세 DTO
  - TurnFeedbackResponse: 턴 단위 피드백 DTO
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ======================
# 요청 스키마
# ======================

class FeedbackRequest(BaseModel):
    """피드백 생성 요청"""
    session_id: str = Field(..., description="세션 ID")
    scenario_id: int = Field(..., description="시나리오 ID")
    audio_file_path: Optional[str] = Field(None, description="로컬 오디오 파일 경로")
    audio_url: Optional[str] = Field(None, description="S3 오디오 URL")


class TurnFeedbackRequest(BaseModel):
    """턴 단위 피드백 요청"""
    session_id: str = Field(..., description="세션 ID (UUID 문자열)")
    scenario_id: int = Field(..., description="시나리오 ID")
    turn_number: int = Field(..., description="턴 번호 (짝수만)")
    user_message: str = Field(..., description="사용자 발화 텍스트")
    system_message: str = Field(..., description="AI 발화 텍스트")
    audio_file_path: Optional[str] = Field(None, description="오디오 파일 경로")


# ======================
# 응답 스키마
# ======================

class ScoreDetail(BaseModel):
    """점수 상세"""
    score: float = Field(..., description="점수 (0-100)")
    level: str = Field(..., description="레벨 (A1-C2 또는 Low/Medium/High)")


class VocabularySuggestion(BaseModel):
    """어휘 제안"""
    original: str = Field(..., description="원본 단어/표현")
    suggested: str = Field(..., description="제안 단어/표현")
    reason: str = Field(..., description="제안 이유")


class SentenceFeedbackResponse(BaseModel):
    """문장 단위 피드백 응답"""
    sentence_index: int = Field(..., description="문장 인덱스")
    original_sentence: str = Field(..., description="원본 문장")
    pronunciation_note: Optional[str] = Field(None, description="발음 관련 노트")
    vocabulary_suggestion: Optional[str] = Field(None, description="어휘 제안 (JSON)")


class SimpleTurnFeedback(BaseModel):
    """턴별 간단 피드백 (추천 문장만)"""
    turn_number: int = Field(..., description="턴 번호")
    user_message: str = Field(..., description="사용자 발화")
    system_message: str = Field(..., description="AI 발화 (질문)")
    suggested_sentence: str = Field(..., description="추천 문장")


class TurnFeedbackResponse(BaseModel):
    """턴 단위 피드백 응답 (6개 항목)"""
    turn_feedback_id: int = Field(..., description="피드백 ID")
    turn_number: int = Field(..., description="턴 번호")

    # Azure 4가지 평가
    accuracy: ScoreDetail = Field(..., description="정확도")
    fluency: ScoreDetail = Field(..., description="유창성")
    completeness: ScoreDetail = Field(..., description="완성도")
    pronunciation: ScoreDetail = Field(..., description="발음")

    # LLM 2가지 피드백
    overall_feedback: str = Field(..., description="종합 피드백")
    suggested_sentence: str = Field(..., description="추천 문장")

    # 추가 정보
    user_message: str = Field(..., description="사용자 발화")
    system_message: str = Field(..., description="AI 발화")
    grammar_notes: list[str] = Field(default=[], description="문법 지적 사항")
    vocabulary_suggestions: list[VocabularySuggestion] = Field(
        default=[], description="어휘 제안"
    )

    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        from_attributes = True


class SessionFeedbackResponse(BaseModel):
    """세션 전체 피드백 응답"""
    session_id: int = Field(..., description="세션 ID")
    scenario_id: int = Field(..., description="시나리오 ID")
    total_turns: int = Field(..., description="총 평가된 턴 수")

    # 평균 점수
    avg_accuracy: float = Field(..., description="평균 정확도")
    avg_fluency: float = Field(..., description="평균 유창성")
    avg_completeness: float = Field(..., description="평균 완성도")
    avg_pronunciation: float = Field(..., description="평균 발음")
    overall_score: float = Field(..., description="종합 점수")

    # 턴별 피드백
    turn_feedbacks: list[TurnFeedbackResponse] = Field(..., description="턴별 피드백")

    # 전체 코멘트
    summary_comment: str = Field(..., description="전체 요약 코멘트")

    created_at: datetime = Field(..., description="생성 시간")


class FeedbackSummaryResponse(BaseModel):
    """피드백 요약 응답"""
    feedback_id: int
    session_id: str
    scenario_id: int
    total_pronunciation: float
    total_grammar: float
    total_diversity: float
    total_score: float
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageFeedbackResponse(BaseModel):
    """메시지 단위 피드백 응답"""
    feedback_id: int
    message_id: int
    session_id: str
    original_expression: Optional[str]
    suggested_expression: Optional[str]
    pronunciation: float
    grammar: float
    diversity: float
    score: float
    criterion: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BatchAudioFeedbackResponse(BaseModel):
    """배치 오디오 피드백 응답 - 전체 대화 종료 후 통합 피드백"""
    session_id: str = Field(..., description="세션 ID (UUID 문자열)")
    scenario_id: int = Field(..., description="시나리오 ID")
    total_files: int = Field(..., description="업로드된 총 파일 수")
    processed_count: int = Field(..., description="성공적으로 처리된 파일 수")
    failed_count: int = Field(..., description="실패한 파일 수")

    # ========== 턴별 추천 문장 (각 문장에 대한 간단 피드백) ==========
    turn_feedbacks: list[SimpleTurnFeedback] = Field(..., description="턴별 추천 문장 목록")

    # ========== 전체 대화 종료 후 통합 피드백 (아래 항목들은 마지막에 한 번만) ==========
    # Azure 4가지 평가 (평균)
    avg_accuracy: ScoreDetail = Field(..., description="평균 정확도")
    avg_fluency: ScoreDetail = Field(..., description="평균 유창성")
    avg_completeness: ScoreDetail = Field(..., description="평균 완성도")
    avg_pronunciation: ScoreDetail = Field(..., description="평균 발음")
    overall_score: float = Field(default=0.0, description="종합 점수 (4가지 평균)")

    # 최종 종합 피드백 (짧은 버전 + 긴 버전)
    final_feedback_short: str = Field(default="", description="짧은 피드백 (1-2문장)")
    final_feedback_long: str = Field(default="", description="긴 피드백 (7문장)")
