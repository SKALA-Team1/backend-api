"""
Session Service
===============
롤플레잉 세션을 FastAPI 내부용으로 저장 및 관리하는 서비스.

역할:
- Spring 1에서 생성한 session_id를 받아서 FastAPI 내부용으로 저장
- DB에서 시나리오 정보 조회
- Redis에 세션 정보 저장 (TTL 2시간)

주의:
- session_id 생성은 Spring 1의 책임
- FastAPI는 setup_session() 호출 시 session_id를 전달받아야 함

의존성:
- Redis (세션 저장)
- MySQL DB (시나리오 조회, READ-ONLY)
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.roleplaying.schemas import ScenarioDetail

logger = logging.getLogger(__name__)


class SessionService:
    """
    롤플레잉 세션 생성 및 관리 서비스
    """

    def __init__(self):
        """SessionService 초기화"""
        self.redis_url = settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        logger.info("SessionService initialized")

    async def _get_redis_client(self) -> redis.Redis:
        """Redis 클라이언트 연결"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    async def setup_session(
        self,
        session_id: str,
        user_id: int,
        scenario_id: int,
        db: Session
    ) -> tuple[str, ScenarioDetail, datetime]:
        """
        세션 저장 (Spring 1에서 생성한 session_id를 받아서 FastAPI 내부용으로 저장)

        Args:
            session_id: Spring 1에서 생성한 UUID (필수)
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            db: DB 세션

        Returns:
            (session_id, scenario_detail, expires_at)

        Raises:
            ValueError: 시나리오를 찾을 수 없는 경우
        """
        # Step 1: DB에서 시나리오 조회 (READ-ONLY)
        scenario_detail = await self._get_scenario_from_db(scenario_id, user_id, db)

        if not scenario_detail:
            raise ValueError(f"Scenario {scenario_id} not found for user {user_id}")

        # Step 2: Redis에 세션 저장 (TTL 2시간)
        expires_at = datetime.utcnow() + timedelta(hours=2)
        await self._save_session_to_redis(session_id, user_id, expires_at)

        logger.info(
            f"Session setup: {session_id}, user={user_id}, "
            f"scenario={scenario_id}, expires_at={expires_at}"
        )

        return (session_id, scenario_detail, expires_at)

    async def _get_scenario_from_db(
        self,
        scenario_id: int,
        user_id: int,
        db: Session
    ) -> Optional[ScenarioDetail]:
        """
        DB에서 시나리오 조회 (READ-ONLY)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            db: DB 세션

        Returns:
            ScenarioDetail 또는 None
        """
        try:
            # SQL 쿼리: scenario + subject 조인
            query = text("""
                SELECT
                    sc.scenario_id,
                    sc.subject_id,
                    sc.title,
                    sc.status,
                    sc.fixed_questions,
                    sc.ai_role,
                    sc.topic_type,
                    sub.my_role
                FROM scenario sc
                JOIN subject sub ON sc.subject_id = sub.subject_id
                WHERE sc.scenario_id = :scenario_id
                  AND sc.user_id = :user_id
                  AND LOWER(sc.status) = 'generated'
            """)

            result = db.execute(
                query,
                {"scenario_id": scenario_id, "user_id": user_id}
            )
            row = result.first()

            if not row:
                logger.warning(
                    f"Scenario not found: scenario_id={scenario_id}, user_id={user_id}"
                )
                return None

            # fixed_questions 파싱 (JSON 컬럼)
            fixed_questions_raw = row.fixed_questions
            if fixed_questions_raw:
                if isinstance(fixed_questions_raw, str):
                    fixed_questions = json.loads(fixed_questions_raw)
                else:
                    fixed_questions = fixed_questions_raw
            else:
                # fixed_questions가 없으면 기본값
                fixed_questions = [
                    "Can you introduce yourself?",
                    "What challenges do you face?",
                    "What are your next steps?"
                ]

            # ScenarioDetail 생성
            scenario_detail = ScenarioDetail(
                scenarioId=row.scenario_id,
                subjectId=row.subject_id,
                myRole=row.my_role or "User",
                aiRole=row.ai_role or "AI Assistant",
                title=row.title,
                topicType=row.topic_type or "detail",
                fixedQuestions=fixed_questions[:3]  # 3개만 사용
            )

            logger.info(
                f"Scenario loaded from DB: {scenario_id}, "
                f"role={scenario_detail.myRole} → {scenario_detail.aiRole}"
            )

            return scenario_detail

        except Exception as e:
            logger.error(f"DB query failed: {e}", exc_info=True)
            return None

    async def _save_session_to_redis(
        self,
        session_id: str,
        user_id: int,
        expires_at: datetime
    ) -> None:
        """
        Redis에 세션 저장 (Spring 1 형식과 호환)

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            expires_at: 만료 시각
        """
        redis_client = await self._get_redis_client()

        # Redis 키: session:{session_id}
        redis_key = f"session:{session_id}"

        # 세션 데이터 (Spring 1과 동일한 형식)
        session_data = {
            "userId": user_id,
            "role": "user",
            "scenarioType": "ROLEPLAYING",
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "expiresAt": expires_at.isoformat() + "Z"
        }

        # Redis에 저장 (TTL 2시간)
        ttl_seconds = 7200  # 2 hours
        await redis_client.setex(
            redis_key,
            ttl_seconds,
            json.dumps(session_data)
        )

        logger.info(f"Session saved to Redis: {redis_key}, TTL={ttl_seconds}s")

    async def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# 전역 SessionService 인스턴스
session_service = SessionService()
