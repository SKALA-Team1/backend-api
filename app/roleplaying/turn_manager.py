"""
Turn Manager
============
시나리오 내 턴(turn) 단위 대화 흐름을 관리하는 유틸리티.

역할:
    - 각 대화 턴의 순서, 참여자 교체, 종료 조건 관리
    - 턴별 상태(예: “AI 응답 대기”, “사용자 입력 완료”) 추적

주요 함수:
    - next_turn(current_turn)
    - is_turn_complete(state)
    - reset_turns()

의존성:
    - step_planner.py
"""