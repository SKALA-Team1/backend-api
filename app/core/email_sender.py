"""
📄 파일명: email_sender.py
📌 역할: 이메일 발송 관련 기능을 담당하는 유틸리티 모듈.
        - 회원가입, 비밀번호 찾기, 인증 코드 전송 등에서 공통 사용.
        - SMTP 또는 외부 이메일 서비스(API 기반)와 연동.
🧩 관련 모듈:
  - app.user.services.email_signup_service.py  → 인증 메일 전송
  - app.user.services.verify_service.py        → 인증 코드 검증 로직과 연동
  - app.config.py                              → 메일 서버 설정 참조 (SMTP_HOST, PORT, USER 등)
🧠 주요 기능:
  - send_email(to, subject, body): 일반 텍스트 이메일 발송
  - send_verification_email(user_email, code): 인증 메일 전송 헬퍼
  - send_password_reset_email(user_email, link): 비밀번호 재설정 메일
"""