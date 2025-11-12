"""
User Schemas
=============
사용자 관련 API 요청/응답용 Pydantic 스키마 정의.

역할:
    - 회원가입/로그인 요청 데이터 검증
    - 프로필, 설정, 인증 상태 등 응답 직렬화
    - Models와 연동되는 안전한 DTO 구조 제공

주요 스키마(예시):
    - EmailSignupRequest / EmailSignupResponse
    - EmailLoginRequest / TokenResponse
    - ProfileSchema / ProfileUpdateSchema
    - PasswordResetRequest / PasswordResetResponse
    - OAuthUserSchema / VerifyEmailSchema

의존성:
    - Models.py
"""