# Backend Skeleton – 개발자용 간단 가이드

FastAPI 프로젝트에서 꼭 알아야 할 파일과 사용법을 쉽게 정리했습니다. 새 기능을 만들기 전에 아래 내용을 한번 읽어보세요.

---

## 1. 환경 변수 (`app/config.py`, `.env`, `.env.example`)
- `.env` 파일에 DB 주소, SECRET_KEY 등을 적어둡니다. 깃에는 올라가지 않으니 각자 만들어야 합니다.
- `.env.example`은 팀원에게 보여줄 예시입니다. 새 키를 쓰면 여기에도 예시 값을 꼭 추가하세요.
- `settings = get_settings()`로 환경 값을 불러옵니다. 어디서든 `settings.database_url` 식으로 사용하면 됩니다.

## 2. DB 연결 (`app/db/session.py`, `app/core/deps.py`)
- `SessionLocal`이 DB 연결을 만들어 줍니다.
- FastAPI 라우터에서는 `Depends(get_db)`를 사용해 세션을 가져오고, 작업이 끝나면 자동으로 닫힙니다.
- 스크립트에서 쓸 때는 `session = get_session()` 후 `session.close()`를 직접 호출하세요.

## 3. 로그 (`app/core/logging.py`)
- `setup_logging()`을 호출하면 모든 로그가 JSON 형태로 콘솔에 출력됩니다.
- 로그를 쓰고 싶으면 파일 상단에서 `logger = get_logger(__name__)`을 호출하고 `logger.info(...)`처럼 사용하세요.
- 파일로 남기고 싶으면 `_build_logging_config()`에 FileHandler를 추가하면 됩니다.

## 4. 예외와 상태 코드 (`app/core/exceptions.py`, `app/core/http_status.py`)
- 공통 예외 `AppException`을 사용하면 HTTP 상태 코드와 메시지를 쉽게 지정할 수 있습니다.
  ```python
  from app.core.exceptions import AppException
  from app.core.http_status import StatusCode

  raise AppException("권한 없음", status_code=StatusCode.FORBIDDEN)
  ```
- `StatusCode` Enum을 사용해 숫자 대신 이름으로 상태 코드를 쓰면 실수를 줄일 수 있습니다.
- `app/main.py`에서 `register_exception_handlers(app)`를 호출해야 전역 예외 처리가 동작합니다.

## 5. 앱 시작 (`app/main.py`)
1. `setup_logging()` 호출
2. `app = FastAPI(...)` 생성
3. `register_exception_handlers(app)` 호출
4. `app.include_router(...)`로 필요한 라우터 연결

## 6. README / 스크립트
- `README.md`의 Quick Start는 항상 최신으로 유지합니다.
- 공용 스크립트(`scripts/run_dev.sh` 등)를 만들면, 사용법을 README에 같이 적어 두세요.

## 7. 기타 팁
- 라우터 함수에 `status_code=StatusCode.CREATED`처럼 상태 코드를 지정하면 API 문서가 명확해집니다.
- 새 환경 변수를 만들면 `.env.example`과 `app/config.py`를 동시에 수정하세요.
- 설정이나 패턴에 변동이 있으면 이 문서도 같이 업데이트해 주세요.
