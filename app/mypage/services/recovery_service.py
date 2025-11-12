"""
Recovery Service
================
계정 복구(비밀번호 찾기, 이메일 재발송 등) 기능을 관리하는 서비스 모듈입니다.

역할:
    - 복구 요청 생성 및 상태 관리
    - 이메일 인증 코드 생성 및 발송
    - 토큰 검증 및 비밀번호 재설정 처리

주요 함수:
    - request_recovery(email)
    - verify_recovery_code(email, code)
    - reset_password(email, new_password)

의존성:
    - repository.py
    - Core/email_sender.py
    - Core/Security.py (비밀번호 암호화)
"""