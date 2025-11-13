"""
Roleplaying Models
==================
시나리오와 대화 관련 데이터베이스 모델 정의 모듈.

역할:
    - 시나리오, 대화 로그, 참여자 정보 등의 ORM 모델 정의
    - 세션 ID, 진행 상태, 메타데이터 관리

주요 클래스:
    - Scenario: 시나리오 기본 정보 (제목, 생성자, 상태)
    - ConversationLog: 사용자/AI 대화 로그
    - TurnRecord: 각 턴의 상태 및 전이 정보

의존성:
    - Db/base.py
"""