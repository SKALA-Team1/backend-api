"""
Session Service Refactored (SOLID 준수)
========================================
세션 설정 및 관리를 담당하는 서비스.

구조:
    SessionServiceImpl  → 세션 설정 및 관리만 담당
    - SessionRepository로 세션 저장/조회
    - ScenarioRepository로 시나리오 정보 조회
    - 비즈니스 로직 조율

책임:
    - Spring 1에서 생성한 session_id를 받아서 FastAPI 내부용으로 저장
    - DB에서 시나리오 정보 조회
    - Redis에 세션 정보 저장

의존성:
    - SessionRepository (Redis 기반)
    - ScenarioRepository (MySQL 기반)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.roleplaying.api.api_schemas import ScenarioDetail
from app.roleplaying.services.service_interfaces import SessionRepository, ScenarioRepository

logger = logging.getLogger(__name__)


class SessionServiceImpl:
    """세션 관리 서비스 (SOLID 준수)

    책임: 세션 설정 및 관리만 담당
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        scenario_repository: ScenarioRepository
    ):
        """
        세션 서비스 초기화

        Args:
            session_repository: SessionRepository 구현체
            scenario_repository: ScenarioRepository 구현체
        """
        self.session_repo = session_repository
        self.scenario_repo = scenario_repository
        logger.info("SessionServiceImpl initialized with injected repositories")

    async def setup_session(
        self,
        session_id: str,
        user_id: int,
        scenario_id: int,
        db: Session,
        interaction_mode: str,
        voice_id: Optional[str] = None
    ) -> tuple[str, ScenarioDetail, datetime]:
        """
        세션 설정 (Spring 1에서 생성한 session_id를 받아서 FastAPI 내부용으로 저장)

        Args:
            session_id: Spring 1에서 생성한 UUID (필수)
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            db: DB 세션
            interaction_mode: 상호작용 모드 (default, handsfree)
            voice_id: ElevenLabs Voice ID (선택적)

        Returns:
            (session_id, scenario_detail, expires_at)

        Raises:
            ValueError: 시나리오를 찾을 수 없는 경우
        """
        # Step 1: DB에서 시나리오 조회 (READ-ONLY)
        scenario_detail = await self.scenario_repo.get_scenario(scenario_id, user_id, db)

        if not scenario_detail:
            raise ValueError(f"Scenario {scenario_id} not found for user {user_id}")

        # Step 2: Redis에 세션 저장 (TTL 2시간)
        expires_at = datetime.utcnow() + timedelta(hours=2)
        await self.session_repo.save_session(session_id, user_id, expires_at, interaction_mode, voice_id)

        logger.info(
            f"Session setup: {session_id}, user={user_id}, "
            f"scenario={scenario_id}, expires_at={expires_at}, interaction_mode={interaction_mode}, voice_id={voice_id}"
        )

        return (session_id, scenario_detail, expires_at)
