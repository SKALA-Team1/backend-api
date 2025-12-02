"""
Session Message Handler
=======================

목적: 세션의 텍스트 메시지 처리 (비동기, 스레드 안전)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

책임:
    - 대화 히스토리에 메시지 추가
    - 발화 인덱스 관리
    - 동시성 제어 (asyncio.Lock)

메서드:
    - append_message_async(): 메시지 추가 (비동기, 스레드 안전)
    - increment_utterance_index_async(): 발화 인덱스 증가 (비동기, 스레드 안전)

동시성 모델:
    - asyncio.Lock을 사용하여 race condition 방지
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from app.roleplaying.core.session_models import SessionState, Turn
from app.roleplaying.core.session_manager_base import session_manager

logger = logging.getLogger(__name__)


class SessionMessageHandler:
    """세션 텍스트 메시지 처리"""

    @staticmethod
    async def append_message_async(
        session_id: str,
        speaker: str,
        text: str,
        audio_s3_url: Optional[str] = None,
        is_fixed_question: bool = False
    ) -> None:
        """
        대화 히스토리에 메시지 추가 (비동기, 스레드 안전)

        - Race condition 방지: asyncio.Lock 사용

        Args:
            session_id: 세션 ID
            speaker: "user" | "ai"
            text: 발화 텍스트
            audio_s3_url: S3 URL (사용자 발화만)
            is_fixed_question: 고정 질문 여부 (AI만)

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        lock = session_manager._get_lock(session_id)
        async with lock:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            turn = Turn(
                speaker=speaker,
                text=text,
                timestamp=datetime.now(timezone.utc),  # timezone-aware UTC
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

    @staticmethod
    async def increment_utterance_index_async(session_id: str) -> int:
        """
        발화 인덱스 증가 (비동기, 스레드 안전)

        - Race condition 방지: asyncio.Lock 사용

        Args:
            session_id: 세션 ID

        Returns:
            증가된 발화 인덱스

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        lock = session_manager._get_lock(session_id)
        async with lock:
            session = session_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            session.utterance_index += 1
            logger.debug(f"Utterance index incremented for session {session_id}: {session.utterance_index}")

            return session.utterance_index
