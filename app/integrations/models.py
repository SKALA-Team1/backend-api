"""
Integration Models
==================
외부 서비스 통합 과정에서 사용되는 데이터 모델(Pydantic / SQLAlchemy)을 정의합니다.

역할:
    - 통합 설정, 매핑 정보, 동기화 로그 등의 ORM 모델 및 스키마 정의
    - 외부 API 응답을 내부 표준 모델로 변환하기 위한 중간 구조체 제공

주요 클래스:
    - IntegrationConfig: 각 서비스의 인증/설정 정보를 보관
    - SyncLog: 동기화 결과 및 상태 기록
    - ExternalMapping: 외부 객체와 내부 객체의 매핑 관계 저장

의존성:
    - Db/base.py
    - Mappers/slack_mapper.py, github_mapper.py
"""