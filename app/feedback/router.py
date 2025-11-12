"""
📄 파일명: router.py
📌 역할: FastAPI 라우터 정의. 피드백 관련 API 엔드포인트 제공.
        - 학습 요약, 피드백 상세 조회, 제안문 복습 API 등을 포함.
🧩 관련 모듈:
  - services/*.py: 실제 로직을 수행하는 서비스 계층
  - schemas.py: 요청/응답 검증 및 직렬화
🧠 주요 엔드포인트 예시:
  - GET /feedback/summary      → 시나리오별 피드백 요약 조회
  - GET /feedback/review/{id}  → 대화별 피드백 상세 조회
  - GET /feedback/suggestion/{id} → 제안문 복습 상세 조회
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
