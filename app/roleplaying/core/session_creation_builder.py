"""
Session Creation Builder
=========================

목적: 세션 생성 요청을 Fluent API로 구성하는 빌더 패턴 구현
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

주요 클래스:
    - SessionCreationRequest: Fluent API로 세션 생성 요청 구성
      • with_session_id(session_id): 세션 ID 설정
      • with_user_id(user_id): 사용자 ID 설정
      • with_subject_id(subject_id): 시나리오 주제 ID 설정
      • with_roles(my_role, ai_role): 역할 설정
      • with_fixed_questions(questions): 고정 질문 설정 (정확히 3개)
      • with_expiration(expires_at): 만료 시각 설정
      • validate(): 유효성 검증
      • build(): 세션 생성 실행

책임:
    - 세션 생성 요청 매개변수 구성
    - 입력 유효성 검증
    - session_manager.create_session() 호출

사용 예시:
    builder = SessionCreationRequest()
    session = builder.with_session_id("session-123") \\
                     .with_user_id(456) \\
                     .with_subject_id(789) \\
                     .with_roles("Software Engineer", "Tech Lead") \\
                     .with_fixed_questions(["q1", "q2", "q3"]) \\
                     .with_expiration(datetime.now() + timedelta(hours=1)) \\
                     .validate() \\
                     .build()
"""

import logging
from typing import List, Optional
from datetime import datetime

from app.roleplaying.core.session_state_manager import session_manager

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