"""
📄 파일명: schemas.py
📌 역할: Pydantic 기반의 요청/응답 DTO 정의.
        - 피드백, 요약, 제안문, 점수 등 API 데이터 구조를 명세.
🧩 관련 모듈:
  - models.py: DB 모델 구조와 매핑
  - router.py: API 응답 및 요청 데이터 검증
🧠 주요 클래스:
  - FeedbackSummaryResponse: 피드백 요약 응답 DTO
  - MessageFeedbackResponse: 발화별 피드백 DTO
  - SuggestionDetailResponse: 교정 제안문 상세 DTO
"""