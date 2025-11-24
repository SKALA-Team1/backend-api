"""FastAPI application entrypoint where routers and services are wired."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.health.router import router as health_router
from app.roleplaying.router import router as roleplaying_router
from app.roleplaying.ws_realtime import router as ws_realtime_router

logger = logging.getLogger(__name__)

setup_logging()


# ========================================
# Ollama Warmup
# ========================================


async def warmup_ollama() -> None:
    """
    Ollama 모델을 미리 로드하여 콜드 스타트 방지

    목표:
    - 첫 요청 시 모델 로딩 지연(2-3초) 방지
    - 클라이언트가 타임아웃하지 않도록 사전에 모델 준비
    """
    try:
        from app.config import settings
        import ollama
        import asyncio

        logger.info("🔥 Starting Ollama model warmup...")
        start_time = asyncio.get_running_loop().time()

        # 간단한 프롬프트로 모델 로드
        # (실제 응답은 필요 없고, 메모리 로드만 필요)
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'ready' in one word."
                }
            ],
            stream=False
        )

        elapsed = asyncio.get_running_loop().time() - start_time
        logger.info(
            f"✅ Ollama warmup complete in {elapsed:.2f}s "
            f"(model={settings.OLLAMA_MODEL})"
        )

    except Exception as e:
        logger.warning(
            f"⚠️  Ollama warmup failed (will retry on first request): {e}"
        )


# ========================================
# FastAPI Lifespan Handler
# ========================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱 lifecycle 관리

    Startup: 앱 시작 시 필요한 연결 초기화
    Shutdown: 앱 종료 시 연결 정리 및 resource 해제
    """
    # ========================================
    # Startup: 리소스 초기화
    # ========================================
    logger.info("FastAPI application starting up...")

    try:
        # Redis 클라이언트 초기화 (필요시)
        from app.integrations.clients.redis_client import redis_validator
        logger.info("Redis validator initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}")

    try:
        # Spring 2 클라이언트 초기화 (필요시)
        from app.integrations.clients.spring2_client import spring2_client
        logger.info("Spring 2 client initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Spring 2 client: {e}")

    # ========================================
    # Ollama 모델 워밍업 (콜드 스타트 방지)
    # ========================================
    try:
        await warmup_ollama()
    except Exception as e:
        logger.warning(f"Ollama warmup failed (non-fatal): {e}")

    logger.info("FastAPI application startup complete")

    yield

    # ========================================
    # Shutdown: 리소스 정리
    # ========================================
    logger.info("FastAPI application shutting down...")

    try:
        # ✅ Redis 연결 종료 (public interface 사용)
        from app.integrations.clients.redis_client import close_redis_client
        await close_redis_client()
    except Exception as e:
        logger.warning(f"Failed to close Redis: {e}")

    try:
        # ✅ HTTP 클라이언트 종료 (public interface 사용)
        from app.integrations.clients.spring2_client import spring2_client
        await spring2_client.close()
    except Exception as e:
        logger.error(f"Error closing HTTP client: {e}", exc_info=True)

    logger.info("FastAPI application shutdown complete")


app = FastAPI(title="Backend Skeleton", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(roleplaying_router, prefix="/roleplaying", tags=["roleplaying"])
app.include_router(ws_realtime_router, tags=["websocket"])


@app.get("/")
async def root():
    return {"message": "hello"}
