#!/usr/bin/env bash
#
# Pre-flight checks for text-based roleplaying tests.
# 1. Verify Ollama server is reachable.
# 2. Verify MySQL and Redis services are reachable (config taken from .env).
# 3. Verify the configured scenario_id exists in the DB.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT_DIR}/infra"
SCENARIO_ID="${SCENARIO_ID:-1}"
export SCENARIO_ID

log() {
  printf '%s %s\n' "[check]" "$*"
}

fatal() {
  printf '%s %s\n' "[error]" "$*" >&2
  exit 1
}

start_ollama() {
  if pgrep -f "ollama serve" >/dev/null 2>&1; then
    log "Ollama 서버가 이미 실행 중입니다."
    return
  fi
  if ! command -v ollama >/dev/null 2>&1; then
    fatal "ollama 명령어를 찾을 수 없습니다. 설치 후 다시 실행하세요."
  fi
  log "Ollama 서버를 백그라운드에서 실행합니다..."
  nohup ollama serve > "${ROOT_DIR}/ollama.log" 2>&1 &
  sleep 2
}

start_docker_services() {
  if ! command -v docker-compose >/dev/null 2>&1; then
    fatal "docker-compose 명령어를 찾을 수 없습니다."
  fi
  if [ ! -f "${INFRA_DIR}/docker-compose.dev.yml" ]; then
    fatal "infra 디렉터리에서 docker-compose.dev.yml을 찾을 수 없습니다."
  fi
  log "infra 디렉터리에서 docker-compose로 Redis/MinIO를 실행합니다..."
  (
    cd "${INFRA_DIR}"
    docker-compose -f docker-compose.dev.yml up -d redis minio minio-init
  )
}

start_ollama
start_docker_services

log "1) Ollama 서버 상태 확인 중..."
if curl -fsS http://localhost:11434/api/tags > /dev/null; then
  log "   Ollama 응답 확인 완료."
else
  fatal "Ollama 서버에 연결할 수 없습니다. (http://localhost:11434/api/tags)"
fi

log "2) MySQL 및 Redis 연결 확인 중... (scenario_id=${SCENARIO_ID})"
python - <<'PY'
import sys
import pymysql
import os
from redis import Redis
from sqlalchemy.engine.url import make_url
from app.config import settings

def check_mysql():
    try:
        url = make_url(settings.database_url)
        scenario_id = int(os.environ.get("SCENARIO_ID", "31"))
        conn = pymysql.connect(
            host=url.host or "localhost",
            port=url.port or 3306,
            user=url.username or "root",
            password=url.password or "",
            database=url.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
        )
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.execute("SELECT 1 FROM scenario WHERE scenario_id = %s LIMIT 1;", (scenario_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row is None:
            print(f"[error] DB에는 scenario_id={scenario_id} 레코드가 없습니다.", file=sys.stderr)
            return False
        print(f"[check]   MySQL 연결 및 scenario_id={scenario_id} 존재 확인 완료.")
        return True
    except Exception as exc:
        print(f"[error] MySQL 연결 실패: {exc}", file=sys.stderr)
        return False

def check_redis():
    try:
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("[check]   Redis 연결 확인 완료.")
        return True
    except Exception as exc:
        print(f"[error] Redis 연결 실패: {exc}", file=sys.stderr)
        return False

ok_pg = check_mysql()
ok_redis = check_redis()
sys.exit(0 if (ok_pg and ok_redis) else 1)
PY

log "모든 선행 조건을 충족했습니다. 이제 텍스트 기반 롤플레잉 테스트를 진행할 수 있습니다."
