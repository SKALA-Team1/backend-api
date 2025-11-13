"""
Mypage Models
=============
사용자 마이페이지 관련 데이터베이스 ORM 모델을 정의하는 모듈입니다.

역할:
    - 프로필, 북마크, 랭킹 기록, 설정 정보, 복구 요청 등의 테이블 구조를 정의
    - SQLAlchemy ORM 기반으로 User 관련 확장 데이터를 관리

주요 클래스:
    - UserProfile: 사용자 소개, 프로필 이미지, 활동 지표 저장
    - UserBookmark: 사용자가 저장한 항목(시나리오, 컨텐츠 등)
    - UserRanking: 사용자의 활동 점수, 랭킹 정보 저장
    - UserSettings: 알림, 공개범위, 환경설정 등 사용자 설정값
    - AccountRecovery: 복구 요청/상태 관리

의존성:
    - Db/base.py
    - schemas.py
"""