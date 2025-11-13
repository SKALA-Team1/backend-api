"""
Get Status Service
==================
현재 진행 중인 시나리오의 상태를 조회하는 서비스 모듈.

역할:
    - 진행 단계(turn), 현재 상황 요약, 목표 달성률 등 반환
    - WebSocket 기반 실시간 상태 업데이트와도 연동 가능

주요 함수:
    - get_status(scenario_id)
    - get_current_turn(scenario_id)
    - get_progress_summary()

의존성:
    - turn_manager.py
    - Repository.py
"""