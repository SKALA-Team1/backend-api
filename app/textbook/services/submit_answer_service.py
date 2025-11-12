"""
Submit Answer Service
=====================
사용자 답안을 검증/채점하고 피드백을 생성하는 서비스.

역할:
    - 정답 판정(객관식/주관식/음성/코드 등 유형별 채점 로직)
    - 부분점수/가중치/시간 페널티 등 평가 정책 적용
    - 즉시 피드백 문장, 해설, 추가 학습 링크 생성

주요 함수(예시):
    - submit_answer(lesson_id, question_id, payload)
    - grade_answer(question, payload)      # 규칙/ML/LLM 기반 채점
    - build_feedback(question, payload, result)

의존성:
    - repository.py
    - models.py
    - (옵션) Core/grader.py, Core/llm_client.py
"""