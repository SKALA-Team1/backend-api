#!/bin/bash

##############################################################################
# Spacebar 기반 음성 롤플레잉 대화 (10턴)
#
# 스페이스바로 마이크를 활성화/비활성화하면서
# 10턴의 음성 기반 롤플레이을 진행합니다.
#
# 사용법:
#   bash scripts/roleplay_voice_interactive.sh [옵션]
#
# 옵션:
#   --record-duration N  한 번에 녹음할 최대 시간 (초, 기본값: 5)
#   --verbose           상세 로깅 활성화
#   --server-only       서버만 시작 (테스트 미실행)
#
# 사용 방법:
#   1. 스크립트 실행
#   2. AI 첫 질문 대기
#   3. 스페이스바 누르기 → 마이크 활성화 (파란색)
#   4. 대고 말하기
#   5. 스페이스바 뗌 → 마이크 비활성화, STT 변환 시작
#   6. 10턴까지 반복
#
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 환경 설정 로드
source "$SCRIPT_DIR/config.sh"

# 기본값
RECORD_DURATION=5
VERBOSE=false
SERVER_ONLY=false
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

print_ai() {
    echo -e "${CYAN}🤖 AI:${NC} $1"
}

# 커맨드라인 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --record-duration)
                RECORD_DURATION="$2"
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

# 음성 대화 테스트
run_voice_interactive() {
    print_header "Spacebar 기반 음성 롤플레이 - 10턴"

    print_warning "🎙️  사용 방법 (토글 방식):"
    echo "  1️⃣  스페이스바 누르기 → 마이크 활성화 (🔴 RECORDING)"
    echo "  2️⃣  대고 말하기 → \"The answer is in the logs\" 같은 답변"
    echo "  3️⃣  스페이스바 다시 누르기 → 마이크 비활성화, STT 변환 시작"
    echo "  4️⃣  AI 응답 대기"
    echo "  5️⃣  10턴까지 반복"
    echo ""
    print_info "녹음 최대 시간: ${RECORD_DURATION}초"
    echo ""
    read -p "준비되셨으면 엔터를 눌러주세요: "
    echo ""

    cd "$BACKEND_DIR"

    # Python 음성 클라이언트 실행
    $PYTHON_BIN "$SCRIPTS_DIR/voice_client.py" \
        "$RECORD_DURATION" \
        "$([ "$VERBOSE" = true ] && echo "verbose" || echo "")" \
        "$FASTAPI_URL"
}

main() {
    parse_args "$@"

    print_header "Spacebar 기반 음성 롤플레이 테스트"
    echo "구성:"
    echo "  최대 녹음 시간: ${RECORD_DURATION}초"
    echo "  상세 로깅: $([ "$VERBOSE" = true ] && echo "활성화" || echo "비활성화")"

    # 서버 시작
    if ! start_server; then
        print_error "서버 시작 실패"
        exit 1
    fi

    # 테스트 실행
    if [ "$SERVER_ONLY" != true ]; then
        run_voice_interactive
    else
        print_success "서버가 실행 중입니다"
        print_info "다른 터미널에서 음성 대화형 테스트를 실행할 수 있습니다:"
        echo "  bash scripts/roleplay_voice_interactive.sh"
        wait
    fi
}

main "$@"