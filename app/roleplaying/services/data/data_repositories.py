"""
Repository Implementations (SOLID 준수)
========================================
데이터 접근 계층 추상화를 통한 OCP 준수.

설계:
- Repository Protocol로 인터페이스 정의
- 각 저장소는 Protocol 구현
- 특정 데이터 소스(Redis, MySQL)에 종속되지 않음
- 새로운 저장소 구현 추가 가능

OCP 준수:
- 기존 클래스 수정 없음 (Closed for modification)
- 새로운 저장소 구현 추가 가능 (Open for extension)

구조:
    RedisSessionRepository     → Redis 기반 세션 저장소
    DatabaseScenarioRepository → MySQL 기반 시나리오 저장소
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.roleplaying.api.api_schemas import ScenarioDetail
from app.roleplaying.services.service_interfaces import SessionRepository, ScenarioRepository

logger = logging.getLogger(__name__)


# ============================================
# RedisSessionRepository
# ============================================

class RedisSessionRepository(SessionRepository):
    """Redis 기반 세션 저장소

    FastAPI 내부 세션을 Redis에 저장/관리합니다.
    책임: 세션 CRUD만 담당
    """

    def __init__(self, redis_url: str = None):
        """
        Redis 세션 저장소 초기화

        Args:
            redis_url: Redis 연결 URL (기본값: settings.REDIS_URL)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        logger.info(f"RedisSessionRepository initialized with {self.redis_url}")

    async def _get_redis_client(self) -> redis.Redis:
        """Redis 클라이언트 연결"""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self.redis_client

    async def save_session(
        self,
        session_id: str,
        user_id: int,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        세션 저장

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            expires_at: 만료 시각 (기본값: 현재 + 2시간)
        """
        redis_client = await self._get_redis_client()

        # 기본 만료 시간
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(hours=2)

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

        # TTL 계산
        ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
        ttl_seconds = max(1, ttl_seconds)  # 최소 1초

        # Redis에 저장
        await redis_client.setex(
            redis_key,
            ttl_seconds,
            json.dumps(session_data)
        )

        logger.info(f"Session saved to Redis: {redis_key}, user_id={user_id}, TTL={ttl_seconds}s")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        redis_client = await self._get_redis_client()

        redis_key = f"session:{session_id}"

        try:
            session_data = await redis_client.get(redis_key)
            if session_data:
                logger.debug(f"Session retrieved from Redis: {redis_key}")
                return json.loads(session_data)
            else:
                logger.debug(f"Session not found in Redis: {redis_key}")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve session from Redis: {e}")
            return None

    async def delete_session(self, session_id: str) -> None:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        redis_client = await self._get_redis_client()

        redis_key = f"session:{session_id}"

        try:
            deleted = await redis_client.delete(redis_key)
            if deleted:
                logger.info(f"Session deleted from Redis: {redis_key}")
            else:
                logger.debug(f"Session not found to delete: {redis_key}")
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")

    async def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")


# ============================================
# DatabaseScenarioRepository
# ============================================

class DatabaseScenarioRepository(ScenarioRepository):
    """MySQL 기반 시나리오 저장소

    시나리오 정보를 MySQL에서 조회합니다 (READ-ONLY).
    책임: 시나리오 조회만 담당
    """

    async def get_scenario(
        self,
        scenario_id: int,
        user_id: int,
        db: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        """
        시나리오 조회 (READ-ONLY)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (권한 확인용)
            db: DB 세션 (FastAPI Depends에서 주입됨)

        Returns:
            ScenarioDetail DTO 또는 None
        """
        if db is None:
            logger.error("DB session is required for DatabaseScenarioRepository")
            return None

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

    async def get_user_scenarios(
        self,
        user_id: int,
        limit: int = 10,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        사용자의 시나리오 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수 제한
            db: DB 세션

        Returns:
            시나리오 리스트
        """
        if db is None:
            logger.error("DB session is required for DatabaseScenarioRepository")
            return []

        try:
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
                WHERE sc.user_id = :user_id
                  AND LOWER(sc.status) = 'generated'
                ORDER BY sc.created_at DESC
                LIMIT :limit
            """)

            result = db.execute(
                query,
                {"user_id": user_id, "limit": limit}
            )
            rows = result.fetchall()

            scenarios = []
            for row in rows:
                fixed_questions_raw = row.fixed_questions
                if fixed_questions_raw:
                    if isinstance(fixed_questions_raw, str):
                        fixed_questions = json.loads(fixed_questions_raw)
                    else:
                        fixed_questions = fixed_questions_raw
                else:
                    fixed_questions = [
                        "Can you introduce yourself?",
                        "What challenges do you face?",
                        "What are your next steps?"
                    ]

                scenario_detail = ScenarioDetail(
                    scenarioId=row.scenario_id,
                    subjectId=row.subject_id,
                    myRole=row.my_role or "User",
                    aiRole=row.ai_role or "AI Assistant",
                    title=row.title,
                    topicType=row.topic_type or "detail",
                    fixedQuestions=fixed_questions[:3]
                )
                scenarios.append(scenario_detail)

            logger.info(f"Loaded {len(scenarios)} scenarios for user {user_id}")
            return scenarios

        except Exception as e:
            logger.error(f"DB query failed: {e}", exc_info=True)
            return []
