"""
Message Flow Service
====================
사용자 ↔ AI 간의 대화 흐름을 관리하는 핵심 서비스 모듈.

역할:
    - 메시지 입력 → 시나리오 단계별 응답 생성 → 로그 기록의 전체 파이프라인 관리
    - TurnManager와 StepPlanner를 통해 대화 흐름 제어
    - KeywordEngine으로 맥락 강화 및 Summarizer로 요약 지원

주요 함수:
    - process_message(scenario_id, user_message)
    - generate_ai_reply(context)
    - log_turn(scenario_id, user_text, ai_text)

의존성:
    - turn_manager.py
    - step_planner.py
    - keyword_engine.py
    - summarizer.py
    - Repository.py
"""