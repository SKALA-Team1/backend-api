"""
Mypage Repository
=================
마이페이지 관련 데이터를 데이터베이스에서 CRUD하기 위한 Repository 계층 모듈입니다.

역할:
    - 서비스 계층(Service Layer)에서 사용할 데이터 접근 함수 제공
    - 각 테이블(UserProfile, UserBookmark, UserSettings 등)에 대한 쿼리 메서드 구현
    - 복잡한 JOIN, 정렬, 필터링 로직 캡슐화

주요 함수:
    - get_user_profile(user_id)
    - update_user_settings(user_id, settings_data)
    - get_user_bookmarks(user_id)
    - get_user_ranking(user_id)
    - create_recovery_request(email)

의존성:
    - models.py
    - Db/Session.py
"""