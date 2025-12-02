"""
SessionManager
==============

목적: WebSocket 세션의 상태를 인메모리에서 관리하는 매니저
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

책임:
    - 세션 생성/조회/종료/정리
    - 대화 히스토리 관리
    - 오디오 버퍼 관리
    - AI 턴 번호 추적 (고정 질문 판단용)
    - 세션 상태 동시성 제어 (asyncio.Lock)

세션 라이프사이클:
    1. create_session() - WebSocket 연결 시
    2. append_message_async() / append_audio_chunk() - 대화 중 (비동기)
    3. end_session() - 세션 종료 시
    4. cleanup() - 메모리에서 제거

동시성 모델:
    - 각 세션마다 asyncio.Lock을 할당하여 상태 수정 작업 보호
    - 다중 concurrent 태스크에서 race condition 방지

모듈 구조:
    - session_models.py: 데이터 모델 (SessionStatus, Turn, SessionState)
    - session_manager_base.py: SessionManager 공통 메서드
    - session_message_handler.py: 텍스트 메시지 처리
    - session_audio_handler.py: 오디오 처리
"""

# ============================================
# 모듈 가져오기 (기존 호환성 유지)
# ============================================

from app.roleplaying.core.session_models import (
    SessionStatus,
    Turn,
    SessionState,
    _get_utc_now
)

from app.roleplaying.core.session_manager_base import (
    SessionManager,
    session_manager
)

from app.roleplaying.core.session_message_handler import (
    SessionMessageHandler
)

from app.roleplaying.core.session_audio_handler import (
    SessionAudioHandler
)

# ============================================
# 공개 API (backward compatibility)
# ============================================

__all__ = [
    # Models
    "SessionStatus",
    "Turn",
    "SessionState",
    "_get_utc_now",
    # Manager
    "SessionManager",
    "session_manager",
    # Handlers
    "SessionMessageHandler",
    "SessionAudioHandler",
]
