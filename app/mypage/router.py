"""
Mypage Router
=============
사용자 마이페이지 관련 API 엔드포인트를 정의하는 라우터 모듈입니다.

역할:
    - 프로필 조회 및 수정, 북마크, 랭킹, 설정 변경, 계정 복구 등의 HTTP 엔드포인트 제공
    - FastAPI Router를 통해 클라이언트 요청을 서비스 계층으로 라우팅

주요 엔드포인트:
    - GET /mypage/profile : 사용자 프로필 조회
    - PATCH /mypage/settings : 설정 변경
    - GET /mypage/bookmarks : 북마크 목록 조회
    - POST /mypage/recover : 계정 복구 요청

의존성:
    - Services/profile_service.py
    - Services/bookmark_service.py
    - Services/ranking_service.py
    - Services/settings_service.py
    - Services/recovery_service.py
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
