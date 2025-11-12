from fastapi import FastAPI
from app.health.router import router as health_router

app = FastAPI(title="Backend Skeleton")
app.include_router(health_router, prefix="/health", tags=["health"])

@app.get("/")
async def root():
    return {"message": "hello"}
