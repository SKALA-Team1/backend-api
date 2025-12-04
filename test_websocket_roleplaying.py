"""
WebSocket 롤플레잉 대화 자동 테스트
INIT → USER_TEXT → AI 응답 확인
"""
import asyncio
import websockets
import json
import sys

async def test_roleplaying():
    # 세션 정보 로드
    with open("/Users/younashin/.skala-session-info.json", "r") as f:
        session_info = json.load(f)

    ws_url = session_info["ws_url"]
    session_id = session_info["session_id"]

    print(f"🔗 WebSocket 연결 중...")
    print(f"   URL: {ws_url}")
    print(f"   세션 ID: {session_id}")
    print()

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket 연결 성공!")
            print()

            # 1. INIT 메시지 전송
            init_message = {
                "type": "INIT",
                "userId": 1,
                "subjectId": 1,
                "myRole": "Backend Engineer",
                "aiRole": "Project Manager",
                "fixedQuestions": [
                    "Can you summarize the root cause of the /reports endpoint error after enabling finance advanced filters?",
                    "How do you plan to implement a temporary workaround for the Redis connection pool issues, and what's the expected impact on system performance?",
                    "What are the next steps to resolve the issue, and when can we expect a fix or further updates from your team?"
                ]
            }

            print("📤 INIT 메시지 전송 중...")
            await websocket.send(json.dumps(init_message))

            # INIT 응답 받기
            response = await websocket.recv()
            print(f"📥 INIT 응답: {response}")
            print()

            # 2. 사용자 메시지 전송
            user_message = {
                "type": "USER_TEXT",
                "text": "Hello, I'm here to discuss the recent deployment issue with the /reports endpoint."
            }

            print("📤 USER_TEXT 메시지 전송 중...")
            print(f"   내용: {user_message['text']}")
            await websocket.send(json.dumps(user_message))

            # AI 응답 기다리기 (최대 30초)
            print("⏳ AI 응답 대기 중 (최대 30초)...")
            try:
                ai_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                print(f"📥 AI 응답:")
                response_data = json.loads(ai_response)
                print(f"   타입: {response_data.get('type')}")
                if response_data.get('type') == 'AI_TEXT':
                    print(f"   내용: {response_data.get('text', 'N/A')[:200]}...")
                else:
                    print(f"   전체: {ai_response}")
                print()

                # 추가 응답 확인 (UTTERANCE_SAVED 등)
                print("⏳ 추가 응답 확인 중...")
                try:
                    while True:
                        extra_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        print(f"📥 추가 응답: {extra_response}")
                except asyncio.TimeoutError:
                    print("✅ 더 이상 응답 없음")

            except asyncio.TimeoutError:
                print("⚠️  30초 내에 AI 응답을 받지 못했습니다")

            print()
            print("🎉 WebSocket 테스트 완료!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_roleplaying())
