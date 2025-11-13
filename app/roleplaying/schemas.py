"""
Roleplaying Schemas
===================
시나리오 관련 API 요청/응답에 사용되는 Pydantic 스키마 정의 모듈.

역할:
    - 데이터 유효성 검증 및 직렬화
    - Models.py의 ORM 객체를 안전하게 API 응답용 형태로 변환

주요 스키마:
    - ScenarioCreateSchema / ScenarioResponseSchema
    - MessageSchema / TurnSchema
    - ScenarioStatusSchema

의존성:
    - Models.py
"""