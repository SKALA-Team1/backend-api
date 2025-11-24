# test_microphone.py
import asyncio
import json
import websockets
from uuid import uuid4

async def setup_test_session(session_id: str) -> str:
  """Redis에 테스트 세션을 생성합니다"""
  print(f"📝 테스트 세션 생성: {session_id}")

  try:
    import redis.asyncio as aioredis

    # Redis에 접속
    r = await aioredis.from_url("redis://localhost", decode_responses=True)

    # 세션 데이터 저장
    session_data = {
      "userId": 1,
      "scenarioId": 1,
      "status": "ACTIVE",
      "expiresAt": "2025-12-31T23:59:59Z"
    }

    # Redis에 저장 (key: session:{session_id})
    await r.setex(
      f"session:{session_id}",
      7200,  # 2시간 TTL
      json.dumps(session_data)
    )

    await r.close()
    print(f"✅ Redis 세션 생성 완료")
    return session_id

  except Exception as e:
    print(f"❌ Redis 연결 실패: {e}")
    print("💡 Redis가 실행 중인지 확인하세요: redis-cli ping")
    raise

async def test_with_microphone():
  """실제 마이크 입력으로 WebSocket 테스트"""

  session_id = str(uuid4())

  # Redis에 세션 생성
  await setup_test_session(session_id)

  # 포트 확인 (환경에 따라 8000 또는 8082)
  port = 8082
  uri = f"ws://localhost:{port}/ws/roleplaying/{session_id}"

  print(f"\n🎤 WebSocket 연결 시도: {uri}")

  async with websockets.connect(uri) as websocket:
      print("✅ 연결 성공!")

      # Step 1: INIT 메시지 전송
      init_msg = {
          "type": "INIT",
          "userId": 1,
          "subjectId": 1,
          "myRole": "Student",
          "aiRole": "Teacher",
          "fixedQuestions": [
              "How are you?",
              "What is your name?",
              "Where are you from?"
          ]
      }

      print("\n📤 INIT 메시지 전송...")
      await websocket.send(json.dumps(init_msg))

      # ACK 수신 (타임아웃: 3초)
      try:
          response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
          print(f"📥 응답: {response}")
      except asyncio.TimeoutError:
          print("❌ ACK 수신 타임아웃 (3초)")
          return

      # Step 2: AI 첫 질문 수신 (타임아웃: 3초)
      try:
          ai_question = await asyncio.wait_for(websocket.recv(), timeout=3.0)
          print(f"🤖 AI 질문: {ai_question}")
      except asyncio.TimeoutError:
          print("❌ AI 질문 수신 타임아웃 (3초)")
          return

      # Step 3: 마이크 입력 준비
      print("\n🎤 마이크를 통해 답변하세요 (5초 동안 녹음)...")
      print("(Ctrl+C로 언제든지 중단 가능)\n")

      try:
          # PyAudio로 마이크 입력 받기
          import pyaudio
          import wave

          CHUNK = 1024
          FORMAT = pyaudio.paInt16
          CHANNELS = 1
          RATE = 16000

          p = pyaudio.PyAudio()

          # 마이크 스트림 시작
          stream = p.open(
              format=FORMAT,
              channels=CHANNELS,
              rate=RATE,
              input=True,
              frames_per_buffer=CHUNK
          )

          print("🔴 녹음 시작...")

          # 5초 동안 녹음하며 전송
          frames = []
          for _ in range(0, int(RATE / CHUNK * 5)):
              data = stream.read(CHUNK)
              frames.append(data)

              # 오디오 청크를 WebSocket으로 전송 (바이너리)
              await websocket.send(data)
              print(f"📤 청크 전송: {len(data)} bytes")

          print("\n✋ 녹음 종료")

          # 발화 종료 신호
          print("📤 발화 종료 신호 전송...")
          utterance_end = {"type": "UTTERANCE_END"}
          await websocket.send(json.dumps(utterance_end))

          # STT 결과 수신 (타임아웃: 5초 - STT 처리 시간 포함)
          print("\n⏳ STT 결과 대기 중...")
          try:
              stt_result = await asyncio.wait_for(websocket.recv(), timeout=5.0)
              print(f"🎯 STT 결과: {stt_result}")
          except asyncio.TimeoutError:
              print("❌ STT 결과 수신 타임아웃 (5초)")
              return

          # AI 응답 수신 (타임아웃: 10초 - 모델 생성 시간 포함)
          # 첫 AI 응답: 3초 (모델 워밍업됨)
          # 콜드 스타트: 5초 (모델 로딩 + 생성)
          # 여유있게: 10초
          print("\n⏳ AI 응답 대기 중 (최대 10초)...")
          try:
              ai_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
              print(f"🤖 AI 응답: {ai_response}")
          except asyncio.TimeoutError:
              print("❌ AI 응답 수신 타임아웃 (10초)")
              return

          stream.stop_stream()
          stream.close()
          p.terminate()

      except ImportError:
          print("⚠️  PyAudio가 설치되지 않았습니다.")
          print("설치: pip install pyaudio")
          print("\n대신 텍스트로 테스트합니다...")

          # 텍스트 모드 테스트
          text_msg = {
              "type": "USER_TEXT",
              "text": "I am fine, thank you!"
          }
          await websocket.send(json.dumps(text_msg))

          response = await websocket.recv()
          print(f"📥 응답: {response}")

if __name__ == "__main__":
  asyncio.run(test_with_microphone())
