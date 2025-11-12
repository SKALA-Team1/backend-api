"""
Start Lesson Service
====================
새 레슨을 생성/초기화하고 첫 질문/목표/스코프를 설정하는 서비스.

역할:
    - 교재/단원/난이도/학습목표 등 파라미터 검증
    - Lesson 엔티티 생성 및 초기 상태 세팅
    - 첫 문항 선별(어댑티브 전략 적용 가능)

주요 함수(예시):
    - start_lesson(user_id, textbook_id, unit_id, options)
    - build_initial_context(options)
    - pick_first_question(context)

의존성:
    - repository.py
    - schemas.py
    - (옵션) Core/policy.py (레슨 정책)
"""