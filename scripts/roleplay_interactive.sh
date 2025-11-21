#!/bin/bash

##############################################################################
# 대화형 텍스트 기반 롤플레잉
#
# 사용자가 터미널에서 직접 텍스트를 입력하여
# 실시간으로 AI와 대화하는 롤플레잉 시스템입니다.
#
# 사용법:
#   bash scripts/roleplay_interactive.sh [옵션]
#
# 옵션:
#   --verbose          상세 로깅 활성화
#   --server-only      서버만 시작 (테스트 미실행)
#
# 예시:
#   bash scripts/roleplay_interactive.sh
#   bash scripts/roleplay_interactive.sh --verbose
#
# 사용법:
#   1. 서버 시작 후 스크립트 실행
#   2. 터미널에서 직접 메시지 입력
#   3. 'quit' 또는 'exit' 입력하면 종료
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

print_ai() {
    echo -e "${CYAN}🤖 AI:${NC} $1"
}

print_user() {
    echo -e "${GREEN}👤 You:${NC} $1"
}

# 커맨드라인 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
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

# 대화형 테스트
run_interactive() {
    print_header "대화형 롤플레잉 - 실시간 입력 모드"

    print_warning "안내:"
    echo "  • 터미널에서 직접 메시지를 입력합니다"
    echo "  • AI가 즉시 응답합니다"
    echo "  • 'quit' 또는 'exit'로 종료합니다"
    echo ""

    cd "$BACKEND_DIR"

    python3 << 'EOF'
import asyncio
import json
import logging
import httpx
import websockets
import sys

log_level = logging.DEBUG if sys.argv[1] == "verbose" else logging.INFO
logging.basicConfig(level=log_level, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

FASTAPI_URL = "http://localhost:8082"
WS_URL_BASE = "ws://localhost:8082/ws/roleplaying"

# 색상
CYAN = '\033[0;36m'
GREEN = '\033[0;32m'
NC = '\033[0m'

async def interactive_roleplay():
    try:
        # 1. 세션 생성
        logger.info("🔧 세션 생성 중...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_URL}/roleplaying/sessions",
                json={"userId": 1, "scenarioId": 1},
                timeout=10.0
            )
            data = response.json()
            session_id = data.get("session_id")
            scenario = data.get("scenario")
            logger.info(f"✅ 세션 생성됨: {session_id}")

        # 2. WebSocket 연결
        logger.info("🔗 WebSocket 연결 중...")
        ws = await websockets.connect(f"{WS_URL_BASE}/{session_id}")
        logger.info("✅ WebSocket 연결됨")

        # 3. INIT 메시지
        logger.info("📤 INIT 메시지 전송...")
        init_msg = {
            "type": "INIT",
            "userId": 1,
            "subjectId": scenario.get("subjectId"),
            "myRole": scenario.get("myRole"),
            "aiRole": scenario.get("aiRole"),
            "fixedQuestions": scenario.get("fixedQuestions", [])
        }
        await ws.send(json.dumps(init_msg))

        # ACK + 첫 질문 수신
        ack = await ws.recv()
        ai_q1 = await ws.recv()
        data = json.loads(ai_q1)

        print()
        print(f"{CYAN}🤖 AI:{NC} {data.get('text')}")
        print()

        # 4. 대화 루프
        turn = 1
        while True:
            # 사용자 입력
            try:
                user_input = input(f"{GREEN}👤 You (turn {turn}): {NC}").strip()
            except EOFError:
                # Ctrl+D 입력
                break

            # 종료 명령어 확인
            if user_input.lower() in ['quit', 'exit', 'q']:
                logger.info("사용자가 대화를 종료했습니다")
                break

            # 빈 입력 무시
            if not user_input:
                print("⚠️  입력을 해주세요")
                continue

            # USER_TEXT 메시지 전송
            user_msg = {
                "type": "USER_TEXT",
                "text": user_input
            }
            await ws.send(json.dumps(user_msg))

            # AI 응답 수신
            ai_response = None
            try:
                while True:
                    response = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    msg_data = json.loads(response)
                    msg_type = msg_data.get("type")

                    if msg_type == "AI_TEXT":
                        ai_response = msg_data.get("text")
                        print()
                        print(f"{CYAN}🤖 AI:{NC} {ai_response}")
                        print()
                        break
                    elif msg_type == "ERROR":
                        logger.warning(f"서버 에러: {msg_data.get('message')}")
            except asyncio.TimeoutError:
                logger.error("❌ AI 응답 타임아웃")
                break

            if ai_response is None:
                logger.error("❌ AI 응답을 받지 못했습니다")
                break

            turn += 1

        # 5. 세션 종료
        logger.info("🛑 END_SESSION 메시지 전송...")
        await ws.send(json.dumps({"type": "END_SESSION"}))

        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            if json.loads(response).get("type") == "SESSION_ENDED":
                logger.info("✅ 세션 종료됨")
        except asyncio.TimeoutError:
            pass

        await ws.close()
        print()
        logger.info("=" * 50)
        logger.info("✅ 대화 완료!")
        logger.info("=" * 50)
        return True

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        return False

result = asyncio.run(interactive_roleplay())
sys.exit(0 if result else 1)
EOF
}

main() {
    parse_args "$@"

    print_header "대화형 롤플레잉 테스트"
    echo "구성:"
    echo "  상세 로깅: $([ "$VERBOSE" = true ] && echo "활성화" || echo "비활성화")"

    # 서버 시작
    if ! start_server; then
        print_error "서버 시작 실패"
        exit 1
    fi

    # 테스트 실행
    if [ "$SERVER_ONLY" != true ]; then
        run_interactive
    else
        print_success "서버가 실행 중입니다"
        print_info "다른 터미널에서 대화형 테스트를 실행할 수 있습니다:"
        echo "  bash scripts/roleplay_interactive.sh"
        wait
    fi
}

main "$@"