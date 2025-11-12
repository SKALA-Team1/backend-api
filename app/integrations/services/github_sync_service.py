"""
GitHub Sync Service
===================
GitHub 리포지토리, 커밋, PR, 이슈 데이터를 동기화하는 서비스.

역할:
    - GitHub API 호출 (GitHubClient 이용)
    - 프로젝트 단위 데이터 수집 및 내부 표준화
    - 코드 요약 및 변경 로그 생성

주요 함수:
    - sync_repositories()
    - sync_commits()
    - sync_pull_requests()

의존성:
    - Clients/github_client.py
    - Mappers/github_mapper.py
    - Normalizers/code_summaizer.py
    - repository.py
"""