"""
Finish Lesson Service
=====================
레슨 종료 후 결과 집계/요약/기록을 담당하는 서비스.

역할:
    - 총점/정답률/태그별 성취도 계산
    - 약점 분석 및 학습 리포트 생성
    - 레슨 상태 종료 처리 및 재시작 포인트 기록

주요 함수(예시):
    - finish_lesson(lesson_id)
    - compute_scores(submissions)
    - build_summary_report(lesson, scores)

의존성:
    - repository.py
    - summarizer(옵션, LLM 기반 요약)
"""