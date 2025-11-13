"""
GitHub Mapper
=============
GitHub API 응답(JSON)을 내부 표준 모델로 변환하는 모듈.

역할:
    - Repository, Issue, PR, Commit 등 GitHub 데이터 → 내부 Task, CodeChange 객체 변환
    - 필드 구조를 단일화하고 누락 필드 처리

주요 함수:
    - map_repository(repo_json)
    - map_pull_request(pr_json)
    - map_commit(commit_json)
"""