"""
Permission Service
==================
사용자 역할(Role) 및 권한(Access Control)을 관리하는 서비스.

역할:
    - 사용자별 접근 권한 조회/검증
    - 관리자/튜터/일반 사용자 등 역할 기반 접근 제어(RBAC)
    - 권한 부여 및 취소 로직 처리

주요 함수(예시):
    - assign_role(user_id, role_name)
    - has_permission(user_id, resource)
    - list_user_permissions(user_id)

의존성:
    - repository.py
    - Models.py
"""