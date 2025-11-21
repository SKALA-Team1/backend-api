#!/bin/bash

##############################################################################
# 음성 기반 롤플레잉 통합 테스트 스크립트
#
# 사용법:
#   bash scripts/test_voice_flow.sh [옵션]
#
# 옵션:
#   --use-mic                실제 마이크 사용 (기본값: 더미 오디오)
#   --record-duration N      녹음 시간 (초, 기본값: 3)
#   --iterations N           테스트 반복 횟수 (기본값: 1)
#   --server-only            서버만 시작 (테스트 미실행)
#   --test-only              테스트만 실행 (서버 미시작)
#   --verbose                상세 로깅 활성화
#   --interactive            대화형 모드 (각 단계마다 엔터 필요)
#
# 예시:
#   bash scripts/test_voice_flow.sh                           # 더미 오디오, 1회
#   bash scripts/test_voice_flow.sh --use-mic                 # 실제 마이크, 1회
#   bash scripts/test_voice_flow.sh --use-mic --iterations 3  # 3회 반복
#   bash scripts/test_voice_flow.sh --interactive              # 대화형 모드
#
# 마이크 버튼 역할 (자동화 방식):
#   1. 대화 시작: INIT 메시지 전송 → AI 첫 인사
#   2. 사용자 발화: 오디오 청크 전송 (마이크 또는 더미)
#   3. 발화 종료: UTTERANCE_END 메시지 → STT → AI 응답
#   4. 반복: 2-3번 반복 (다중 턴 대화)
#   5. 대화 종료: END_SESSION 메시지
#
# 대화형 모드에서 마이크 버튼 역할:
#   - 각 단계마다 엔터 키를 눌러 다음 단계 진행
#   - Ctrl+C로 언제든 중단 가능
##############################################################################

set -e  # 에러 발생 시 스크립트 중단

# ============================================================================
# 설정 및 색상
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${BACKEND_DIR}/logs"
SERVER_LOG="${LOG_DIR}/server.log"
TEST_LOG="${LOG_DIR}/test.log"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본 옵션값
USE_MIC=false
RECORD_DURATION=3
ITERATIONS=1
SERVER_ONLY=false
TEST_ONLY=false
VERBOSE=false
INTERACTIVE=false
FASTAPI_URL="http://localhost:8082"
FASTAPI_PID=""

# ============================================================================
# 함수 정의
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=================================================="
    echo "$1"
    echo "==================================================${NC}"
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
            --use-mic)
                USE_MIC=true
                shift
                ;;
            --record-duration)
                RECORD_DURATION="$2"
                shift 2
                ;;
            --iterations)
                ITERATIONS="$2"
                shift 2
                ;;
            --server-only)
                SERVER_ONLY=true
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --interactive)
                INTERACTIVE=true
                shift
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

print_usage() {
    echo "사용법: bash scripts/test_voice_flow.sh [옵션]"
    echo ""
    echo "옵션:"
    echo "  --use-mic                실제 마이크 사용"
    echo "  --record-duration N      녹음 시간 (초)"
    echo "  --iterations N           테스트 반복 횟수"
    echo "  --server-only            서버만 시작"
    echo "  --test-only              테스트만 실행"
    echo "  --verbose                상세 로깅 활성화"
    echo "  --interactive            대화형 모드"
}

cleanup() {
    print_header "정리 중"

    if [ ! -z "$FASTAPI_PID" ]; then
        print_info "FastAPI 서버 종료 중... (PID: $FASTAPI_PID)"
        if kill $FASTAPI_PID 2>/dev/null; then
            print_success "서버 종료됨"
        else
            print_warning "서버를 이미 종료했거나 찾을 수 없습니다"
        fi
    fi
}

# Ctrl+C 처리
trap cleanup EXIT INT TERM

# 로그 디렉토리 생성
setup_logs() {
    mkdir -p "$LOG_DIR"
    echo "" > "$SERVER_LOG"
    echo "" > "$TEST_LOG"
    print_success "로그 디렉토리 준비: $LOG_DIR"
}

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
    print_error "서버 준비 타임아웃 (${max_attempts}초)"
    return 1
}

# FastAPI 서버 시작
start_server() {
    if [ "$TEST_ONLY" = true ]; then
        print_info "테스트 전용 모드: 서버 시작 생략"
        return 0
    fi

    print_header "FastAPI 서버 시작"

    cd "$BACKEND_DIR"

    # 포트 사용 여부 확인
    if lsof -i :8082 > /dev/null 2>&1; then
        print_warning "포트 8082가 이미 사용 중입니다"
        print_info "기존 서버를 사용합니다"

        if check_server; then
            return 0
        else
            print_error "기존 서버에 연결할 수 없습니다"
            return 1
        fi
    fi

    # 새 서버 시작
    python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8082 \
        >> "$SERVER_LOG" 2>&1 &

    FASTAPI_PID=$!
    print_info "FastAPI 서버 시작됨 (PID: $FASTAPI_PID)"

    # 서버 준비 대기
    if check_server; then
        return 0
    else
        return 1
    fi
}

# 대화형 대기
wait_for_interaction() {
    if [ "$INTERACTIVE" = true ]; then
        echo ""
        read -p "다음 단계로 진행하려면 엔터를 눌러주세요 (또는 'q' + 엔터로 중단): " input

        if [ "$input" = "q" ]; then
            print_warning "사용자에 의해 중단됨"
            exit 0
        fi
    fi
}

# 테스트 실행
run_test() {
    local iteration=$1

    print_header "음성 테스트 (${iteration}/${ITERATIONS})"

    # 테스트 옵션 구성
    local test_args="--fastapi-url $FASTAPI_URL"
    test_args="$test_args --user-id 1 --scenario-id 1"

    if [ "$USE_MIC" = true ]; then
        test_args="$test_args --use-mic --record-duration $RECORD_DURATION"
        print_info "모드: 실제 마이크 (${RECORD_DURATION}초)"
    else
        print_info "모드: 더미 오디오"
    fi

    if [ "$VERBOSE" = true ]; then
        test_args="$test_args --verbose"
        print_info "상세 로깅 활성화"
    fi

    echo ""
    print_info "테스트 시작..."
    echo "명령어: python scripts/test_voice_client.py $test_args"
    echo ""

    if python scripts/test_voice_client.py $test_args 2>&1 | tee -a "$TEST_LOG"; then
        print_success "테스트 ${iteration} 통과"
        wait_for_interaction
        return 0
    else
        print_error "테스트 ${iteration} 실패"
        return 1
    fi
}

# 전체 시나리오 실행
run_scenario() {
    print_header "음성 기반 롤플레잉 시나리오"
    print_info "각 대화는 다음 단계를 거칩니다:"
    echo "  1️⃣  세션 생성 (REST API)"
    echo "  2️⃣  WebSocket 연결"
    echo "  3️⃣  INIT 메시지 → AI 첫 인사"
    echo "  4️⃣  사용자 발화 (오디오 전송)"
    echo "  5️⃣  UTTERANCE_END → STT → AI 응답"
    echo "  6️⃣  대화 반복 또는 종료"
    echo ""

    if [ "$USE_MIC" = true ]; then
        print_warning "마이크 모드 주의사항:"
        echo "  - 각 발화 단계에서 마이크에 대고 말씀해주세요"
        echo "  - 녹음 시간: ${RECORD_DURATION}초"
        echo "  - 다시 시작하려면 Ctrl+C를 누르세요"
    fi

    echo ""
    wait_for_interaction

    # 반복 테스트
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
        return 0
    else
        print_error "$failed개 테스트 실패"
        return 1
    fi
}

# ============================================================================
# 메인 실행
# ============================================================================

main() {
    parse_args "$@"

    print_header "음성 기반 롤플레잉 통합 테스트"
    echo "구성:"
    echo "  마이크 모드: $([ "$USE_MIC" = true ] && echo "실제 마이크" || echo "더미 오디오")"
    echo "  녹음 시간: ${RECORD_DURATION}초"
    echo "  반복 횟수: $ITERATIONS"
    echo "  상세 로깅: $([ "$VERBOSE" = true ] && echo "활성화" || echo "비활성화")"
    echo "  대화형 모드: $([ "$INTERACTIVE" = true ] && echo "활성화" || echo "비활성화")"

    # 로그 디렉토리 설정
    setup_logs

    # 서버 시작
    if ! start_server; then
        print_error "서버 시작 실패"
        exit 1
    fi

    # 테스트 전용이 아닌 경우 테스트 실행
    if [ "$SERVER_ONLY" != true ]; then
        if ! run_scenario; then
            exit 1
        fi
    else
        print_success "서버가 실행 중입니다"
        print_info "다른 터미널에서 테스트를 실행할 수 있습니다:"
        echo "  python scripts/test_voice_client.py --use-mic"
        echo ""
        print_info "서버를 중단하려면 Ctrl+C를 누르세요"

        # 서버 유지
        wait
    fi
}

# 실행
main "$@"