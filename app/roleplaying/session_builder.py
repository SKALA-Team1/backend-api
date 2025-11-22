"""
세션 생성 빌더 패턴
===============================================

역할:
- 세션 생성 요청 객체화
- Builder 패턴으로 파라미터 축소
- 유효성 검증
"""

from datetime import datetime
from typing import List, Optional
import logging

from app.roleplaying.session_manager import session_manager

logger = logging.getLogger(__name__)


class SessionCreationRequest:
    """세션 생성 요청"""

    def __init__(self):
        self.session_id: Optional[str] = None
        self.user_id: Optional[int] = None
        self.subject_id: Optional[int] = None
        self.my_role: Optional[str] = None
        self.ai_role: Optional[str] = None
        self.fixed_questions: List[str] = []
        self.expires_at: Optional[datetime] = None

    def with_session_id(self, session_id: str) -> "SessionCreationRequest":
        """세션 ID 설정"""
        self.session_id = session_id
        return self

    def with_user_id(self, user_id: int) -> "SessionCreationRequest":
        """사용자 ID 설정"""
        self.user_id = user_id
        return self

    def with_subject_id(self, subject_id: int) -> "SessionCreationRequest":
        """주제 ID 설정"""
        self.subject_id = subject_id
        return self

    def with_roles(self, my_role: str, ai_role: str) -> "SessionCreationRequest":
        """역할 설정"""
        self.my_role = my_role
        self.ai_role = ai_role
        return self

    def with_fixed_questions(self, questions: List[str]) -> "SessionCreationRequest":
        """고정 질문 설정 (반드시 3개)"""
        if len(questions) != 3:
            raise ValueError(f"Fixed questions must contain exactly 3 questions, got {len(questions)}")
        self.fixed_questions = questions
        return self

    def with_expiration(self, expires_at: Optional[datetime]) -> "SessionCreationRequest":
        """만료 시각 설정"""
        self.expires_at = expires_at
        return self

    def validate(self) -> None:
        """유효성 검증"""
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.user_id is None:
            raise ValueError("user_id is required")
        if self.subject_id is None:
            raise ValueError("subject_id is required")
        if not self.my_role:
            raise ValueError("my_role is required")
        if not self.ai_role:
            raise ValueError("ai_role is required")
        if len(self.fixed_questions) != 3:
            raise ValueError("fixed_questions must contain exactly 3 questions")

    def build(self):
        """세션 생성"""
        self.validate()
        return session_manager.create_session(
            session_id=self.session_id,
            user_id=self.user_id,
            subject_id=self.subject_id,
            my_role=self.my_role,
            ai_role=self.ai_role,
            fixed_questions=self.fixed_questions,
            expires_at=self.expires_at,
        )


def create_session_builder() -> SessionCreationRequest:
    """빌더 팩토리"""
    return SessionCreationRequest()