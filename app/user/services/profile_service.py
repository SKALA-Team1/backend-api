"""
Profile Service
===============
사용자 프로필 조회 및 수정 로직을 담당하는 서비스 모듈.

역할:
    - 프로필 정보 로드/업데이트
    - 아바타 이미지 업로드 및 저장 경로 관리
    - 공개 범위(privacy setting) 및 상태 메시지 관리

주요 함수(예시):
    - get_profile(user_id)
    - update_profile(user_id, update_data)
    - upload_avatar(user_id, file_path)

의존성:
    - repository.py
    - Core/Security.py
    - Core/file_uploader.py
"""