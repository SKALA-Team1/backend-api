"""
User Repository
================
사용자 관련 데이터를 DB에서 CRUD하는 데이터 접근 계층(Data Access Layer).

역할:
    - User, Profile, Permission, Agreement, Notification 관련 DB 트랜잭션 캡슐화
    - 인증 및 토큰 검증 시 DB 접근 통합 관리
    - Service 계층에서 직접 SQL 접근을 차단하고 재사용 가능한 함수 제공

주요 함수(예시):
    - create_user(email, password_hash)
    - get_user_by_email(email)
    - update_profile(user_id, data)
    - get_permissions(user_id)
    - log_user_agreement(user_id, policy_version)
    - update_notification_settings(user_id, prefs)

의존성:
    - Models.py
    - Db/Session.py
"""