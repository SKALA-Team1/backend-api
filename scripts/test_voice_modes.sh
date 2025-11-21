#!/bin/bash

##############################################################################
# 다양한 테스트 모드를 제공하는 음성 테스트 스크립트
#
# 사용법:
#   bash scripts/test_voice_modes.sh [모드]
#
# 모드:
#   dummy       더미 오디오로 테스트 (권장 - 안정적)
#   mic         실제 마이크로 테스트 (10초 녹음 - 기본값)
#   mic-long    실제 마이크로 테스트 (5초 녹음 - 짧은 버전)
#   text        텍스트 기반 테스트 (마이크 없이)
#   interactive 대화형 모드 (각 단계마다 엔터 필요)
#   multi       3회 반복 테스트
#   demo        데모 시나리오 (여러 턴)
#
# 예시:
#   bash scripts/test_voice_modes.sh dummy              # 더미 오디오
#   bash scripts/test_voice_modes.sh mic                # 마이크 3초
#   bash scripts/test_voice_modes.sh interactive --mic  # 대화형 + 마이크
#   bash scripts/test_voice_modes.sh demo               # 데모 (3턴)
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
MODE="${1:-dummy}"
FASTAPI_URL="http://localhost:8082"

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

# 서버 실행 확인
check_server() {
    if ! curl -s "$FASTAPI_URL/docs" > /dev/null 2>&1; then
        print_error "서버가 실행 중이지 않습니다!"
        echo ""
        echo "다음 명령어로 서버를 시작하세요:"
        echo "  bash scripts/start_server.sh"
        echo ""
        exit 1
    fi
    print_success "서버가 준비되었습니다"
}

# 더미 오디오 테스트
test_dummy() {
    print_header "더미 오디오 테스트 모드"
    print_info "실제 마이크 없이 더미 음성 데이터로 테스트합니다"
    print_info "안정적이고 재현 가능한 테스트에 이상적입니다"
    echo ""

    cd "$BACKEND_DIR"
    python scripts/test_voice_client.py \
        --fastapi-url "$FASTAPI_URL" \
        --user-id 1 \
        --scenario-id 1
}

# 마이크 테스트 (10초)
test_mic() {
    print_header "실제 마이크 테스트 (10초 녹음)"
    print_warning "주의사항:"
    echo "  • 녹음이 시작되면 마이크에 대고 명확하게 말씀해주세요"
    echo "  • 여유있게 말씀해주세요 (기본 10초 녹음)"
    echo "  • 예: \"The answer is in the logs\" 같은 간단한 문장"
    echo ""
    read -p "준비되셨으면 엔터를 눌러주세요: "
    echo ""

    cd "$BACKEND_DIR"
    python scripts/test_voice_client.py \
        --fastapi-url "$FASTAPI_URL" \
        --user-id 1 \
        --scenario-id 1 \
        --use-mic \
        --verbose
}

# 마이크 테스트 (5초)
test_mic_long() {
    print_header "실제 마이크 테스트 (5초 녹음)"
    print_warning "더 긴 시간 녹음하기"
    print_info "마이크에 대고 더 많이 말씀할 수 있습니다"
    echo ""
    read -p "준비되셨으면 엔터를 눌러주세요: "
    echo ""

    cd "$BACKEND_DIR"
    python scripts/test_voice_client.py \
        --fastapi-url "$FASTAPI_URL" \
        --user-id 1 \
        --scenario-id 1 \
        --use-mic \
        --record-duration 5 \
        --verbose
}

# 텍스트 기반 테스트 (USER_TEXT 메시지 사용)
test_text() {
    print_header "텍스트 기반 테스트 모드"
    print_info "STT 없이 텍스트로 직접 대화합니다"
    print_info "마이크가 필요하지 않으며, 음성 인식 오류가 없습니다"
    echo ""

    cd "$BACKEND_DIR"

    # 파이썬으로 텍스트 기반 테스트 클라이언트 실행
    python3 << 'EOF'
import asyncio
import json
import logging
import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def test_text_mode():
    FASTAPI_URL = "http://localhost:8082"
    WS_URL_BASE = "ws://localhost:8082/ws/roleplaying"

    # 1. 세션 생성
    logger.info("세션 생성 중...")
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
    logger.info(f"WebSocket 연결 중...")
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
    logger.info(f"🤖 AI: {data.get('text')[:80]}...")

    # 4. 텍스트 메시지 전송 (1턴)
    logger.info("📝 사용자 답변 전송...")
    user_text_msg = {
        "type": "USER_TEXT",
        "text": "I think the issue is related to incorrect field filtering in the request parameters."
    }
    await ws.send(json.dumps(user_text_msg))

    # 응답 수신
    while True:
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(response)
        msg_type = data.get("type")

        if msg_type == "STT_FINAL":
            logger.info(f"✅ STT: {data.get('text')}")
        elif msg_type == "UTTERANCE_SAVED":
            logger.info(f"💾 발화 저장됨 (index={data.get('index')})")
        elif msg_type == "AI_TEXT":
            logger.info(f"🤖 AI: {data.get('text')[:80]}...")
            break

    # 5. 세션 종료
    logger.info("📤 END_SESSION 메시지 전송...")
    await ws.send(json.dumps({"type": "END_SESSION"}))

    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
    data = json.loads(response)
    if data.get("type") == "SESSION_ENDED":
        logger.info(f"✅ 세션 종료됨")

    await ws.close()
    logger.info("=" * 50)
    logger.info("✅ 테스트 완료!")
    logger.info("=" * 50)

asyncio.run(test_text_mode())
EOF
}

# 대화형 모드
test_interactive() {
    print_header "대화형 모드"
    print_info "각 단계마다 엔터 키를 눌러 다음 단계로 진행합니다"
    print_info "'q' + 엔터로 언제든 중단 가능합니다"
    echo ""

    local extra_args=""
    if [ "$2" = "--mic" ]; then
        extra_args="--use-mic --record-duration 3"
        print_info "모드: 실제 마이크"
    else
        print_info "모드: 더미 오디오"
    fi

    cd "$BACKEND_DIR"
    bash scripts/test_voice_flow.sh --interactive $extra_args
}

# 3회 반복 테스트
test_multi() {
    print_header "3회 반복 테스트"
    print_info "더미 오디오로 3번 반복 테스트합니다"
    echo ""

    cd "$BACKEND_DIR"
    bash scripts/test_voice_flow.sh --iterations 3
}

# 데모 시나리오 (다중 턴)
test_demo() {
    print_header "데모 시나리오 (3턴 대화)"
    print_info "더미 오디오로 전체 3턴 대화를 시연합니다"
    echo ""

    cd "$BACKEND_DIR"

    # 파이썬으로 데모 실행
    python3 << 'EOF'
import asyncio
import json
import logging
import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

async def demo():
    FASTAPI_URL = "http://localhost:8082"
    WS_URL_BASE = "ws://localhost:8082/ws/roleplaying"

    # 1. 세션 생성
    logger.info("🎬 데모 시작 - 음성 기반 롤플레잉")
    logger.info("=" * 50)
    logger.info("1️⃣  세션 생성 중...")

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
    logger.info("2️⃣  WebSocket 연결...")
    ws = await websockets.connect(f"{WS_URL_BASE}/{session_id}")
    logger.info("✅ 연결됨")

    # 3. INIT 메시지
    logger.info("3️⃣  초기화 중...")
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
    await ws.recv()  # ACK
    ai_q1 = await ws.recv()
    data = json.loads(ai_q1)
    logger.info(f"")
    logger.info(f"🤖 AI (Turn 1): {data.get('text')}")
    logger.info(f"")

    # 4. 각 턴마다 사용자 답변 + AI 응답
    user_responses = [
        "The root cause appears to be in the request filtering logic where the finance filter condition is applied incorrectly.",
        "Yes, specifically when the advanced filters are enabled, the condition check fails because the condition is not properly nested.",
        "I would recommend adding more comprehensive validation for the filter parameters before processing the request.",
    ]

    for turn, user_text in enumerate(user_responses, 1):
        logger.info(f"📝 User (Turn {turn+1}): {user_text}")

        # USER_TEXT 메시지 전송
        msg = {"type": "USER_TEXT", "text": user_text}
        await ws.send(json.dumps(msg))

        # 응답 수신
        while True:
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)
            msg_type = data.get("type")

            if msg_type == "AI_TEXT":
                logger.info(f"")
                logger.info(f"🤖 AI (Turn {turn+2}): {data.get('text')}")
                logger.info(f"")
                break

        if turn < len(user_responses):
            await asyncio.sleep(1)

    # 5. 세션 종료
    logger.info("4️⃣  세션 종료...")
    await ws.send(json.dumps({"type": "END_SESSION"}))

    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
    if json.loads(response).get("type") == "SESSION_ENDED":
        logger.info("✅ 세션 종료됨")

    await ws.close()
    logger.info("=" * 50)
    logger.info("✅ 데모 완료!")
    logger.info("=" * 50)

asyncio.run(demo())
EOF
}

# 헬프
show_help() {
    echo "음성 테스트 모드"
    echo ""
    echo "사용법: bash scripts/test_voice_modes.sh [모드]"
    echo ""
    echo "모드:"
    echo "  dummy       더미 오디오 테스트 (권장)"
    echo "  mic         마이크 테스트 (10초 - 기본값)"
    echo "  mic-long    마이크 테스트 (5초 - 짧은 버전)"
    echo "  text        텍스트 기반 테스트"
    echo "  interactive 대화형 모드"
    echo "  multi       3회 반복 테스트"
    echo "  demo        데모 시나리오"
    echo ""
    exit 0
}

# 메인
case "$MODE" in
    dummy)
        check_server
        test_dummy
        ;;
    mic)
        check_server
        test_mic
        ;;
    mic-long)
        check_server
        test_mic_long
        ;;
    text)
        check_server
        test_text
        ;;
    interactive)
        check_server
        test_interactive "$2"
        ;;
    multi)
        check_server
        test_multi
        ;;
    demo)
        check_server
        test_demo
        ;;
    --help|-h)
        show_help
        ;;
    *)
        print_error "알 수 없는 모드: $MODE"
        echo ""
        show_help
        ;;
esac