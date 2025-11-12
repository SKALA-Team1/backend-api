"""
Scheduler
=========
통합 관련 정기 작업(동기화, 매핑 갱신 등)을 관리하는 스케줄러.

역할:
    - APScheduler 또는 Celery Beat 기반의 주기적 Job 실행
    - 매일/매주 단위의 Slack/GitHub 동기화 수행

주요 함수:
    - schedule_sync_jobs()
    - run_all_jobs()

의존성:
    - Tasks.py
"""