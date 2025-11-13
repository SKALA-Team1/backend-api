"""
Mypage Schemas
==============
마이페이지 관련 API 요청 및 응답에 사용되는 Pydantic 스키마 정의 모듈입니다.

역할:
    - 클라이언트 ↔ 서버 간 데이터 직렬화 및 유효성 검증 담당
    - Models와 1:1 혹은 경량화된 형태로 매핑

주요 스키마:
    - ProfileSchema / ProfileUpdateSchema
    - BookmarkSchema / BookmarkCreateSchema
    - RankingSchema
    - SettingsSchema / SettingsUpdateSchema
    - RecoveryRequestSchema / RecoveryStatusSchema

의존성:
    - models.py
"""