"""
User Router
===========
사용자 관련 API 엔드포인트를 정의하는 라우터 모듈.

역할:
    - 회원가입, 로그인, 이메일 인증, 비밀번호 찾기 등 계정 관리 엔드포인트 제공
    - 프로필 조회/수정, 알림 설정, 약관 동의 등 서비스 전반의 사용자 인터페이스를 담당
    - OAuth 및 이메일 로그인 API 분기 처리

주요 엔드포인트(예시):
    - POST /user/signup/email        : 이메일 회원가입
    - POST /user/login/email         : 이메일 로그인
    - GET  /user/profile             : 프로필 조회
    - PATCH /user/profile            : 프로필 수정
    - POST /user/verify/email        : 이메일 인증 코드 확인
    - POST /user/password/recover    : 비밀번호 복구 요청

의존성:
    - Services/email_signup_service.py
    - Services/email_login_service.py
    - Services/oauth_service.py
    - Services/profile_service.py
    - Services/verify_service.py
    - Services/pw_search_service.py
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}
