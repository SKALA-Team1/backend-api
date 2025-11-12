"""
Agreement Service
=================
이용약관 및 개인정보 처리방침 등 사용자 동의 내역을 관리하는 서비스.

역할:
    - 가입 시 또는 서비스 변경 시 최신 약관 동의 확인
    - 버전별 약관 기록 관리 및 감사 추적
    - 필수/선택 항목 분리 및 유효성 검증

주요 함수(예시):
    - record_user_agreement(user_id, agreement_version, accepted)
    - get_latest_agreements()
    - has_user_agreed(user_id, version)

의존성:
    - repository.py
    - Models.py
"""