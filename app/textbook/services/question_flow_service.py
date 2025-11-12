"""
Question Flow Service
=====================
레슨 중 문항 제시/전이 로직(어댑티브 출제)을 담당.

역할:
    - 현재 학습 상태, 난이도 곡선, 태그(문법/어휘/리스닝 등)에 따라 다음 문항 결정
    - 힌트/예시/보충설명 생성(LLM 연계 가능)
    - 오디오/텍스트 인터페이스를 모두 지원

주요 함수(예시):
    - get_next_question(lesson_id)
    - provide_hint(lesson_id, question_id)
    - explain_answer(question, user_submission)

의존성:
    - repository.py
    - models.py
    - (옵션) Core/llm_client.py, keyword/tag engine
"""