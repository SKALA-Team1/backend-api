"""
Textbook Schemas
================
API 요청/응답에 사용하는 Pydantic 스키마 정의.

역할:
    - 외부로 노출되는 데이터 구조의 유효성 검사 및 직렬화
    - 내부 ORM(models)과 대응되는 경량/보안형 응답 모델 제공

주요 스키마(예시):
    - LessonStartRequest / LessonResponse
    - QuestionRequest / QuestionResponse
    - AnswerSubmitRequest / AnswerResult
    - LessonFinishResponse
    - ReviewItem / ReviewResponse

의존성:
    - models.py
"""