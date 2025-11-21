#!/bin/bash

################################################################################
# 음성 기반 롤플레잉 자동화 테스트
################################################################################
# 기능:
#   1. Redis Docker 컨테이너 시작
#   2. Ollama Docker 컨테이너 시작 및 모델 다운로드
#   3. FastAPI 서버 시작
#   4. 음성 기반 롤플레잉 테스트 실행
#
# 사용법:
#   bash scripts/test_voice_automated.sh [옵션]
#
# 옵션:
#   --skip-docker       Docker 시작 건너뛰기
#   --skip-server       FastAPI 서버 시작 건너뛰기
#   --only-test         테스트만 실행
#   --help              도움말
################################################################################

set -e

# ============================================================================
# 프로젝트 경로 설정
# ============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$PROJECT_ROOT/scripts"

# ============================================================================
# 환경변수 (.env에서 읽기)
# ============================================================================

# .env 파일 로드
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo "❌ .env 파일을 찾을 수 없습니다"
    exit 1
fi

# 기본값 설정 (필요한 경우)
FASTAPI_PORT=${FASTAPI_PORT:-8082}
FASTAPI_HOST="127.0.0.1"
FASTAPI_URL="http://$FASTAPI_HOST:$FASTAPI_PORT"
WS_BASE_URL="${WS_BASE_URL:-ws://localhost:8082}"

REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
REDIS_CONTAINER="redis-voice-test"

OLLAMA_CONTAINER="ollama-voice-test"
OLLAMA_PORT="11434"
OLLAMA_MODEL="mistral"

# 타임아웃
STARTUP_TIMEOUT=60
TEST_TIMEOUT=120

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 플래그
SKIP_DOCKER=false
SKIP_SERVER=false
ONLY_TEST=false

# ============================================================================
# 헬퍼 함수
# ============================================================================

print_header() {
    echo -e "\n${BLUE}══════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════${NC}\n"
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

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

wait_for_service() {
    local url=$1
    local timeout=$2
    local service_name=$3
    local elapsed=0

    print_info "서비스 시작 대기 중: $service_name"

    while [ $elapsed -lt $timeout ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service_name 시작됨"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    print_error "$service_name 시작 실패 (timeout: ${timeout}s)"
    return 1
}

check_prerequisites() {
    print_header "전제 조건 확인"

    if ! command -v docker &> /dev/null; then
        print_error "Docker이 설치되지 않았습니다"
        exit 1
    fi
    print_success "Docker 설치됨"

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3이 설치되지 않았습니다"
        exit 1
    fi
    print_success "Python 3 설치됨"

    if ! command -v curl &> /dev/null; then
        print_error "curl이 설치되지 않았습니다"
        exit 1
    fi
    print_success "curl 설치됨"
}

start_redis() {
    print_header "Redis Docker 시작"

    # 기존 컨테이너 정리
    if docker ps -a --format '{{.Names}}' | grep -q "^$REDIS_CONTAINER$"; then
        print_info "기존 Redis 컨테이너 제거 중..."
        docker stop $REDIS_CONTAINER 2>/dev/null || true
        docker rm $REDIS_CONTAINER 2>/dev/null || true
        sleep 1
    fi

    # Redis 시작
    docker run -d \
        --name $REDIS_CONTAINER \
        -p $REDIS_PORT:6379 \
        redis:7-alpine \
        redis-server --appendonly no

    sleep 2

    # Redis 상태 확인
    if docker exec $REDIS_CONTAINER redis-cli ping | grep -q "PONG"; then
        print_success "Redis 시작됨"
        return 0
    else
        print_error "Redis 시작 실패"
        return 1
    fi
}

start_ollama() {
    print_header "Ollama Docker 시작"

    # 기존 컨테이너 정리
    if docker ps -a --format '{{.Names}}' | grep -q "^$OLLAMA_CONTAINER$"; then
        print_info "기존 Ollama 컨테이너 제거 중..."
        docker stop $OLLAMA_CONTAINER 2>/dev/null || true
        docker rm $OLLAMA_CONTAINER 2>/dev/null || true
        sleep 1
    fi

    # Ollama 이미지 확인
    if ! docker images | grep -q "ollama"; then
        print_info "Ollama 이미지 다운로드 중..."
        docker pull ollama/ollama
    fi

    # Ollama 시작
    docker run -d \
        --name $OLLAMA_CONTAINER \
        -p $OLLAMA_PORT:11434 \
        -v ollama_volume:/root/.ollama \
        ollama/ollama

    sleep 3

    # Ollama 상태 확인
    if wait_for_service "http://127.0.0.1:$OLLAMA_PORT/api/tags" $STARTUP_TIMEOUT "Ollama API"; then
        # 모델 다운로드
        print_info "Ollama 모델 다운로드 중: $OLLAMA_MODEL"
        docker exec $OLLAMA_CONTAINER ollama pull $OLLAMA_MODEL
        print_success "Ollama 모델 준비 완료"
        return 0
    else
        print_error "Ollama 시작 실패"
        return 1
    fi
}

start_fastapi() {
    print_header "FastAPI 서버 시작"

    print_info "환경변수 확인:"
    print_info "  DATABASE_URL: $DATABASE_URL"
    print_info "  REDIS_URL: $REDIS_URL"
    print_info "  WS_BASE_URL: $WS_BASE_URL"
    print_info "  FASTAPI_PORT: $FASTAPI_PORT"
    print_info "  DEEPGRAM_API_KEY: ${DEEPGRAM_API_KEY:0:10}..."

    cd "$PROJECT_ROOT"

    # FastAPI 서버 시작 (백그라운드)
    python3 -m uvicorn app.main:app \
        --host $FASTAPI_HOST \
        --port $FASTAPI_PORT \
        --reload \
        > /tmp/fastapi.log 2>&1 &

    FASTAPI_PID=$!
    echo $FASTAPI_PID > /tmp/fastapi.pid

    print_info "FastAPI 시작 (PID: $FASTAPI_PID)"

    # 서버 시작 대기
    if wait_for_service "$FASTAPI_URL/health/ping" $STARTUP_TIMEOUT "FastAPI"; then
        print_success "FastAPI 실행 중: $FASTAPI_URL"
        return 0
    else
        print_error "FastAPI 시작 실패"
        print_warning "로그 확인: tail -f /tmp/fastapi.log"
        return 1
    fi
}

run_test() {
    print_header "음성 기반 롤플레잉 테스트"

    cd "$PROJECT_ROOT"

    print_info "테스트 시나리오:"
    print_info "  1. REST API로 세션 생성"
    print_info "  2. WebSocket 연결"
    print_info "  3. INIT 메시지 전송"
    print_info "  4. 더미 오디오 청크 전송"
    print_info "  5. UTTERANCE_END 메시지 전송"
    print_info "  6. STT 결과 및 AI 응답 수신"
    print_info "  7. END_SESSION으로 종료\n"

    # Python 테스트 실행
    # timeout 명령어 확인 (macOS는 gtimeout, Linux는 timeout)
    if command -v timeout &> /dev/null; then
        timeout $TEST_TIMEOUT python3 "$SCRIPT_DIR/test_voice_client.py"
    elif command -v gtimeout &> /dev/null; then
        gtimeout $TEST_TIMEOUT python3 "$SCRIPT_DIR/test_voice_client.py"
    else
        # timeout 없으면 그냥 실행
        python3 "$SCRIPT_DIR/test_voice_client.py"
    fi

    return $?
}

cleanup() {
    print_header "정리"

    # FastAPI 종료
    if [ -f /tmp/fastapi.pid ]; then
        PID=$(cat /tmp/fastapi.pid)
        if ps -p $PID > /dev/null 2>&1; then
            print_info "FastAPI 종료 중 (PID: $PID)"
            kill $PID 2>/dev/null || true
            sleep 1
        fi
        rm /tmp/fastapi.pid
    fi

    # Docker 컨테이너 정지 (선택사항)
    if [ "$1" != "keep" ]; then
        print_info "Docker 컨테이너 정지 중..."
        docker stop $REDIS_CONTAINER 2>/dev/null || true
        docker stop $OLLAMA_CONTAINER 2>/dev/null || true
    else
        print_warning "Docker 컨테이너는 계속 실행 중"
        print_info "수동 정지: docker stop $REDIS_CONTAINER $OLLAMA_CONTAINER"
    fi

    print_success "정리 완료"
}

show_help() {
    cat << EOF
${BLUE}음성 기반 롤플레잉 자동화 테스트${NC}

${GREEN}사용법:${NC}
  bash $0 [옵션]

${GREEN}옵션:${NC}
  --skip-docker       Docker 시작 건너뛰기
  --skip-server       FastAPI 서버 시작 건너뛰기
  --only-test         테스트만 실행
  --keep-docker       테스트 후 Docker 컨테이너 유지
  --help              이 도움말 표시

${GREEN}예시:${NC}
  # 전체 자동화
  bash $0

  # Docker 건너뛰기 (이미 실행 중인 경우)
  bash $0 --skip-docker

  # 테스트만 실행
  bash $0 --only-test

${GREEN}환경 설정:${NC}
  설정은 .env 파일에서 자동으로 로드됩니다:
  - DATABASE_URL
  - REDIS_URL
  - FASTAPI_PORT
  - DEEPGRAM_API_KEY
  - WS_BASE_URL

${GREEN}로그 확인:${NC}
  FastAPI:   tail -f /tmp/fastapi.log
  Redis:     docker logs $REDIS_CONTAINER
  Ollama:    docker logs $OLLAMA_CONTAINER

EOF
}

# ============================================================================
# 옵션 파싱
# ============================================================================

KEEP_DOCKER="keep"

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-server)
            SKIP_SERVER=true
            shift
            ;;
        --only-test)
            ONLY_TEST=true
            SKIP_DOCKER=true
            SKIP_SERVER=true
            shift
            ;;
        --keep-docker)
            KEEP_DOCKER=""
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            print_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================================================
# 메인 로직
# ============================================================================

main() {
    print_header "음성 기반 롤플레잉 자동화 테스트"

    # 1. 전제 조건 확인
    check_prerequisites

    # 2. Docker 서비스 시작
    if [ "$SKIP_DOCKER" = false ]; then
        start_redis || exit 1
        start_ollama || exit 1
    else
        print_info "Docker 시작 건너뛰기"
    fi

    # 3. FastAPI 서버 시작
    if [ "$SKIP_SERVER" = false ]; then
        start_fastapi || exit 1
    else
        print_info "FastAPI 서버 시작 건너뛰기"
    fi

    # 4. 테스트 실행
    if run_test; then
        print_success "테스트 성공! ✅"
        RESULT=0
    else
        print_error "테스트 실패"
        RESULT=1
    fi

    # 5. 정리
    cleanup $KEEP_DOCKER

    # 종료
    if [ $RESULT -eq 0 ]; then
        print_header "완료 ✅"
        exit 0
    else
        print_header "실패 ❌"
        exit 1
    fi
}

# Ctrl+C 핸들러
trap "cleanup; exit 130" INT TERM

# 실행
main