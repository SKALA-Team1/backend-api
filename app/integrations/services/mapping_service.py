"""
Mapping Service
===============
외부 객체(Slack/GitHub 등)와 내부 도메인 모델 간의 매핑 관계를 관리합니다.

역할:
    - 외부 ID ↔ 내부 ID 변환
    - 매핑 테이블 생성 및 갱신
    - 비정상 매핑(삭제된 외부 객체 등) 검증

주요 함수:
    - create_mapping(external_obj, internal_obj)
    - resolve_internal_id(external_id)
    - cleanup_orphan_mappings()

의존성:
    - repository.py
    - models.py
"""