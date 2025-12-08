"""
Session Manager Base
====================

목적: WebSocket 세션 상태 관리 및 생명주기 관리 (공통 메서드)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

책임:
    - 세션 생성/조회/종료/정리
    - 세션별 동시성 제어 (asyncio.Lock)
    - 활성 세션 관리

메서드:
    - create_session(): 새 세션 생성
    - get_session(): 세션 조회
    - _get_lock(): 세션별 Lock 반환
    - end_session(): 세션 종료
    - cleanup(): 세션 메모리 해제
    - get_active_sessions_count(): 활성 세션 개수
    - get_all_sessions_count(): 전체 세션 개수

스레드 안전성:
    - 각 세션마다 asyncio.Lock을 할당하여 상태 수정 작업 보호
    - concurrent 태스크에서 race condition 방지
"""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from datetime import datetime

from app.roleplaying.core.session_models import SessionState, SessionStatus

logger = logging.getLogger(__name__)


class SessionManager:
    """
    WebSocket 세션 상태 관리자

    인메모리 딕셔너리로 세션 상태를 관리합니다.
    향후 Redis로 전환 가능하도록 설계되었습니다.

    스레드 안전성:
    - 각 세션마다 asyncio.Lock을 할당하여 상태 수정 작업 보호
    - concurrent 태스크에서 race condition 방지
    """

    def __init__(self):
        """SessionManager 초기화"""
        self._sessions: Dict[str, SessionState] = {}
        self._session_locks: defaultdict = defaultdict(asyncio.Lock)  # 세션별 Lock (자동 생성)
        logger.info("SessionManager initialized")

    def create_session(
        self,
        session_id: str,
        user_id: int,
        subject_id: int,
        my_role: str,
        ai_role: str,
        fixed_questions: List[str],
        expires_at: Optional[datetime] = None,
        interaction_mode: str = "default"  # Add interaction mode
    ) -> SessionState:
        """
        새 세션 생성

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            subject_id: 시나리오 주제 ID
            my_role: 사용자 역할
            ai_role: AI 역할
            fixed_questions: 고정 질문 3개
            expires_at: 세션 만료 시각 (옵션)
            interaction_mode: 상호작용 모드 (default, handsfree)

        Returns:
            생성된 SessionState

        Raises:
            ValueError: 세션이 이미 존재하는 경우
        """
        if session_id in self._sessions:
            raise ValueError(f"Session {session_id} already exists")

        if len(fixed_questions) != 3:
            raise ValueError(f"fixedQuestions must contain exactly 3 questions, got {len(fixed_questions)}")

        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            subject_id=subject_id,
            my_role=my_role,
            ai_role=ai_role,
            fixed_questions=fixed_questions,
            expires_at=expires_at,
            interaction_mode=interaction_mode  # Pass interaction mode
        )

        self._sessions[session_id] = session
        logger.info(
            f"Session created: {session_id}, user={user_id}, "
            f"subject={subject_id}, role={my_role} → {ai_role}"
        )

        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            SessionState 또는 None (존재하지 않으면)
        """
        return self._sessions.get(session_id)

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """
        세션별 Lock 반환 (없으면 자동 생성)

        - Race condition 방지를 위한 세션 상태 접근 제어
        - defaultdict를 사용하여 Lock 자동 생성

        Args:
            session_id: 세션 ID

        Returns:
            해당 세션의 asyncio.Lock
        """
        return self._session_locks[session_id]

    def end_session(self, session_id: str, reason: str) -> None:
        """
        세션 종료

        Args:
            session_id: 세션 ID
            reason: 종료 사유 (user_end, timeout, disconnected, error)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if reason == "error":
            session.status = SessionStatus.ERROR
        else:
            session.status = SessionStatus.FINISHED

        logger.info(
            f"Session ended: {session_id}, reason={reason}, "
            f"turns={len(session.history)}, ai_turns={session.ai_turn_count}"
        )

    def cleanup(self, session_id: str) -> None:
        """
        세션 메모리에서 제거 (세션과 Lock 포함)

        Args:
            session_id: 세션 ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

        # 세션 Lock도 함께 정리
        if session_id in self._session_locks:
            del self._session_locks[session_id]

        logger.info(f"Session cleaned up: {session_id}")

    def get_active_sessions_count(self) -> int:
        """
        활성 세션 개수 반환

        Returns:
            활성 세션 개수
        """
        return len([s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE])

    def get_all_sessions_count(self) -> int:
        """
        전체 세션 개수 반환 (종료된 세션 포함)

        Returns:
            전체 세션 개수
        """
        return len(self._sessions)


# 전역 SessionManager 인스턴스 (FastAPI 앱에서 사용)
session_manager = SessionManager()
