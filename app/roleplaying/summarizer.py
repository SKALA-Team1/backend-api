"""
Summarizer
==========
시나리오 로그나 대화 기록을 요약하는 모듈.

역할:
    - 각 턴의 요약 및 전체 시나리오 요약 생성
    - AI 피드백 문장, 학습 포인트, 감정 흐름 분석 가능

주요 함수:
    - summarize_turns(turn_logs)
    - summarize_full_scenario(logs)
    - extract_learning_points()

의존성:
    - Core/llm_client.py (LLM 요약)
"""