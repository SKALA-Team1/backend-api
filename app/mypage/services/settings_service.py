"""
Settings Service
================
사용자의 개인 설정(환경 설정, 알림, 공개 범위 등)을 관리하는 서비스 모듈입니다.

역할:
    - 사용자 설정 저장 및 업데이트
    - 알림 여부, 공개 범위, 언어 설정 등 UI/UX 관련 설정값 관리
    - 시스템 기본 설정값과 병합 처리

주요 함수:
    - get_settings(user_id)
    - update_settings(user_id, settings_data)
    - reset_to_default(user_id)

의존성:
    - repository.py
    - schemas.py
    - config.py
"""