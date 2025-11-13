"""
Verify Service
==============
이메일/전화번호 인증, 코드 검증 등을 처리하는 서비스 모듈.

역할:
    - 인증 코드 생성 및 만료 시간 관리
    - 이메일/휴대폰 인증 결과 저장
    - 가입, 비밀번호 찾기, 민감 정보 변경 시 인증 흐름 제어

주요 함수(예시):
    - generate_verification_code(target)
    - verify_code(target, code)
    - invalidate_code(target)

의존성:
    - Core/email_sender.py
    - repository.py
"""