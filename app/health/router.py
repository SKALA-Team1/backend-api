"""
📄 파일명: router.py
📌 역할: 헬스체크 API (DB 연결, LLM 상태 확인).
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
