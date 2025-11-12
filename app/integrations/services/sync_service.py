"""
Sync Service
============
통합 시스템의 메인 동기화 로직을 관리하는 서비스.

역할:
    - SlackSyncService, GitHubSyncService 등의 하위 서비스 호출을 오케스트레이션
    - 전체 동기화 주기 관리 (스케줄러와 연동)
    - 매핑 및 로그 기록 처리

주요 함수:
    - sync_all(): 모든 외부 서비스를 순차적으로 동기화
    - sync_specific(service): 특정 서비스만 갱신
    - update_sync_status()

의존성:
    - slack_sync_service.py
    - github_sync_service.py
    - repository.py
"""