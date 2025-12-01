"""
📄 파일명: repository.py
📌 역할: 피드백 관련 DB 접근 로직을 캡슐화한 데이터 액세스 계층.
        - 조회, 생성, 업데이트 등 SQLAlchemy ORM을 이용한 CRUD 처리.
🧩 관련 모듈:
  - models.py: ORM 모델 참조
  - services/*.py: 서비스 계층에서 호출
🧠 주요 기능:
  - get_feedback_by_scenario(): 시나리오별 피드백 조회
  - save_feedback(): 새 피드백 데이터 저장
  - list_message_feedbacks(): 발화 단위 피드백 리스트 반환
  - save_turn_feedback(): 턴 단위 피드백 저장
  - get_turn_feedbacks_by_session(): 세션별 턴 피드백 조회
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.feedback.models import (
    ScenarioFeedback,
    ScenarioMessageFeedback,
    ScenarioTurnFeedback,
    ScenarioSentenceFeedback
)

logger = logging.getLogger(__name__)


class FeedbackRepository:
    """피드백 리포지토리"""

    def __init__(self, db: Session):
        self.db = db

    # ======================
    # ScenarioFeedback CRUD
    # ======================

    def get_feedback_by_session(self, session_id: str) -> Optional[ScenarioFeedback]:
        """세션 ID로 피드백 조회"""
        return self.db.query(ScenarioFeedback).filter(
            ScenarioFeedback.session_id == session_id
        ).first()

    def get_feedback_by_scenario(self, scenario_id: int) -> list[ScenarioFeedback]:
        """시나리오 ID로 피드백 목록 조회"""
        return self.db.query(ScenarioFeedback).filter(
            ScenarioFeedback.scenario_id == scenario_id
        ).all()

    def save_scenario_feedback(self, feedback: ScenarioFeedback) -> ScenarioFeedback:
        """시나리오 피드백 저장"""
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # ======================
    # ScenarioMessageFeedback CRUD
    # ======================

    def list_message_feedbacks(self, session_id: str) -> list[ScenarioMessageFeedback]:
        """세션의 메시지 피드백 목록 조회"""
        return self.db.query(ScenarioMessageFeedback).filter(
            ScenarioMessageFeedback.session_id == session_id
        ).all()

    def save_message_feedback(
        self, feedback: ScenarioMessageFeedback
    ) -> ScenarioMessageFeedback:
        """메시지 피드백 저장"""
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # ======================
    # ScenarioTurnFeedback CRUD
    # ======================

    def get_turn_feedback(
        self,
        session_id: int,
        turn_number: int
    ) -> Optional[ScenarioTurnFeedback]:
        """특정 턴의 피드백 조회"""
        return self.db.query(ScenarioTurnFeedback).filter(
            ScenarioTurnFeedback.session_id == session_id,
            ScenarioTurnFeedback.turn_number == turn_number
        ).first()

    def get_turn_feedbacks_by_session(
        self,
        session_id: int
    ) -> list[ScenarioTurnFeedback]:
        """세션의 모든 턴 피드백 조회"""
        return self.db.query(ScenarioTurnFeedback).filter(
            ScenarioTurnFeedback.session_id == session_id
        ).order_by(ScenarioTurnFeedback.turn_number).all()

    def save_turn_feedback(
        self,
        feedback: ScenarioTurnFeedback
    ) -> ScenarioTurnFeedback:
        """턴 피드백 저장"""
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def save_turn_feedback_with_sentences(
        self,
        turn_feedback: ScenarioTurnFeedback,
        sentence_feedbacks: list[dict]
    ) -> ScenarioTurnFeedback:
        """턴 피드백 + 문장 피드백 함께 저장"""
        self.db.add(turn_feedback)
        self.db.flush()  # turn_feedback_id 생성

        for idx, sf in enumerate(sentence_feedbacks):
            sentence = ScenarioSentenceFeedback(
                turn_feedback_id=turn_feedback.turn_feedback_id,
                sentence_index=idx,
                original_sentence=sf.get("original_sentence", ""),
                pronunciation_note=sf.get("pronunciation_note"),
                vocabulary_suggestion=json.dumps(
                    sf.get("vocabulary_suggestion", {}),
                    ensure_ascii=False
                ) if sf.get("vocabulary_suggestion") else None
            )
            self.db.add(sentence)

        self.db.commit()
        self.db.refresh(turn_feedback)
        return turn_feedback

    # ======================
    # ScenarioSentenceFeedback CRUD
    # ======================

    def get_sentence_feedbacks(
        self,
        turn_feedback_id: int
    ) -> list[ScenarioSentenceFeedback]:
        """턴의 문장 피드백 목록 조회"""
        return self.db.query(ScenarioSentenceFeedback).filter(
            ScenarioSentenceFeedback.turn_feedback_id == turn_feedback_id
        ).order_by(ScenarioSentenceFeedback.sentence_index).all()

    def save_sentence_feedback(
        self,
        feedback: ScenarioSentenceFeedback
    ) -> ScenarioSentenceFeedback:
        """문장 피드백 저장"""
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # ======================
    # 통계/집계 메서드
    # ======================

    def get_session_average_scores(self, session_id: int) -> dict:
        """세션의 평균 점수 계산"""
        feedbacks = self.get_turn_feedbacks_by_session(session_id)

        if not feedbacks:
            return {
                "avg_accuracy": 0.0,
                "avg_fluency": 0.0,
                "avg_completeness": 0.0,
                "avg_pronunciation": 0.0,
                "overall_score": 0.0,
                "total_turns": 0
            }

        total = len(feedbacks)
        avg_accuracy = sum(f.accuracy_score for f in feedbacks) / total
        avg_fluency = sum(f.fluency_score for f in feedbacks) / total
        avg_completeness = sum(f.coherence_score for f in feedbacks) / total
        avg_pronunciation = sum(f.phonological_control_score for f in feedbacks) / total
        overall = (avg_accuracy + avg_fluency + avg_completeness + avg_pronunciation) / 4

        return {
            "avg_accuracy": round(avg_accuracy, 2),
            "avg_fluency": round(avg_fluency, 2),
            "avg_completeness": round(avg_completeness, 2),
            "avg_pronunciation": round(avg_pronunciation, 2),
            "overall_score": round(overall, 2),
            "total_turns": total
        }
