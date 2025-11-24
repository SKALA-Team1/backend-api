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

# Lazy Redis client cache for utility helpers
_redis_client_cache: Optional[redis.Redis] = None


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


async def get_redis_client(redis_url: Optional[str] = None) -> redis.Redis:
    """
    Redis 클라이언트 단일 인스턴스 반환 (캐싱)

    Args:
        redis_url: 커스텀 Redis URL (없으면 settings.REDIS_URL 사용)

    Returns:
        redis.Redis: Redis 비동기 클라이언트
    """
    from app.config import settings  # 지연 임포트 (순환 참조 방지)

    global _redis_client_cache

    if _redis_client_cache is None:
        url = redis_url or settings.REDIS_URL
        _redis_client_cache = await redis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Redis client initialized for caching: {url}")

    return _redis_client_cache


async def close_redis_client() -> None:
    """
    캐시된 Redis 클라이언트 연결 종료

    ✅ Public interface: private _redis_client_cache에 직접 접근 대신 이 함수 사용
    - FastAPI lifespan에서 서버 종료 시 호출
    - redis_client 모듈의 내부 구현 변경에 영향을 받지 않음

    사용 예:
        from app.integrations.clients.redis_client import close_redis_client
        await close_redis_client()
    """
    global _redis_client_cache

    if _redis_client_cache is not None:
        try:
            await _redis_client_cache.close()
            logger.info("Redis client connection closed")
            _redis_client_cache = None
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}", exc_info=True)
