"""
List Scenario Service
=====================
사용자가 참여했던 롤플레잉 시나리오 목록을 조회하는 서비스 모듈.

역할:
    - DB에서 사용자별 시나리오 메타데이터 로드
    - 정렬, 필터링, 페이징 지원
    - 최근 실행한 시나리오를 빠르게 재개할 수 있는 데이터 반환

주요 함수:
    - list_scenarios(user_id, limit, offset)
    - get_recent_scenario(user_id)
"""