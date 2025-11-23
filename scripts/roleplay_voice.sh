#!/bin/bash

##############################################################################
# 음성 기반 롤플레잉 테스트
#
# 실제 마이크 음성으로 롤플레잉을 테스트합니다.
#
# 사용법:
#   bash scripts/roleplay_voice.sh [옵션]
#
# 옵션:
#   --record-duration N  녹음 시간 (초, 기본값: 10)
#   --iterations N       테스트 반복 횟수 (기본값: 1)
#   --verbose           상세 로깅 활성화
#   --server-only       서버만 시작 (테스트 미실행)
#
# 예시:
#   bash scripts/roleplay_voice.sh
#   bash scripts/roleplay_voice.sh --record-duration 5
#   bash scripts/roleplay_voice.sh --iterations 3 --verbose
#
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 색상
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 기본값
RECORD_DURATION=10
ITERATIONS=1
VERBOSE=false
SERVER_ONLY=false
FASTAPI_URL="http://localhost:8082"
FASTAPI_PID=""

print_header() {
    echo ""
    echo -e "${BLUE}==================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==================================================${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 커맨드라인 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --record-duration)
                RECORD_DURATION="$2"
                shift 2
                ;;
            --iterations)
                ITERATIONS="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --server-only)
                SERVER_ONLY=true
                shift
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                exit 1
                ;;
        esac
    done
}

cleanup() {
    if [ ! -z "$FASTAPI_PID" ]; then
        if kill $FASTAPI_PID 2>/dev/null; then
            print_success "서버 종료됨"
        fi
    fi
}

trap cleanup EXIT INT TERM

# 서버 상태 확인
check_server() {
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$FASTAPI_URL/docs" > /dev/null 2>&1; then
            print_success "서버가 준비되었습니다"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done

    echo ""
    print_error "서버 준비 타임아웃"
    return 1
}

# FastAPI 서버 시작
start_server() {
    print_header "FastAPI 서버 시작"

    cd "$BACKEND_DIR"

    # 포트 사용 여부 확인
    if lsof -i :8082 > /dev/null 2>&1; then
        print_info "포트 8082가 이미 사용 중입니다"
        if check_server; then
            return 0
        else
            return 1
        fi
    fi

    # 새 서버 시작
    python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8082 \
        --reload \
        > /dev/null 2>&1 &

    FASTAPI_PID=$!
    print_info "FastAPI 서버 시작됨 (PID: $FASTAPI_PID)"

    if check_server; then
        return 0
    else
        return 1
    fi
}

# 음성 테스트
run_test() {
    local iteration=$1

    print_header "음성 기반 롤플레잉 (${iteration}/${ITERATIONS})"

    print_warning "마이크 사용:"
    echo "  • 녹음이 시작되면 마이크에 대고 명확하게 말씀해주세요"
    echo "  • 녹음 시간: ${RECORD_DURATION}초"
    echo "  • 예: \"The answer is in the logs\""
    echo ""
    read -p "준비되셨으면 엔터를 눌러주세요: "
    echo ""

    cd "$BACKEND_DIR"

    # 테스트 옵션 구성
    local test_args="--fastapi-url $FASTAPI_URL --user-id 1 --scenario-id 1 --use-mic --record-duration $RECORD_DURATION"

    if [ "$VERBOSE" = true ]; then
        test_args="$test_args --verbose"
    fi

    if python scripts/test_voice_client.py $test_args; then
        print_success "테스트 ${iteration} 통과"
        return 0
    else
        print_error "테스트 ${iteration} 실패"
        return 1
    fi
}

main() {
    parse_args "$@"

    print_header "음성 기반 롤플레잉 테스트"
    echo "구성:"
    echo "  녹음 시간: ${RECORD_DURATION}초"
    echo "  반복 횟수: $ITERATIONS"
    echo "  상세 로깅: $([ "$VERBOSE" = true ] && echo "활성화" || echo "비활성화")"

    # 서버 시작
    if ! start_server; then
        print_error "서버 시작 실패"
        exit 1
    fi

    # 테스트 실행
    if [ "$SERVER_ONLY" != true ]; then
        local failed=0
        for i in $(seq 1 $ITERATIONS); do
            if ! run_test $i; then
                failed=$((failed + 1))
            fi

            if [ $i -lt $ITERATIONS ]; then
                print_info "$((ITERATIONS - i))회 더 진행합니다"
                sleep 2
            fi
        done

        # 결과 요약
        print_header "테스트 결과"
        local passed=$((ITERATIONS - failed))
        echo "통과: $passed / $ITERATIONS"

        if [ $failed -eq 0 ]; then
            print_success "모든 테스트를 통과했습니다!"
        else
            print_warning "$failed개 테스트 실패 (마이크/STT 문제일 수 있음)"
            echo ""
            echo "해결책:"
            echo "  1. 마이크 설정 확인 (System Settings → Sound → Input)"
            echo "  2. 마이크 권한 확인 (System Settings → Privacy & Security → Microphone)"
            echo "  3. 텍스트 모드로 먼저 테스트 (bash scripts/roleplay_text.sh)"
            exit 1
        fi
    else
        print_success "서버가 실행 중입니다"
        print_info "다른 터미널에서 테스트를 실행할 수 있습니다"
        wait
    fi
}

main "$@"