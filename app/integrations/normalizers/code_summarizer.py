"""
Code Summarizer
===============
GitHub 코드 변경 내용(Commit diff, Pull Request 등)을 요약하는 모듈.

역할:
    - 변경된 파일과 라인을 기반으로 자연어 요약 생성
    - 주요 수정 포인트, 영향 모듈, 리스크 포인트 추출

주요 함수:
    - summarize_commit_diff(diff_text)
    - summarize_pull_request(pr_data)

의존성:
    - NLP 모델 또는 LLM API (예: OpenAI GPT)
"""