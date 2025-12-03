"""FastAPI application entrypoint where routers and services are wired."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging

# Load environment variables
load_dotenv()

# ========================================
# LangSmith 설정 (LLM 모니터링)
# ========================================
def setup_langsmith():
    """LangSmith 트레이싱 설정"""
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        api_key = os.getenv("LANGCHAIN_API_KEY")
        project = os.getenv("LANGCHAIN_PROJECT", "default")

        if api_key:
            logging.info(f"✅ LangSmith 트레이싱 활성화 (프로젝트: {project})")
            logging.info(f"   대시보드: https://smith.langchain.com/o/default/projects")
            return True
        else:
            logging.warning("⚠️ LANGCHAIN_API_KEY가 설정되지 않음 - 트레이싱 비활성화")
            return False
    else:
        logging.info("ℹ️ LangSmith 트레이싱 비활성화 (LANGCHAIN_TRACING_V2=false)")
        return False
from app.health.router import router as health_router
from app.roleplaying.router import router as roleplaying_router
from app.roleplaying.ws_realtime import router as ws_realtime_router
from app.feedback.router import router as feedback_router
from app.textbook.rag.router import router as rag_router
from app.scenario.router import router as scenario_router

logger = logging.getLogger(__name__)

setup_logging()


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

    # LangSmith 트레이싱 초기화
    setup_langsmith()

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

app.include_router(health_router, tags=["health"])
app.include_router(roleplaying_router, tags=["roleplaying"])
app.include_router(ws_realtime_router, tags=["websocket"])
app.include_router(feedback_router, tags=["feedback"])
app.include_router(rag_router, prefix="/textbook", tags=["RAG (에이전트1)"])
app.include_router(scenario_router, tags=["시나리오 (에이전트2)"])


@app.get("/")
async def root():
    return {"message": "hello"}
