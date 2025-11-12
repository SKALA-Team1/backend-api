"""
==============================================================
HTTP Status Code Enumeration
==============================================================
Centralized enumeration of HTTP status codes used in the project.

역할:
    - FastAPI 백엔드 전역에서 공통으로 사용하는 HTTP 상태 코드 상수를 관리
    - IntEnum 기반으로 정의하여 정수 비교와 Enum 이름 접근 둘 다 가능
    - 가독성을 높이고, 매직 넘버(200, 404 등)를 코드에서 제거

사용예시:
    from app.core.status_codes import StatusCode
    from app.core.exceptions import AppException

    # 예외 발생 시 의미 있는 상수로 참조
    raise AppException("User not found", status_code=StatusCode.NOT_FOUND)

--------------------------------------------------------------
Author: 정도현
Created: 2025-11-12
--------------------------------------------------------------
"""

from enum import IntEnum


class StatusCode(IntEnum):
    """
    Common HTTP status codes referenced throughout the backend.

    설명:
        - 표준 HTTP 상태 코드(2xx, 4xx, 5xx)를 열거형(enum)으로 정의
        - IntEnum을 상속받아 숫자 비교 및 Enum 이름 접근이 모두 가능
        - 코드 내에서 의미를 명확하게 표현 (예: 404 → StatusCode.NOT_FOUND)
    """

    # ✅ 성공(2xx)
    OK = 200                 # 요청 성공
    CREATED = 201            # 리소스 생성 성공
    ACCEPTED = 202           # 요청 접수 (비동기 처리 중)
    NO_CONTENT = 204         # 성공했지만 반환할 내용 없음

    # ⚠️ 클라이언트 오류(4xx)
    BAD_REQUEST = 400        # 잘못된 요청
    UNAUTHORIZED = 401       # 인증 실패 (로그인 필요)
    FORBIDDEN = 403          # 권한 없음
    NOT_FOUND = 404          # 리소스 없음
    CONFLICT = 409           # 요청 충돌 (예: 중복 데이터)
    UNPROCESSABLE_ENTITY = 422  # 요청은 유효하지만 처리 불가 (Pydantic ValidationError 등)

    # 💣 서버 오류(5xx)
    INTERNAL_SERVER_ERROR = 500  # 서버 내부 오류
    BAD_GATEWAY = 502            # 게이트웨이 오류 (Upstream 서버 문제)
    SERVICE_UNAVAILABLE = 503    # 서버가 일시적으로 사용 불가


# 모듈 외부에서 import 시 노출할 객체 제한
__all__ = ["StatusCode"]