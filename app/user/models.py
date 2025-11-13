"""
User Models
============
사용자 관련 데이터베이스 ORM 모델 정의 모듈.

역할:
    - 사용자 계정, 권한, 동의, 알림, 프로필 등 핵심 테이블 구조 정의
    - SQLAlchemy 기반 ORM 클래스 구성
    - 관계형 필드(User ↔ Permission, Notification 등) 관리

주요 클래스(예시):
    - User: 기본 사용자 정보(이메일, 비밀번호 해시, 가입 일시 등)
    - UserProfile: 추가 정보(닉네임, 아바타, 상태 메시지 등)
    - UserAgreement: 이용약관 및 개인정보 처리방침 동의 내역
    - UserPermission: 역할(Role) 및 접근 권한 정보
    - UserNotification: 알림 수신 설정 및 로그

의존성:
    - Db/base.py
"""