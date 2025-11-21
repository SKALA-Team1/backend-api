"""
WebSocket 실시간 롤플레잉 테스트 클라이언트

실행 방법:
    python scripts/test_websocket.py

테스트 시나리오:
    1. WebSocket 연결
    2. INIT 메시지 전송
    3. 더미 오디오 청크 전송
    4. UTTERANCE_END 메시지 전송
    5. AI 응답 수신
    6. END_SESSION 메시지 전송
"""

import asyncio
import json
import websockets
import os

# 설정
WS_URL = "ws://localhost:8000/ws/roleplaying/test-session-123"


async def test_websocket():
    """WebSocket 연결 및 테스트"""

    print("🚀 WebSocket 테스트 시작\n")
    print(f"📡 연결 URL: {WS_URL}\n")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket 연결 성공!\n")

            # ========================================
            # Step 1: INIT 메시지 전송
            # ========================================
            print("📤 [1/5] INIT 메시지 전송...")
            init_message = {
                "type": "INIT",
                "userId": 1,
                "subjectId": 123,
                "myRole": "Software Engineer",
                "aiRole": "Tech Lead",
                "fixedQuestions": [
                    "Can you introduce yourself and your current project?",
                    "What technical challenges are you facing?",
                    "What are your next steps?"
                ]
            }
            await websocket.send(json.dumps(init_message))

            # ACK 수신
            response = await websocket.recv()
            print(f"📥 응답: {response}\n")

            # 첫 AI 질문 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"🤖 AI 질문 (턴 1): {data.get('text')}\n")

            # ========================================
            # Step 2: 더미 오디오 청크 전송
            # ========================================
            print("📤 [2/5] 오디오 청크 전송 (더미 데이터)...")

            # 더미 오디오 데이터 생성 (1KB)
            dummy_audio = b'\x00' * 1024

            # 3개의 청크 전송 (시뮬레이션)
            for i in range(3):
                await websocket.send(dummy_audio)
                print(f"   청크 {i+1}/3 전송 완료")

            print()

            # ========================================
            # Step 3: UTTERANCE_END 메시지 전송
            # ========================================
            print("📤 [3/5] UTTERANCE_END 메시지 전송...")
            utterance_end = {
                "type": "UTTERANCE_END"
            }
            await websocket.send(json.dumps(utterance_end))

            # STT 결과 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 STT 결과: {data}\n")

            # UTTERANCE_SAVED 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 발화 저장 완료: {data}\n")

            # AI_TYPING 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 AI 응답 생성 중: {data.get('type')}\n")

            # AI 응답 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"🤖 AI 응답 (턴 2): {data.get('text')}\n")

            # ========================================
            # Step 4: 추가 대화 (선택)
            # ========================================
            print("📤 [4/5] 추가 대화 테스트...")

            # 오디오 전송
            for i in range(2):
                await websocket.send(dummy_audio)

            # UTTERANCE_END
            await websocket.send(json.dumps(utterance_end))

            # 응답 수신 (여러 개)
            for _ in range(4):  # STT_FINAL, UTTERANCE_SAVED, AI_TYPING, AI_TEXT
                response = await websocket.recv()
                data = json.loads(response)
                msg_type = data.get('type')

                if msg_type == 'AI_TEXT':
                    print(f"🤖 AI 응답 (턴 3): {data.get('text')}\n")
                else:
                    print(f"📥 {msg_type}")

            print()

            # ========================================
            # Step 5: END_SESSION 메시지 전송
            # ========================================
            print("📤 [5/5] END_SESSION 메시지 전송...")
            end_session = {
                "type": "END_SESSION"
            }
            await websocket.send(json.dumps(end_session))

            # SESSION_ENDED 수신
            response = await websocket.recv()
            data = json.loads(response)
            print(f"📥 세션 종료: {data}\n")

            print("✅ 테스트 완료!")

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket 연결 종료: {e}")
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket 에러: {e}")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # asyncio 실행
    asyncio.run(test_websocket())