"""
📄 파일명: models.py
📌 역할: 피드백 도메인의 데이터베이스 모델 정의.
        - 시나리오 피드백 및 메시지 피드백 테이블을 ORM으로 매핑.
🧩 관련 테이블:
  - scenario_feedback
  - scenario_message_feedback
🧠 주요 클래스:
  - ScenarioFeedback: 시나리오 단위 점수 및 총평 저장
  - ScenarioMessageFeedback: 각 발화(메시지) 단위의 세부 피드백 저장
"""