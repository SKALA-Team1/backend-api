"""
Email Signup Service
====================
이메일 기반 회원가입을 처리하는 서비스 모듈.

역할:
    - 이메일 중복 검사, 비밀번호 암호화, 계정 생성
    - 이메일 인증 코드 발송 및 유효성 검증
    - 신규 유저 기본 설정(Profile, Agreement 등) 초기화

주요 함수(예시):
    - signup_with_email(email, password, nickname)
    - send_verification_email(email)
    - verify_signup_code(email, code)

의존성:
    - repository.py
    - Core/email_sender.py
    - Core/Security.py
    - Services/verify_service.py
"""