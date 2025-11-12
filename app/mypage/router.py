from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
