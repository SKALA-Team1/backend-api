"""
Step Planner
============
시나리오의 단계(phase) 진행 로직을 정의하는 모듈.

역할:
    - 시나리오의 구조적 단계(도입-전개-결말 등) 정의 및 상태 전이 관리
    - 메시지의 목적(intent)에 따라 다음 단계 자동 결정

주요 함수:
    - determine_next_step(current_context)
    - advance_step()
    - reset_plan()

의존성:
    - keyword_engine.py
"""