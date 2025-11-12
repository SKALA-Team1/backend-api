"""
Roleplaying Router
==================
AI 롤플레잉(시나리오 기반 대화) 관련 API 엔드포인트를 정의하는 라우터 모듈.

역할:
    - 시나리오 시작, 메시지 주고받기, 상태 조회, 종료 등 모든 흐름의 진입점 제공.
    - WebSocket 및 HTTP 기반 요청을 서비스 계층으로 전달.

주요 엔드포인트:
    - POST /roleplaying/start : 새 시나리오 시작
    - POST /roleplaying/message : 사용자 메시지 전달 및 AI 응답 반환
    - GET /roleplaying/status : 현재 시나리오 상태 조회
    - POST /roleplaying/finish : 시나리오 종료 후 요약/정리

의존성:
    - Services/start_scenario_service.py
    - Services/message_flow_service.py
    - Services/get_status_service.py
    - Services/finish_scenario_service.py
    - ws_audio.py (실시간 음성 세션)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
