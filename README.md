# Backend

## Quick Start

1. Python 3.11 이상 가상환경을 만들고 `pip install -r requirements.txt`(추가 예정)으로 의존성을 설치합니다.
2. `.env.example`을 복사해 `.env`를 만들고 값들을 팀 환경에 맞게 채웁니다.
3. `python -m app.main` 혹은 `uvicorn app.main:app --reload`로 개발 서버를 실행합니다.

## Environment Variables

`.env.example`에 정의된 값을 기반으로 아래 항목을 반드시 채워야 합니다.

- `ENVIRONMENT`: `development`/`production` 등 실행 모드.
- `SECRET_KEY`: JWT, 세션 등에서 사용할 비밀 키.
- `DATABASE_URL`: Supabase Postgres 연결 문자열.
- `OPENAI_API_KEY`: 생성형 모델 연동 시 필요(없다면 비워둬도 됨).

## Scripts

`setup_skeleton.sh`을 실행하면 FastAPI 스켈레톤 디렉터리가 생성됩니다. 필요 시 `scripts/run_dev.sh`, `scripts/migrate.sh`, `scripts/seed_db.sh`에 실제 명령을 채워 팀 공용 스크립트로 활용합니다.
