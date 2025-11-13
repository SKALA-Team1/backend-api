"""
Bookmark Service
================
사용자의 북마크 기능을 처리하는 서비스 모듈입니다.

역할:
    - 시나리오, 컨텐츠 등 사용자가 즐겨찾기한 항목을 CRUD 관리
    - 북마크 상태 토글, 정렬, 필터링 로직 수행
    - 스크랩한 항목 기반으로 추천 피처를 계산할 수도 있음

주요 함수:
    - get_bookmarks(user_id)
    - add_bookmark(user_id, target_id)
    - remove_bookmark(user_id, target_id)
    - is_bookmarked(user_id, target_id)

의존성:
    - repository.py
    - schemas.py
"""