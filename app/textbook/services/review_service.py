"""
Review Service
==============
오답노트/리뷰 데이터 생성 및 재학습 경로 추천을 담당.

역할:
    - 틀린 문항/약점 태그 묶음으로 리뷰 아이템 생성
    - 스페이싱 반복(Spaced Repetition) 일정/큐 구성
    - 다음 학습 추천(복습 문제, 관련 단원, 레슨 재시작 포인트)

주요 함수(예시):
    - build_review(lesson_id)
    - get_review_items(lesson_id, limit=20)
    - recommend_next_steps(user_id, weaknesses)

의존성:
    - repository.py
    - models.py
    - (옵션) Core/recommender.py
"""