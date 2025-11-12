"""
Password Search (Recovery) Service
==================================
비밀번호 찾기 및 재설정 로직을 처리하는 서비스.

역할:
    - 비밀번호 재설정 링크/토큰 발급 및 검증
    - 이메일 발송 및 만료 정책 관리
    - 새 비밀번호 저장 및 보안 로그 기록

주요 함수(예시):
    - request_password_reset(email)
    - validate_reset_token(token)
    - reset_password(email, new_password)

의존성:
    - repository.py
    - Core/email_sender.py
    - Core/Security.py
"""