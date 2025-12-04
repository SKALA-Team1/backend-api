#!/bin/bash

##############################################################################
# 모든 서비스 시작 스크립트
#
# Redis, MinIO, FastAPI를 한번에 시작합니다.
# (선택사항: Ollama도 함께 시작 가능)
#
# 사용법:
#   bash scripts/start_all_services.sh [옵션]
#
# 옵션:
#   --with-ollama    Ollama도 함께 시작
#   --no-docker      Docker 서비스 스킵 (FastAPI만)
#   --stop           모든 서비스 중단
#   --logs           Docker 컨테이너 로그 확인
#   --status         서비스 상태 확인
#
# 예시:
#   bash scripts/start_all_services.sh
#   bash scripts/start_all_services.sh --with-ollama
#   bash scripts/start_all_services.sh --stop
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
CYAN='\033[0;36m'
NC='\033[0m'

# 기본값
WITH_OLLAMA=true  # Ollama는 무조건 실행
NO_DOCKER=false
STOP_SERVICES=false
SHOW_LOGS=false
SHOW_STATUS=false

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
            --with-ollama)
                WITH_OLLAMA=true
                shift
                ;;
            --no-docker)
                NO_DOCKER=true
                shift
                ;;
            --stop)
                STOP_SERVICES=true
                shift
                ;;
            --logs)
                SHOW_LOGS=true
                shift
                ;;
            --status)
                SHOW_STATUS=true
                shift
                ;;
            *)
                print_error "알 수 없는 옵션: $1"
                exit 1
                ;;
        esac
    done
}

# 서비스 중단
stop_services() {
    print_header "모든 서비스 중단 중..."

    if [ "$NO_DOCKER" != true ]; then
        print_info "Docker 컨테이너 중단..."
        cd "$BACKEND_DIR/infra"
        docker-compose -f docker-compose.dev.yml down 2>/dev/null || print_warning "Docker 컨테이너가 실행 중이지 않습니다"
    fi

    print_info "uvicorn 프로세스 중단..."
    pkill -f "uvicorn" || print_warning "uvicorn 프로세스가 실행 중이지 않습니다"

    if [ "$WITH_OLLAMA" = true ]; then
        print_info "Ollama 중단..."
        pkill -f "ollama" || print_warning "Ollama가 실행 중이지 않습니다"
    fi

    print_success "모든 서비스가 중단되었습니다"
    exit 0
}

# 서비스 상태 확인
check_status() {
    print_header "서비스 상태 확인"

    echo "🐳 Docker 컨테이너:"
    docker ps --filter "name=skala" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "  Docker가 실행 중이지 않습니다"

    echo ""
    echo "🚀 FastAPI 서버:"
    if curl -s http://localhost:8082/docs > /dev/null 2>&1; then
        print_success "FastAPI 서버 실행 중 (http://localhost:8082)"
    else
        print_error "FastAPI 서버 실행 중이지 않습니다"
    fi

    echo ""
    echo "💾 Redis:"
    if redis-cli ping > /dev/null 2>&1; then
        print_success "Redis 실행 중 (localhost:6379)"
    else
        print_error "Redis 실행 중이지 않습니다"
    fi

    echo ""
    echo "📦 MinIO:"
    if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        print_success "MinIO 실행 중 (http://localhost:9000)"
    else
        print_error "MinIO 실행 중이지 않습니다"
    fi

    if [ "$WITH_OLLAMA" = true ]; then
        echo ""
        echo "🧠 Ollama:"
        if curl -s http://localhost:11434 > /dev/null 2>&1; then
            print_success "Ollama 실행 중 (http://localhost:11434)"
        else
            print_error "Ollama 실행 중이지 않습니다"
        fi
    fi

    echo ""
}

# Docker 로그 확인
show_logs() {
    print_header "Docker 컨테이너 로그"

    cd "$BACKEND_DIR/infra"
    docker-compose -f docker-compose.dev.yml logs -f --tail=50
}

# Docker 서비스 시작
start_docker_services() {
    print_header "Docker 서비스 시작 (Redis, MinIO)"

    cd "$BACKEND_DIR/infra"

    # Docker 데몬 확인
    if ! docker ps > /dev/null 2>&1; then
        print_error "Docker가 실행 중이지 않습니다"
        print_warning "Docker를 시작하거나 설치하세요"
        return 1
    fi

    print_info "docker-compose 실행 중..."
    docker-compose -f docker-compose.dev.yml up -d

    # 서비스 준비 대기 (최대 60초)
    print_info "서비스 시작 대기 중..."

    local timeout=60
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        # Docker 헬스 체크로 확인
        local redis_status=$(docker inspect --format='{{.State.Health.Status}}' skala-redis 2>/dev/null || echo "none")
        local minio_status=$(docker inspect --format='{{.State.Health.Status}}' skala-minio 2>/dev/null || echo "none")

        if [ "$redis_status" = "healthy" ] && [ "$minio_status" = "healthy" ]; then
            print_success "모든 Docker 서비스 준비 완료!"
            echo ""
            echo "📊 서비스 URL:"
            echo "  🔴 Redis:  redis://localhost:6379"
            echo "  📦 MinIO API:     http://localhost:9000"
            echo "  🎨 MinIO Console: http://localhost:9001 (minioadmin / minioadmin123)"
            echo ""
            return 0
        fi

        echo -n "."
        sleep 1
        elapsed=$((elapsed + 1))
    done

    print_error "Docker 서비스 시작 타임아웃"
    return 1
}

# Ollama 서비스 시작
start_ollama() {
    print_header "Ollama 시작"

    if ! command -v ollama &> /dev/null; then
        print_error "Ollama가 설치되어 있지 않습니다"
        print_warning "설치: https://ollama.ai"
        return 1
    fi

    # Ollama가 이미 실행 중인지 확인
    if curl -s http://localhost:11434 > /dev/null 2>&1; then
        print_success "Ollama가 이미 실행 중입니다 (http://localhost:11434)"

        # mistral 모델 확인 및 다운로드
        if ! ollama list | grep -q "mistral"; then
            print_warning "mistral 모델이 설치되지 않았습니다. 다운로드 중..."
            ollama pull mistral
            print_success "mistral 모델 다운로드 완료"
        else
            print_success "mistral 모델이 이미 설치되어 있습니다"
        fi

        return 0
    fi

    print_info "Ollama 시작 중..."
    ollama serve &
    OLLAMA_PID=$!
    print_info "Ollama 시작 (PID: $OLLAMA_PID)"

    # Ollama 시작 대기 (최대 60초)
    local timeout=60
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -s http://localhost:11434 > /dev/null 2>&1; then
            print_success "Ollama 시작 완료 (http://localhost:11434)"
            echo ""

            # mistral 모델 자동 다운로드
            print_info "mistral 모델 확인 중..."
            if ! ollama list | grep -q "mistral"; then
                print_warning "mistral 모델을 다운로드합니다 (처음 실행 시 약 5분 소요)..."
                ollama pull mistral
                print_success "mistral 모델 다운로드 완료"
            else
                print_success "mistral 모델이 이미 설치되어 있습니다"
            fi

            echo ""
            echo "📚 현재 사용 가능한 모델:"
            ollama list | tail -n +2 || echo "  (모델 없음)"
            echo ""
            return 0
        fi

        echo -n "."
        sleep 1
        elapsed=$((elapsed + 1))
    done

    print_error "Ollama 시작 타임아웃 (${timeout}초)"
    return 1
}

# FastAPI 서버 시작
start_fastapi() {
    print_header "FastAPI 서버 시작 (포트 8082)"

    cd "$BACKEND_DIR"

    # 환경 변수 확인
    if [ ! -f ".env" ]; then
        print_warning ".env 파일을 찾을 수 없습니다 (기본 설정으로 진행)"
    fi

    print_info "FastAPI 서버 시작 중... (포트 8082)"
    python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8082 \
        --reload
}

# 메인 함수
main() {
    parse_args "$@"

    # 옵션별 처리
    if [ "$STOP_SERVICES" = true ]; then
        stop_services
    fi

    if [ "$SHOW_STATUS" = true ]; then
        check_status
        exit 0
    fi

    if [ "$SHOW_LOGS" = true ]; then
        show_logs
        exit 0
    fi

    # 서비스 시작
    print_header "SKALA 서비스 시작"

    echo "📋 시작할 서비스:"
    [ "$NO_DOCKER" != true ] && echo "  ✓ Docker (Redis, MinIO)" || echo "  ✗ Docker 스킵"
    echo "  ✓ FastAPI (포트 8082)"
    [ "$WITH_OLLAMA" = true ] && echo "  ✓ Ollama (포트 11434)" || echo "  ✗ Ollama 스킵"
    echo ""

    # Docker 서비스 시작
    if [ "$NO_DOCKER" != true ]; then
        if ! start_docker_services; then
            print_error "Docker 서비스 시작 실패"
            print_info "다시 시도하려면: docker-compose -f infra/docker-compose.dev.yml up"
            exit 1
        fi
    fi

    # Ollama 시작
    if [ "$WITH_OLLAMA" = true ]; then
        if ! start_ollama; then
            print_warning "Ollama 시작 실패 (계속 진행합니다)"
        fi
    fi

    echo ""
    print_success "모든 서비스 준비 완료!"
    echo ""
    echo "📊 서비스 포트:"
    echo "  🔴 Redis:  redis://localhost:6379"
    echo "  📦 MinIO:  http://localhost:9000 (minioadmin / minioadmin123)"
    echo "  🚀 FastAPI: http://localhost:8082"
    [ "$WITH_OLLAMA" = true ] && echo "  🧠 Ollama:  http://localhost:11434"
    echo ""
    echo "📖 다른 터미널에서 음성 테스트 실행:"
    echo "  bash scripts/roleplay_voice_interactive.sh"
    echo ""
    echo "🛑 중단하려면 Ctrl+C를 누르세요"
    echo ""

    # FastAPI 서버 시작 (포그라운드)
    start_fastapi
}

main "$@"