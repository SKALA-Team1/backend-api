"""
📄 파일명: aggregation_service.py
📌 역할: 시나리오 종료 후 전체 대화의 피드백 데이터를 집계하고 저장.
        - 각 발화의 세부 피드백을 수집하여 총점, 평균점수, 요약 코멘트를 생성.
🧩 관련 모듈:
  - content_summary_service.py : 시나리오 요약 생성
  - content_review_service.py  : 문장별 제안문 및 수정 내용 수집
  - suggestion_service.py      : 교정 제안문 조회 및 병합
  - feedback.builder.*         : 점수 계산 및 요약 생성 유틸
🧠 주요 기능:
  - aggregate_scenario_feedback(): 전체 피드백 집계 및 저장
  - compute_totals(): 항목별 평균/총점 계산
"""