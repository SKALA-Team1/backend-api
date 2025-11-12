"""
GitHub Client
=============
GitHub REST/GraphQL API 호출용 클라이언트.

역할:
    - 저장소, 이슈, PR, 커밋 등 엔드포인트 호출
    - OAuth 또는 Personal Access Token 인증 지원
    - Pagination 및 속도 제한 대응

주요 함수:
    - get_repositories(org)
    - get_commits(repo)
    - get_pull_requests(repo)

의존성:
    - config.py (GITHUB_TOKEN)
"""