"""
📄 파일명: suggestion_service.py
📌 역할: 사용자 발화에서 교정이 필요한 문장을 찾아
        LLM을 통해 제안문(suggested expression)을 생성.
🧩 관련 모듈:
  - builder.prompt_builder.py   : LLM 프롬프트 생성
  - builder.response_parser.py  : LLM 응답 파싱
  - repository.py               : 피드백 저장
🧠 주요 기능:
  - generate_suggestions(): LLM 호출로 제안문 생성
  - get_suggestion_detail(): 단일 문장의 교정/해설 반환
"""