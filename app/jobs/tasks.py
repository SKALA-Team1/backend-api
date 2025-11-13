"""
Integration Tasks
=================
Scheduler에서 호출되는 개별 Task 로직을 정의합니다.

역할:
    - Slack, GitHub, Mapping 관련 작업을 구체적으로 실행
    - 각 작업 단위는 retry-safe 하게 설계되어 있음

주요 함수:
    - task_sync_slack()
    - task_sync_github()
    - task_update_mappings()

의존성:
    - Services/sync_service.py
    - Services/mapping_service.py
"""