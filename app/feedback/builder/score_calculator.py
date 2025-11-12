"""
📄 파일명: score_calculator.py
📌 역할: 발음, 문법, 표현 다양성 등 세부 평가 항목 점수를 계산하거나 변환.
🧩 관련 모듈:
  - response_parser.py : LLM 응답 내 점수 필드 추출
  - feedback_assembler.py : 최종 점수 반영
🧠 주요 기능:
  - normalize_score(): 점수 스케일링
  - calculate_overall_score(): 항목별 가중 평균 계산
"""