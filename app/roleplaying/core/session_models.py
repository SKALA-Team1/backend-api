"""
Session State Models
====================

목적: 세션 상태를 표현하는 데이터 모델 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

주요 클래스:
    - SessionStatus: 세션 상태 (ACTIVE, FINISHED, ERROR)
    - Turn: 대화 턴 (사용자 또는 AI의 한 번의 발화)
    - SessionState: WebSocket 세션의 전체 상태
        • 세션 메타데이터 (ID, 사용자, 시나리오)
        • 대화 히스토리 (Turn 목록)
        • 오디오 버퍼 (현재 발화 오디오)
        • 턴 추적 (AI 턴, 사용자 턴)
        • 재시도 관리 (현재 질문, 재시도 횟수)
        • 피드백 기록

세션 라이프사이클:
    1. create_session() - 세션 생성
    2. 대화 중 - 메시지/오디오 추가, 턴 추적
    3. end_session() - 세션 종료
    4. cleanup() - 메모리 해제
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class SessionStatus(str, Enum):
    """세션 상태"""
    ACTIVE = "ACTIVE"        # 진행 중
    FINISHED = "FINISHED"    # 정상 종료
    ERROR = "ERROR"          # 오류로 종료


@dataclass
class Turn:
    """
    대화 턴 (사용자 또는 AI의 한 번의 발화)

    Attributes:
        speaker: "user" | "ai"
        text: 발화 내용 (사용자는 STT 결과, AI는 생성된 텍스트)
        timestamp: 발화 시각
        audio_s3_url: S3 URL (사용자 발화만, AI는 None)
        is_fixed_question: 고정 질문 여부 (AI만 해당)
    """
    speaker: str  # "user" | "ai"
    text: str
    timestamp: datetime
    audio_s3_url: Optional[str] = None
    is_fixed_question: bool = False


def _get_utc_now() -> datetime:
    """현재 UTC 시각을 timezone-aware datetime으로 반환"""
    return datetime.now(timezone.utc)


@dataclass
class SessionState:
    """
    WebSocket 세션의 상태

    Attributes:
        session_id: 세션 고유 ID
        user_id: 사용자 ID
        subject_id: 시나리오 주제 ID
        my_role: 사용자 직무 역할
        ai_role: AI 역할
        fixed_questions: 고정 질문 3개 (턴 1, 4, 7 사용)
        history: 대화 히스토리 (Turn 목록)
        status: 세션 상태
        created_at: 세션 생성 시각 (timezone-aware UTC)
        expires_at: 세션 만료 시각 (timezone-aware UTC)
        current_utterance_audio: 현재 발화 오디오 버퍼
        utterance_index: 발화 인덱스 (0부터 시작)
        ai_turn_count: AI 턴 카운트 (고정 질문 판단용)
        current_question_text: 현재 질문 보관 (재시도 시 사용)
        current_question_retry_count: 현재 질문 재시도 횟수
        max_retry_per_question: 질문당 최대 재시도 횟수
        feedback_history: 피드백 기록

    주의: 모든 datetime 필드는 timezone-aware (UTC)여야 합니다.
    """
    session_id: str
    user_id: int
    subject_id: int
    my_role: str
    ai_role: str
    fixed_questions: List[str]
    interaction_mode: str = "default"  # Add interaction mode
    voice_id: Optional[str] = None  # ElevenLabs Voice ID
    history: List[Turn] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=_get_utc_now)  # ✅ timezone-aware UTC
    expires_at: Optional[datetime] = None
    current_utterance_audio: bytes = b""
    utterance_index: int = 0
    ai_turn_count: int = 0  # AI가 질문한 횟수 (1부터 시작)
    user_turn_count: int = 0  # 사용자가 답한 횟수

    # ========================================
    # Feedback & Retry Fields
    # ========================================
    current_question_text: str = ""
    current_question_retry_count: int = 0
    max_retry_per_question: int = 3
    feedback_history: List[dict] = field(default_factory=list)

    def is_expired(self) -> bool:
        """세션 만료 여부 확인"""
        if self.expires_at is None:
            return False

        # UTC 기준 현재 시각 (timezone-aware)
        now = datetime.now(timezone.utc)

        # expires_at이 timezone-aware가 아니면 UTC로 간주
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def get_ai_turn_number(self) -> int:
        """
        다음 AI 턴 번호 반환 (1부터 시작)

        Returns:
            다음 AI 턴 번호 (1, 2, 3, ...)
        """
        return self.ai_turn_count + 1

    def should_use_fixed_question(self) -> bool:
        """
        다음 AI 턴이 고정 질문 턴인지 확인

        Returns:
            True if 턴 1, 4, 7
        """
        next_turn = self.get_ai_turn_number()
        return next_turn in [1, 4, 7]

    def get_fixed_question_index(self) -> Optional[int]:
        """
        다음 AI 턴의 고정 질문 인덱스 반환

        Returns:
            0 (턴 1), 1 (턴 4), 2 (턴 7), None (그 외)
        """
        next_turn = self.get_ai_turn_number()
        fixed_question_map = {
            1: 0,   # 대화 시작
            4: 1,   # 대화 중반
            7: 2    # 대화 마무리
        }
        return fixed_question_map.get(next_turn)

    def has_reached_turn_limit(self, max_turns: int) -> bool:
        """
        주어진 턴 수(AI 7번 질문 + 사용자 7번 답변) 이상 진행되었는지 판단

        AI가 max_turns번 질문하고 사용자가 max_turns번 답변한 후 세션 종료

        Args:
            max_turns: 허용된 최대 턴 수 (AI 질문 수와 사용자 답변 수)
        """
        # AI가 max_turns번 질문하고 사용자가 max_turns번 답변했는지 확인
        return self.ai_turn_count >= max_turns and self.user_turn_count >= max_turns

    # ========================================
    # Feedback & Retry Methods
    # ========================================
    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return self.current_question_retry_count < self.max_retry_per_question

    def increment_retry_count(self) -> None:
        """재시도 카운터 증가"""
        self.current_question_retry_count += 1

    def reset_retry_count(self) -> None:
        """다음 질문으로 진행 시 재시도 카운터 초기화"""
        self.current_question_retry_count = 0
