#!/bin/bash

##############################################################################
# FastAPI 서버 시작 스크립트
#
# 사용법:
#   bash scripts/start_server.sh
#
# 설명:
#   - FastAPI 서버를 포트 8082에서 시작합니다
#   - 코드 변경 시 자동으로 리로드됩니다 (--reload)
#   - Ctrl+C로 종료할 수 있습니다
##############################################################################

set -e  # 에러 발생 시 스크립트 중단

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "FastAPI 서버 시작"
echo "=================================================="
echo ""
echo "📁 작업 디렉토리: $BACKEND_DIR"
echo "🔧 포트: 8082"
echo "🔄 자동 리로드: 활성화"
echo ""
echo "서버가 시작되었습니다. Ctrl+C로 중단할 수 있습니다."
echo "=================================================="
echo ""

cd "$BACKEND_DIR"

# 환경 변수 확인
if [ ! -f ".env" ]; then
    echo "⚠️  경고: .env 파일을 찾을 수 없습니다"
    echo "   기본 설정으로 계속 진행합니다"
    echo ""
fi

# FastAPI 서버 시작
python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8082 \
    --reload