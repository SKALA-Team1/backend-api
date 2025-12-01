"""
WebSocket 클라이언트 테스트 스크립트
"""
import asyncio
import json
import uuid
from datetime import datetime
import websockets

# ============================================
# 테스트 설정
# ============================================

WS_URL = "ws://localhost:8082/ws/roleplaying"
SESSION_ID = str(uuid.uuid4())

# 테스트용 세션 데이터 (Spring 1에서 받는다고 가정)
INIT_MESSAGE = {
    "type": "INIT",
    "subjectId": 1,
    "myRole": "Student",
    "aiRole": "English Teacher",
    "fixedQuestions": [
        "Hello! How are you today?",
        "What is your favorite hobby?",
        "Where are you from?"
    ]
}

TEXT_MESSAGES = [
    "I am fine, thank you!",
    "I like playing tennis.",
    "I am from Korea."
]

# ============================================
# WebSocket 테스트 함수
# ============================================

async def test_text_based_roleplaying():
    """텍스트 기반 롤플레잉 테스트"""
    print(f"\n{'='*60}")
    print("🧪 텍스트 기반 롤플레잉 테스트")
    print(f"{'='*60}")
    print(f"📍 WebSocket URL: {WS_URL}/{SESSION_ID}")
    print(f"📍 세션 ID: {SESSION_ID}\n")

    try:
        async with websockets.connect(f"{WS_URL}/{SESSION_ID}") as websocket:
            # Step 1: INIT 메시지 전송
            print("📤 [1] INIT 메시지 전송")
            await websocket.send(json.dumps(INIT_MESSAGE))
            print("✅ INIT 전송 완료\n")

            # Step 2: 응답 대기
            print("📥 응답 대기...\n")
            response_count = 0

            async for message in websocket:
                response = json.loads(message)
                response_type = response.get("type")

                print(f"[응답 {response_count + 1}] {response_type}")

                if response_type == "ACK":
                    print("✅ 세션 초기화 완료")

                elif response_type == "AI_TEXT_MESSAGE":
                    question = response.get("text", "")[:50]
                    print(f"   질문: {question}...")

                    # 사용자 답변 전송
                    if response_count < len(TEXT_MESSAGES):
                        user_text = TEXT_MESSAGES[response_count]
                        print(f"\n📤 사용자 답변 전송: '{user_text}'")

                        user_msg = {
                            "type": "USER_TEXT",
                            "text": user_text
                        }
                        await websocket.send(json.dumps(user_msg))
                        print("✅ 답변 전송 완료\n")

                elif response_type == "FEEDBACK":
                    print(f"   발음: {response.get('pronunciation_score')}")
                    print(f"   문법: {response.get('grammar_score')}")
                    print(f"   맥락: {response.get('relevance_score')}")
                    print(f"   종합: {response.get('overall_score')}")

                elif response_type == "FEEDBACK_STREAMING":
                    chunk = response.get("chunk", "")[:100]
                    print(f"   피드백: {chunk}...")

                elif response_type == "RETRY_REQUIRED":
                    print(f"   재시도 필요: {response.get('reason')}")
                    print(f"   {response.get('retry_count')}/{response.get('max_retries')}")

                elif response_type == "UTTERANCE_SAVED":
                    print(f"   저장됨: #{response.get('index')}")

                elif response_type == "SESSION_ENDED":
                    print(f"✅ 세션 종료: {response.get('reason')}")
                    break

                elif response_type == "ERROR":
                    print(f"❌ 에러: {response.get('message')}")

                response_count += 1

                if response_count > 20:  # 무한 루프 방지
                    print("\n⚠️  응답 제한 초과 (테스트 종료)")
                    break

        print(f"\n✅ 테스트 완료! 총 {response_count}개 응답 수신")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        print(f"\n💡 확인사항:")
        print(f"   1. FastAPI 서버 실행 중인지 확인")
        print(f"      python -m uvicorn app.main:app --reload --port 8082")
        print(f"   2. Redis 실행 중인지 확인")
        print(f"      redis-cli ping")
        print(f"   3. Ollama 실행 중인지 확인")
        print(f"      curl http://localhost:11434/api/tags")


# ============================================
# 메인
# ============================================

if __name__ == "__main__":
    print("🚀 WebSocket 피드백 시스템 테스트 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        asyncio.run(test_text_based_roleplaying())
    except KeyboardInterrupt:
        print("\n⚠️  테스트 중단됨")
