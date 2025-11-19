#!/usr/bin/env bash
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$dir"

cat <<'ENV' > .env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/skala
environment=development
REDIS_URL=redis://localhost:6379/0
SPRING2_BASE_URL=http://localhost:8081
WS_BASE_URL=ws://localhost:8000
FASTAPI_PORT=8000
ENV_ENTRIES
