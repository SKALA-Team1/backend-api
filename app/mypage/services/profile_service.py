"""
Profile Service
===============
사용자 프로필 조회, 수정, 이미지 변경 등의 비즈니스 로직을 담당하는 서비스 모듈입니다.

역할:
    - 프로필 데이터 로드 및 업데이트
    - 업로드된 이미지 파일 처리 (S3, 로컬 등)
    - 활동 통계, 상태 메시지, 소개글 변경 등

주요 함수:
    - get_profile(user_id)
    - update_profile(user_id, update_data)
    - upload_profile_image(user_id, file)

의존성:
    - repository.py
    - schemas.py
    - Core/Security.py (인증 유저 검증)
"""