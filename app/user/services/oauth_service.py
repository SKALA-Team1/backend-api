"""
OAuth Service
=============
외부 OAuth 제공자(Google, Apple, GitHub 등) 로그인/회원가입 처리 모듈.

역할:
    - OAuth 인증 토큰 교환 및 사용자 정보 수집
    - 기존 사용자 계정 연동 또는 신규 생성
    - 프로필 자동 동기화 (이메일, 이름, 아바타 등)

주요 함수(예시):
    - login_with_oauth(provider, code)
    - link_oauth_account(user_id, provider_info)
    - refresh_oauth_token(provider, refresh_token)

의존성:
    - repository.py
    - Integrations/Clients/github_client.py (GitHub 로그인 시)
    - Core/jwt_manager.py
"""