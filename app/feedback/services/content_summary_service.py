"""
📄 파일명: content_summary_service.py
📌 역할: 대화 전체를 요약하고 학습 요약 리포트를 생성.
        - 발음/문법/표현 점수를 기반으로 코멘트 작성.
🧩 관련 모듈:
  - builder.summary_generator.py : 요약 텍스트 생성
  - builder.score_calculator.py  : 점수 기반 코멘트 생성
🧠 주요 기능:
  - summarize_scenario(): 시나리오 단위 요약 생성
  - generate_learning_summary(): 학습자 피드백 요약문 생성
"""