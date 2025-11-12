"""
📄 파일명: feedback_assembler.py
📌 역할: 피드백 생성 과정의 마지막 단계로, 여러 분석 결과를 통합하여 최종 피드백 구조를 조립.
🧩 관련 모듈:
  - summary_generator.py : 대화 요약 결과 사용
  - score_calculator.py  : 점수 계산 결과 사용
  - response_parser.py   : LLM 응답 파싱 결과 결합
🧠 주요 기능:
  - assemble_feedback(): 문장 단위/시나리오 단위 피드백 통합
  - merge_metrics(): 발음/문법/표현 점수 병합
"""