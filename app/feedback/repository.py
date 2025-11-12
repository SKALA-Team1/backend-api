"""
📄 파일명: repository.py
📌 역할: 피드백 관련 DB 접근 로직을 캡슐화한 데이터 액세스 계층.
        - 조회, 생성, 업데이트 등 SQLAlchemy ORM을 이용한 CRUD 처리.
🧩 관련 모듈:
  - models.py: ORM 모델 참조
  - services/*.py: 서비스 계층에서 호출
🧠 주요 기능:
  - get_feedback_by_scenario(): 시나리오별 피드백 조회
  - save_feedback(): 새 피드백 데이터 저장
  - list_message_feedbacks(): 발화 단위 피드백 리스트 반환
"""