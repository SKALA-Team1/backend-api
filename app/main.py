"""
📄 파일명: main.py
📌 역할: FastAPI 애플리케이션 진입점. 앱 생성, 라우터 등록, 미들웨어 설정.
🧩 관련 모듈:
  - app.core.security / app.core.exceptions
  - app.health.router 등 주요 라우터
"""

from fastapi import FastAPI
from app.health.router import router as health_router

app = FastAPI(title="Backend Skeleton")
app.include_router(health_router, prefix="/health", tags=["health"])

@app.get("/")
async def root():
    return {"message": "hello"}
