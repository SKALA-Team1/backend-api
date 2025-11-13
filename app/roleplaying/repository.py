"""
Roleplaying Repository
======================
시나리오 및 대화 데이터를 CRUD하는 데이터 접근 계층 모듈.

역할:
    - Scenario, ConversationLog, TurnRecord에 대한 쿼리 처리
    - 서비스 계층에서 DB 접근 로직을 추상화
    - 세션 관리, 로그 기록, 캐싱 등 포함

주요 함수:
    - create_scenario(data)
    - get_scenario_by_id(scenario_id)
    - save_conversation_log(scenario_id, user_text, ai_text)
    - update_scenario_status(scenario_id, status)

의존성:
    - Models.py
    - Db/Session.py
"""