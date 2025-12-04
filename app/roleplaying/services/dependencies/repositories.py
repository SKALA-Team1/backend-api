"""
Repository Dependencies
(SessionRepository, ScenarioRepository)
======================================

데이터 접근 계층(DAO) 의존성 주입 (Dependency Injection)

주요 저장소:
    - SessionRepository: Redis 기반 실시간 세션 상태 관리
    - ScenarioRepository: DB 기반 시나리오 조회 및 관리

설계:
    - 각 저장소는 요청별로 새로운 인스턴스 생성 (Request-scoped)
    - Redis/DB 연결은 클라이언트 내부에서 풀링으로 관리
    - Repository Pattern으로 비즈니스 로직과 데이터 접근 분리

사용 예:
    from app.roleplaying.services.dependencies.repositories import (
        SessionRepositoryDep,
        ScenarioRepositoryDep
    )

    @router.get("/sessions/{session_id}")
    async def get_session(
        session_id: str,
        session_repo: SessionRepositoryDep
    ):
        session = await session_repo.get(session_id)
        return session
"""

from typing import Annotated, TYPE_CHECKING

from fastapi import Depends
from app.config import settings

if TYPE_CHECKING:
    from app.roleplaying.services.service_interfaces import (
        SessionRepository,
        ScenarioRepository,
    )


# ============================================
# Repository Factory Functions
# ============================================

def get_session_repository() -> "SessionRepository":
    """세션 저장소 의존성 주입

    💾 역할:
        - Redis 기반 실시간 세션 상태 저장
        - WebSocket 연결 중 세션 데이터 임시 보관
        - 빠른 읽기/쓰기 성능 (메모리 기반)

    Returns:
        SessionRepository 인스턴스 (Request-scoped, 매번 새로 생성)

    Note:
        Redis 연결은 클라이언트 내부의 커넥션 풀에서 관리됩니다.
        여러 요청이 동시에 실행되어도 안전합니다.

    Example:
        @router.post("/sessions")
        async def create_session(
            session_repo: SessionRepositoryDep
        ):
            session = await session_repo.create(
                user_id=123,
                data={...}
            )
            return session
    """
    from app.roleplaying.services.data.data_repositories import RedisSessionRepository

    return RedisSessionRepository(redis_url=settings.REDIS_URL)


def get_scenario_repository() -> "ScenarioRepository":
    """시나리오 저장소 의존성 주입

    📚 역할:
        - DB에 저장된 시나리오 조회
        - 사용자별 시나리오 히스토리 검색
        - 공개 시나리오 템플릿 조회

    Returns:
        ScenarioRepository 인스턴스 (Request-scoped, 매번 새로 생성)

    Note:
        DB 세션은 각 요청마다 새로운 트랜잭션 스코프를 가집니다.
        트랜잭션 격리 레벨로 데이터 일관성이 보장됩니다.

    Example:
        @router.get("/scenarios/{user_id}")
        async def get_user_scenarios(
            user_id: int,
            scenario_repo: ScenarioRepositoryDep
        ):
            scenarios = await scenario_repo.find_by_user(user_id)
            return scenarios
    """
    from app.roleplaying.services.data.data_repositories import DatabaseScenarioRepository

    return DatabaseScenarioRepository()


# ============================================
# Type Aliases for FastAPI Depends
# ============================================

SessionRepositoryDep = Annotated[
    "SessionRepository",
    Depends(get_session_repository)
]
"""세션 저장소 의존성 타입 - Redis 기반 임시 저장"""

ScenarioRepositoryDep = Annotated[
    "ScenarioRepository",
    Depends(get_scenario_repository)
]
"""시나리오 저장소 의존성 타입 - DB 기반 영구 저장"""

__all__ = [
    "get_session_repository",
    "get_scenario_repository",
    "SessionRepositoryDep",
    "ScenarioRepositoryDep",
]
