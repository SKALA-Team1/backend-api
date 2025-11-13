"""
Finish Scenario Service
=======================
시나리오 종료 시 요약, 피드백, 저장 등의 후처리를 담당하는 서비스.

역할:
    - 시나리오 종료 처리 및 최종 상태 저장
    - 대화 로그 요약 및 사용자의 학습 포인트 생성
    - Summarizer를 이용한 대화 분석 결과 생성

주요 함수:
    - finish_scenario(scenario_id)
    - summarize_conversation(logs)
    - save_final_report()

의존성:
    - summarizer.py
    - Repository.py
"""