#!/bin/bash

##############################################################################
# 텍스트 기반 롤플레잉 테스트
#
# STT 없이 텍스트로 직접 대화하는 롤플레잉 시스템을 테스트합니다.
# 마이크가 필요하지 않으며, 시스템 안정성을 검증할 수 있습니다.
#
# 사용법:
#   bash scripts/roleplay_text.sh [옵션]
#
# 옵션:
#   --iterations N       테스트 반복 횟수 (기본값: 1)
#   --verbose           상세 로깅 활성화
#   --server-only       서버만 시작 (테스트 미실행)
#
# 예시:
#   bash scripts/roleplay_text.sh
#   bash scripts/roleplay_text.sh --iterations 3
#   bash scripts/roleplay_text.sh --verbose
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

# 커맨드라인 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
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

# 텍스트 기반 테스트
run_test() {
    local iteration=$1

    print_header "텍스트 기반 롤플레잉 (${iteration}/${ITERATIONS})"

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

async def test():
    FASTAPI_URL = "http://localhost:8082"
    WS_URL_BASE = "ws://localhost:8082/ws/roleplaying"

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
        logger.info(f"")
        logger.info(f"🤖 AI (Turn 1): {data.get('text')[:100]}...")
        logger.info(f"")

        # 4. 텍스트 메시지 전송 및 AI 응답 (3턴)
        user_messages = [
            "I think the root cause is in the request filtering logic when finance advanced filters are enabled.",
            "Yes, I believe the condition check fails because it's not properly nested in the filter parameters.",
            "We should add more comprehensive validation for the filter parameters before processing.",
        ]

        for turn, user_text in enumerate(user_messages, 1):
            logger.info(f"👤 User (Turn {turn+1}): {user_text[:80]}...")

            user_msg = {
                "type": "USER_TEXT",
                "text": user_text
            }
            await ws.send(json.dumps(user_msg))

            # AI 응답 수신
            ai_received = False
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                msg_data = json.loads(response)
                msg_type = msg_data.get("type")

                if msg_type == "AI_TEXT":
                    logger.info(f"")
                    logger.info(f"🤖 AI (Turn {turn+2}): {msg_data.get('text')[:100]}...")
                    logger.info(f"")
                    ai_received = True
                    break

            if not ai_received:
                logger.error("❌ AI 응답을 받지 못했습니다")
                return False

        # 5. 세션 종료
        logger.info("🛑 END_SESSION 메시지 전송...")
        await ws.send(json.dumps({"type": "END_SESSION"}))

        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        if json.loads(response).get("type") == "SESSION_ENDED":
            logger.info("✅ 세션 종료됨")

        await ws.close()
        logger.info("=" * 50)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 50)
        return True

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False

result = asyncio.run(test())
sys.exit(0 if result else 1)
EOF

    local verbose_arg=$([ "$VERBOSE" = true ] && echo "verbose" || echo "normal")
    return $?
}

main() {
    parse_args "$@"

    print_header "텍스트 기반 롤플레잉 테스트"
    echo "구성:"
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
            print_error "$failed개 테스트 실패"
            exit 1
        fi
    else
        print_success "서버가 실행 중입니다"
        print_info "다른 터미널에서 테스트를 실행할 수 있습니다"
        wait
    fi
}

main "$@"
