"""
Textbook Router
===============
교재 기반 레슨 흐름을 위한 API 엔드포인트를 정의하는 라우터 모듈.

역할:
    - 레슨 시작, 문항 질의/응답, 중간/최종 상태 조회, 레슨 종료 및 리뷰 생성 등
    - (옵션) WebSocket 오디오 세션(ws_audio)과의 연계 엔드포인트 제공

주요 엔드포인트(예시):
    - POST /textbook/lessons/start          : 새 레슨 시작
    - POST /textbook/lessons/{id}/question  : 문항 제시/진행
    - POST /textbook/lessons/{id}/answer    : 사용자 답안 제출
    - POST /textbook/lessons/{id}/finish    : 레슨 종료 및 결과 집계
    - GET  /textbook/lessons/{id}/review    : 오답노트/리뷰 조회

의존성:
    - Services/start_lesson_service.py
    - Services/question_flow_service.py
    - Services/submit_answer_service.py
    - Services/finish_lesson_service.py
    - Services/review_service.py
    - repository.py, schemas.py
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
