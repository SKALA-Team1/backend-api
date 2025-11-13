"""
📄 파일명: content_review_service.py
📌 역할: 대화 종료 후 대화 스크립트를 검토하고,
        각 사용자 발화별 제안 문장 및 피드백 리스트를 구성.
🧩 관련 모듈:
  - repository.py              : 시나리오 메시지 조회
  - suggestion_service.py      : 제안문 생성 및 연결
  - builder.response_parser.py : LLM 응답 파싱
🧠 주요 기능:
  - build_review_list(): 발화별 피드백 항목 정리
  - get_message_feedback(): 특정 문장에 대한 피드백 조회
"""