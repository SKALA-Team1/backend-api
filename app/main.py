"""FastAPI application entrypoint where routers and services are wired."""

from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.health.router import router as health_router
from app.roleplaying.router import router as roleplaying_router

setup_logging()

app = FastAPI(title="Backend Skeleton")
register_exception_handlers(app)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(roleplaying_router, prefix="/roleplaying", tags=["roleplaying"])


@app.get("/")
async def root():
    return {"message": "hello"}
