"""
Email Login Service
===================
이메일/비밀번호 기반 로그인 및 토큰 발급을 처리하는 서비스.

역할:
    - 사용자 인증 및 JWT 토큰 생성
    - 비밀번호 검증 및 보안 로깅
    - 로그인 이력 저장 (IP, Device 등)

주요 함수(예시):
    - login_with_email(email, password)
    - verify_credentials(email, password)
    - issue_access_token(user_id)

의존성:
    - repository.py
    - Core/Security.py
    - Core/jwt_manager.py
"""