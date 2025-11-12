"""
📄 파일명: response_parser.py
📌 역할: LLM이 반환한 피드백 응답(JSON/Text)을 파싱하여 구조화된 형태로 변환.
🧩 관련 모듈:
  - llm_client.py : 원본 응답 수신
  - feedback_assembler.py : 구조화된 결과를 전달
🧠 주요 기능:
  - parse_feedback_response(): 피드백 JSON 파싱
  - parse_summary_response(): 요약 응답 파싱
"""