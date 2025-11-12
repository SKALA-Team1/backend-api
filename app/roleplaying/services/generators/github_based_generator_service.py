"""
GitHub-Based Generator Service
==============================
GitHub 활동(이슈, PR, 커밋)을 기반으로 시나리오를 생성하는 Generator 모듈.

역할:
    - 개발 협업 데이터를 분석해 '코드 리뷰', '디버깅 회의' 등 시나리오 구성
    - 코드 변화 요약 및 대화형 시뮬레이션 대본 생성

주요 함수:
    - generate_from_github(repo, pr_id)
    - extract_discussion_points()
    - build_scenario_context()

의존성:
    - Integrations/Clients/github_client.py
    - Integrations/Mappers/github_mapper.py
    - summarizer.py
"""