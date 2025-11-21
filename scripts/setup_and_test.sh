#!/bin/bash

##############################################################################
# SKALA 음성 롤플레잉 테스트 환경 설정 및 실행 스크립트
#
# 사용법:
#   bash scripts/setup_and_test.sh [옵션]
#
# 옵션:
#   --use-mic              실제 마이크로 테스트
#   --record-duration N    녹음 시간 (초, 기본값: 3)
#   --user-id N           사용자 ID (기본값: 1)
#   --scenario-id N       시나리오 ID (기본값: 1)
#   --verbose             상세 로깅 활성화
#   --help                도움말 표시
#
# 예시:
#   bash scripts/setup_and_test.sh --use-mic
#   bash scripts/setup_and_test.sh --use-mic --record-duration 5 --verbose
#   bash scripts/setup_and_test.sh --user-id 2 --scenario-id 5
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 기본값
USE_MIC=false
RECORD_DURATION=3
USER_ID=1
SCENARIO_ID=1
VERBOSE=false

# 명령줄 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --use-mic)
            USE_MIC=true
            shift
            ;;
        --record-duration)
            RECORD_DURATION="$2"
            shift 2
            ;;
        --user-id)
            USER_ID="$2"
            shift 2
            ;;
        --scenario-id)
            SCENARIO_ID="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            grep "^#" "$0" | grep -v "^#!/" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo "❌ 알 수 없는 옵션: $1"
            echo ""
            echo "도움말: bash scripts/setup_and_test.sh --help"
            exit 1
            ;;
    esac
done

# 필수 라이브러리 확인 및 설치
check_and_install_deps() {
    echo ""
    echo "=================================================="
    echo "📦 Python 라이브러리 확인"
    echo "=================================================="
    echo ""

    local missing_deps=()

    # sounddevice, soundfile 확인 (마이크 입력용)
    if ! python -c "import sounddevice" 2>/dev/null; then
        missing_deps+=("sounddevice")
    fi

    if ! python -c "import soundfile" 2>/dev/null; then
        missing_deps+=("soundfile")
    fi

    # websockets 확인
    if ! python -c "import websockets" 2>/dev/null; then
        missing_deps+=("websockets")
    fi

    # httpx 확인
    if ! python -c "import httpx" 2>/dev/null; then
        missing_deps+=("httpx")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "⚠️  다음 라이브러리가 필요합니다: ${missing_deps[*]}"
        echo ""
        echo "설치 중..."
        pip install "${missing_deps[@]}"
        echo "✅ 라이브러리 설치 완료"
    else
        echo "✅ 모든 필수 라이브러리가 설치되어 있습니다"
    fi
    echo ""
}

# 환경 변수 확인
check_environment() {
    echo "=================================================="
    echo "⚙️  환경 설정 확인"
    echo "=================================================="
    echo ""

    if [ ! -f "$BACKEND_DIR/.env" ]; then
        echo "❌ .env 파일을 찾을 수 없습니다"
        echo "   경로: $BACKEND_DIR/.env"
        exit 1
    fi

    echo "✅ .env 파일 확인"

    # .env에서 주요 설정 확인
    if grep -q "DEEPGRAM_API_KEY" "$BACKEND_DIR/.env"; then
        echo "✅ Deepgram API 키 설정됨"
    else
        echo "⚠️  Deepgram API 키가 설정되지 않았습니다"
        echo "   .env 파일에 DEEPGRAM_API_KEY를 추가하세요"
    fi

    if grep -q "SPRING2_BASE_URL" "$BACKEND_DIR/.env"; then
        echo "✅ Spring2 URL 설정됨"
    fi

    if grep -q "FASTAPI_PORT=8082" "$BACKEND_DIR/.env"; then
        echo "✅ FastAPI 포트 설정됨 (8082)"
    fi

    echo ""
}

# 포트 사용 확인
check_port() {
    local port=$1
    local service=$2

    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ 포트 $port 사용 중 ($service가 실행 중)"
        return 0
    else
        echo "⚠️  포트 $port을 사용할 수 없습니다"
        return 1
    fi
}

# 서버 상태 확인
wait_for_server() {
    local url="http://localhost:8082/health"
    local max_attempts=30
    local attempt=0

    echo ""
    echo "🔄 FastAPI 서버 시작 대기 중..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo "✅ FastAPI 서버 준비 완료"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done

    echo ""
    echo "❌ FastAPI 서버가 시작되지 않았습니다"
    echo "   $url에 접속할 수 없습니다"
    return 1
}

# 테스트 실행
run_test() {
    echo ""
    echo "=================================================="
    echo "🧪 테스트 실행"
    echo "=================================================="
    echo ""

    local test_cmd="python scripts/test_voice_client.py"
    test_cmd="$test_cmd --user-id $USER_ID"
    test_cmd="$test_cmd --scenario-id $SCENARIO_ID"

    if [ "$USE_MIC" = true ]; then
        test_cmd="$test_cmd --use-mic"
        test_cmd="$test_cmd --record-duration $RECORD_DURATION"
    fi

    if [ "$VERBOSE" = true ]; then
        test_cmd="$test_cmd --verbose"
    fi

    echo "📝 명령어: $test_cmd"
    echo ""

    cd "$BACKEND_DIR"
    eval "$test_cmd"
}

# 메인 실행
main() {
    echo ""
    echo "╔════════════════════════════════════════════════╗"
    echo "║  SKALA 음성 롤플레잉 테스트                    ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""

    # 설정 확인
    check_environment
    check_and_install_deps

    # 포트 확인
    echo "=================================================="
    echo "🔌 포트 확인"
    echo "=================================================="
    echo ""

    if ! check_port 8082 "FastAPI"; then
        echo ""
        echo "💡 FastAPI 서버를 먼저 시작하세요:"
        echo "   bash scripts/start_server.sh"
        echo ""
        exit 1
    fi

    if ! check_port 8081 "Spring2"; then
        echo ""
        echo "⚠️  Spring2 서버가 실행 중이 아닙니다"
        echo "   발화 저장 기능이 작동하지 않을 수 있습니다"
    fi

    echo ""

    # 테스트 옵션 확인
    echo "=================================================="
    echo "⚙️  테스트 옵션"
    echo "=================================================="
    echo ""
    echo "사용자 ID: $USER_ID"
    echo "시나리오 ID: $SCENARIO_ID"
    if [ "$USE_MIC" = true ]; then
        echo "입력 방식: 실제 마이크 (${RECORD_DURATION}초)"
    else
        echo "입력 방식: 더미 오디오"
    fi
    if [ "$VERBOSE" = true ]; then
        echo "로깅: 상세 로깅 활성화"
    fi
    echo ""

    # 테스트 실행
    run_test
}

# 메인 함수 실행
main
