"""
📄 파일명: prompt_builder.py
📌 역할: LLM 피드백 요청을 위한 프롬프트를 생성하고 포맷팅.
🧩 관련 모듈:
  - app.adapters.llm_client.py : 생성된 프롬프트를 LLM에 전달
  - score_calculator.py        : 평가 항목 기준을 포함할 때 사용
🧠 주요 기능:
  - build_feedback_prompt(): 대화 로그 기반 피드백 요청 프롬프트 생성
  - build_summary_prompt(): 시나리오 요약용 프롬프트 생성
"""