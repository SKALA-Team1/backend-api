"""
Integration Router
==================
외부 서비스(Slack, GitHub 등)와의 통합 관련 API 엔드포인트를 정의하는 라우터 모듈입니다.

역할:
    - FastAPI Router를 통해 통합 관련 요청을 수신하고 각 Service로 라우팅합니다.
    - 예: /integrations/sync/slack → SlackSyncService 호출
    - 예: /integrations/mapping/github → MappingService 호출

주요 기능:
    - Slack / GitHub 동기화 트리거
    - 매핑 검증 및 초기화 API
    - 클라이언트별 토큰 검증 및 상태 조회

의존성:
    - Services/sync_service.py
    - Services/mapping_service.py
    - Clients/slack_client.py, Clients/github_client.py

예시 시나리오:
    /integrations/sync/all → 전체 외부 데이터 재동기화
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
