"""
Textbook Repository
===================
교재 레슨 도메인의 데이터 접근 계층(DAL).

역할:
    - Lesson, Question, Submission, ReviewNote에 대한 CRUD 및 조회 쿼리 제공
    - 페이징/정렬/필터, 트랜잭션 단위 작업 캡슐화
    - 서비스 계층에서 재사용 가능한 고수준 메서드 제공

주요 함수(예시):
    - create_lesson(user_id, textbook_id, unit_id, meta)
    - get_active_lesson(lesson_id)
    - fetch_next_question(lesson_id, strategy)
    - save_submission(lesson_id, question_id, payload)
    - finalize_lesson(lesson_id, scores, summary)
    - upsert_review_notes(lesson_id, notes)

의존성:
    - models.py
    - Db/Session.py
"""