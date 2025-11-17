"""
Redis Client
============
Redis를 사용하여 WebSocket 세션을 검증하는 클라이언트.

책임:
- session_id 검증 (Redis에서 조회)
- 세션 데이터 파싱

세션 데이터 형식 (Spring 1이 저장):
{
    "userId": 1,
    "role": "user",
    "scenarioType": "ROLEPLAYING",
    "startedAt": "2025-11-17T10:00:00Z",
    "expiresAt": "2025-11-17T12:00:00Z"
}
"""

import json
import logging
from typing import Optional, Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisSessionValidator:
    """
    Redis 기반 세션 검증기

    WebSocket 연결 시 session_id를 Redis에서 조회하여 검증합니다.
    """

    def __init__(self, redis_url: str):
        """
        RedisSessionValidator 초기화

        Args:
            redis_url: Redis 연결 URL (예: redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        logger.info(f"RedisSessionValidator initialized with URL: {redis_url}")

    async def connect(self) -> None:
        """Redis 연결 생성"""
        if self.redis is None:
            self.redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis")

    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        session_id를 Redis에서 조회하여 검증

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 (dict) 또는 None (존재하지 않으면)
            {
                "userId": 1,
                "role": "user",
                "scenarioType": "ROLEPLAYING",
                "startedAt": "...",
                "expiresAt": "..."
            }
        """
        if self.redis is None:
            await self.connect()

        try:
            # Redis 키 형식: session:{session_id}
            redis_key = f"session:{session_id}"

            session_data_str = await self.redis.get(redis_key)

            if not session_data_str:
                logger.warning(f"Session {session_id} not found in Redis")
                return None

            # JSON 파싱
            session_data = json.loads(session_data_str)

            logger.info(
                f"Session validated: {session_id}, "
                f"user={session_data.get('userId')}, "
                f"type={session_data.get('scenarioType')}"
            )

            return session_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse session data for {session_id}: {e}")
            return None

        except Exception as e:
            logger.error(f"Redis validation error for {session_id}: {e}")
            return None

    async def close(self) -> None:
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    async def __aenter__(self):
        """async with 지원"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async with 지원"""
        await self.close()