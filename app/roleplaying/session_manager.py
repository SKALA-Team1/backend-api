"""
SessionManager
==============
WebSocket 세션의 상태를 인메모리에서 관리하는 매니저 클래스.

책임:
- 세션 생성/조회/종료/정리
- 대화 히스토리 관리
- 오디오 버퍼 관리
- AI 턴 번호 추적 (고정 질문 판단용)

세션 라이프사이클:
1. create_session() - WebSocket 연결 시
2. append_message() / append_audio_chunk() - 대화 중
3. end_session() - 세션 종료 시
4. cleanup() - 메모리에서 제거
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


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
        fixed_questions: 고정 질문 3개 (턴 1, 5, 10 사용)
        history: 대화 히스토리 (Turn 목록)
        status: 세션 상태
        created_at: 세션 생성 시각
        expires_at: 세션 만료 시각
        current_utterance_audio: 현재 발화 오디오 버퍼
        utterance_index: 발화 인덱스 (0부터 시작)
        ai_turn_count: AI 턴 카운트 (고정 질문 판단용)
    """
    session_id: str
    user_id: int
    subject_id: int
    my_role: str
    ai_role: str
    fixed_questions: List[str]
    history: List[Turn] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    current_utterance_audio: bytes = b""
    utterance_index: int = 0
    ai_turn_count: int = 0  # AI가 질문한 횟수 (1부터 시작)
    user_turn_count: int = 0  # 사용자가 답한 횟수

    def is_expired(self) -> bool:
        """세션 만료 여부 확인"""
        if self.expires_at is None:
            return False

        # UTC 기준 현재 시각 (timezone-aware)
        from datetime import timezone
        now = datetime.now(timezone.utc)

        # expires_at이 timezone-aware가 아니면 UTC로 간주
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            from datetime import timezone
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
            True if 턴 1, 5, 10
        """
        next_turn = self.get_ai_turn_number()
        return next_turn in [1, 5, 10]

    def get_fixed_question_index(self) -> Optional[int]:
        """
        다음 AI 턴의 고정 질문 인덱스 반환

        Returns:
            0 (턴 1), 1 (턴 5), 2 (턴 10), None (그 외)
        """
        next_turn = self.get_ai_turn_number()
        fixed_question_map = {
            1: 0,   # 대화 시작
            5: 1,   # 대화 흐름 전환
            10: 2   # 대화 마무리
        }
        return fixed_question_map.get(next_turn)

    def has_reached_turn_limit(self, max_turns: int) -> bool:
        """
        주어진 턴 수(사용자+AI 쌍) 이상 진행되었는지 판단

        Args:
            max_turns: 허용된 최대 턴 수 (AI+사용자 = 2개의 메시지)
        """
        turn_pair_limit = (
            self.ai_turn_count >= max_turns and self.user_turn_count >= max_turns
        )
        message_limit = self.utterance_index >= max_turns * 2
        return turn_pair_limit or message_limit


class SessionManager:
    """
    WebSocket 세션 상태 관리자

    인메모리 딕셔너리로 세션 상태를 관리합니다.
    향후 Redis로 전환 가능하도록 설계되었습니다.
    """

    def __init__(self):
        """SessionManager 초기화"""
        self._sessions: Dict[str, SessionState] = {}
        logger.info("SessionManager initialized")

    def create_session(
        self,
        session_id: str,
        user_id: int,
        subject_id: int,
        my_role: str,
        ai_role: str,
        fixed_questions: List[str],
        expires_at: Optional[datetime] = None
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
            expires_at=expires_at
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

    def append_message(
        self,
        session_id: str,
        speaker: str,
        text: str,
        audio_s3_url: Optional[str] = None,
        is_fixed_question: bool = False
    ) -> None:
        """
        대화 히스토리에 메시지 추가

        Args:
            session_id: 세션 ID
            speaker: "user" | "ai"
            text: 발화 텍스트
            audio_s3_url: S3 URL (사용자 발화만)
            is_fixed_question: 고정 질문 여부 (AI만)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        turn = Turn(
            speaker=speaker,
            text=text,
            timestamp=datetime.utcnow(),
            audio_s3_url=audio_s3_url,
            is_fixed_question=is_fixed_question
        )

        session.history.append(turn)

        # AI 턴인 경우 카운트 증가
        if speaker == "ai":
            session.ai_turn_count += 1
        elif speaker == "user":
            session.user_turn_count += 1

        logger.debug(
            f"Message added to session {session_id}: {speaker} "
            f"(turn {session.ai_turn_count if speaker == 'ai' else 'N/A'})"
        )

    def append_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        """
        현재 발화에 오디오 청크 추가

        Args:
            session_id: 세션 ID
            chunk: 오디오 청크 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.current_utterance_audio += chunk
        logger.debug(
            f"Audio chunk added to session {session_id}: "
            f"{len(chunk)} bytes (total: {len(session.current_utterance_audio)} bytes)"
        )

    def get_current_audio(self, session_id: str) -> bytes:
        """
        현재 발화 오디오 반환 후 버퍼 초기화

        Args:
            session_id: 세션 ID

        Returns:
            누적된 오디오 데이터 (bytes)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        audio = session.current_utterance_audio
        session.current_utterance_audio = b""  # 버퍼 초기화

        logger.debug(f"Audio retrieved from session {session_id}: {len(audio)} bytes")
        return audio

    def clear_audio_buffer(self, session_id: str) -> None:
        """
        현재 발화 오디오 버퍼 초기화

        Args:
            session_id: 세션 ID

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.current_utterance_audio = b""
        logger.debug(f"Audio buffer cleared for session {session_id}")

    def increment_utterance_index(self, session_id: str) -> int:
        """
        발화 인덱스 증가

        Args:
            session_id: 세션 ID

        Returns:
            증가된 발화 인덱스

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.utterance_index += 1
        logger.debug(f"Utterance index incremented for session {session_id}: {session.utterance_index}")

        return session.utterance_index

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
        세션 메모리에서 제거

        Args:
            session_id: 세션 ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
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
