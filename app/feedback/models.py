"""
📄 파일명: models.py
📌 역할: 피드백 도메인의 데이터베이스 모델 정의.
        - 시나리오 피드백 및 메시지 피드백 테이블을 ORM으로 매핑.
🧩 관련 테이블:
  - scenario_feedback
  - scenario_message_feedback
  - scenario_turn_feedback
  - scenario_sentence_feedback
🧠 주요 클래스:
  - ScenarioFeedback: 시나리오 단위 점수 및 총평 저장
  - ScenarioMessageFeedback: 각 발화(메시지) 단위의 세부 피드백 저장
  - ScenarioTurnFeedback: 턴 단위 Azure 평가 + LLM 피드백
  - ScenarioSentenceFeedback: 문장 단위 세부 피드백
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Integer, String, Text, DECIMAL,
    DateTime, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScenarioFeedback(Base):
    """시나리오 전체 피드백"""
    __tablename__ = "scenario_feedback"

    feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_pronunciation: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    total_grammar: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    total_diversity: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    total_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScenarioMessageFeedback(Base):
    """메시지 단위 피드백"""
    __tablename__ = "scenario_message_feedback"

    feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    original_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pronunciation: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    grammar: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    diversity: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    criterion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScenarioTurnFeedback(Base):
    """
    턴 단위 피드백 (Azure 발음 평가 + LLM 피드백)

    평가 항목:
        - accuracy: 정확도 (Azure)
        - fluency: 유창성 (Azure)
        - phonological_control: 발음 (Azure)
        - coherence: 완성도/일관성 (Azure)
        - range: 어휘 다양성 (LLM)
        - overall: 종합 점수
    """
    __tablename__ = "scenario_turn_feedback"

    turn_feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    scenario_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 사용자/AI 메시지
    user_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Azure 평가 점수 (0-100)
    accuracy_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    accuracy_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    fluency_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    fluency_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    phonological_control_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    phonological_control_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    coherence_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    coherence_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    range_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    range_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    overall_score: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.0)
    overall_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # LLM 종합 피드백
    feedback_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 상세 평가 JSON (단어별 분석 등)
    evaluation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(6), default=datetime.utcnow)

    # 관계
    sentence_feedbacks: Mapped[list["ScenarioSentenceFeedback"]] = relationship(
        "ScenarioSentenceFeedback",
        back_populates="turn_feedback",
        cascade="all, delete-orphan"
    )


class ScenarioSentenceFeedback(Base):
    """
    문장 단위 세부 피드백 (추천 문장, 어휘 제안)
    """
    __tablename__ = "scenario_sentence_feedback"

    sentence_feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    turn_feedback_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("scenario_turn_feedback.turn_feedback_id"),
        nullable=False
    )
    sentence_index: Mapped[int] = mapped_column(Integer, default=0)

    # 원본 문장
    original_sentence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 발음 관련 노트
    pronunciation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 어휘/표현 제안 (JSON 형태로 저장 가능)
    vocabulary_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(6), default=datetime.utcnow)

    # 관계
    turn_feedback: Mapped["ScenarioTurnFeedback"] = relationship(
        "ScenarioTurnFeedback",
        back_populates="sentence_feedbacks"
    )
