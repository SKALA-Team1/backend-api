"""
Session Service (Legacy Compatibility Layer)
=============================================
⚠️ DEPRECATED: 하위 호환성을 위해 유지됩니다.

마이그레이션 가이드:
    기존: from app.roleplaying.services.session_service import session_service
    신규: from app.roleplaying.services.dependencies import SessionRepositoryDep, ScenarioRepositoryDep

구조:
    - SessionService: 레거시 호환성 Facade
    - 내부적으로 session_service_refactored의 구현체들을 위임
    - 모든 메서드는 Deprecated 경고 발생
    - 기능은 동일하게 유지

목표:
    - 기존 코드 파괴 방지
    - 점진적 마이그레이션 지원
    - 새 코드는 repositories + session_service_refactored 직접 사용
"""

import warnings
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.roleplaying.schemas import ScenarioDetail

logger = logging.getLogger(__name__)


class SessionService:
    """⚠️ DEPRECATED: 세션 관리 서비스 (레거시)

    마이그레이션:
        SessionService().setup_session(...)
        → SessionServiceImpl(...).setup_session(...)
    """

    def __init__(self):
        """
        SessionService 초기화

        ⚠️ Deprecated: 새 코드는 session_service_refactored의 구현체 직접 사용
        """
        warnings.warn(
            "SessionService is deprecated. Use specific implementations:\\n"
            "- SessionServiceImpl for session setup and management\\n"
            "- RedisSessionRepository for session CRUD\\n"
            "- DatabaseScenarioRepository for scenario queries\\n"
            "Import from app.roleplaying.services.session_service_refactored "
            "or app.roleplaying.services.repositories",
            DeprecationWarning,
            stacklevel=2
        )

        # Lazy import to avoid circular dependency
        self._impl = None
        logger.info("SessionService initialized (legacy compatibility layer)")

    async def _get_impl(self):
        """구현체 지연 초기화"""
        if self._impl is None:
            from app.roleplaying.services.dependencies import (
                get_session_repository,
                get_scenario_repository
            )
            from app.roleplaying.services.session_service_refactored import SessionServiceImpl

            session_repo = get_session_repository()
            scenario_repo = get_scenario_repository()
            self._impl = SessionServiceImpl(session_repo, scenario_repo)
        return self._impl

    async def setup_session(
        self,
        session_id: str,
        user_id: int,
        scenario_id: int,
        db: Session
    ) -> tuple[str, ScenarioDetail, datetime]:
        """
        세션 설정 (위임)

        Args:
            session_id: Spring 1에서 생성한 UUID
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            db: DB 세션

        Returns:
            (session_id, scenario_detail, expires_at)
        """
        impl = await self._get_impl()
        return await impl.setup_session(session_id, user_id, scenario_id, db)

    async def close(self):
        """Redis 연결 종료"""
        if self._impl is not None:
            # SessionServiceImpl은 저장소를 소유하고 있지 않으므로
            # 저장소의 close()를 직접 호출해야 함
            try:
                await self._impl.session_repo.close()
            except Exception as e:
                logger.warning(f"Failed to close session repository: {e}")


# ============================================
# 전역 인스턴스 (레거시 호환성용)
# ============================================

# ⚠️ DEPRECATED: 새 코드는 dependencies.py의 DI를 사용하세요
def _create_legacy_session_service():
    """레거시 세션 서비스 생성"""
    return SessionService()


# 지연 초기화: 처음 사용시에만 생성
_session_service_instance = None


def get_session_service_instance():
    """레거시 전역 인스턴스 반환"""
    global _session_service_instance
    if _session_service_instance is None:
        _session_service_instance = _create_legacy_session_service()
    return _session_service_instance


# 직접 접근용 (하위호환성)
session_service = None


def __getattr__(name):
    """모듈 수준 속성 접근시 지연 초기화"""
    if name == "session_service":
        return get_session_service_instance()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
