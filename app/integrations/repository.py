"""
Integration Repository
======================
DB 액세스 계층(Data Access Layer)로, 통합 관련 데이터를 CRUD하는 로직을 캡슐화합니다.

역할:
    - IntegrationConfig, SyncLog, ExternalMapping 등의 데이터 저장 및 조회
    - 서비스 계층(Service Layer)에서 직접 DB 접근을 막고 재사용성 향상

주요 함수:
    - get_integration_config(service_name)
    - upsert_mapping(external_id, internal_id)
    - record_sync_log(service, status, details)

의존성:
    - models.py
    - Db/Session.py
"""