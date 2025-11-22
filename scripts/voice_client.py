#!/usr/bin/env python3
"""
음성 기반 롤플레이 클라이언트
=============================

역할:
- WebSocket을 통한 음성 대화 처리
- 마이크 입력 및 오디오 변환
- STT 결과 및 AI 응답 처리
"""

import asyncio
import json
import logging
import httpx
import websockets
import sys
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
from pathlib import Path
import signal
from typing import Tuple, Optional

# 색상
CYAN = '\033[0;36m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'


class VoiceConfig:
    """음성 대화 설정"""

    def __init__(self, fastapi_url: str, record_duration: int, verbose: bool):
        self.fastapi_url = fastapi_url
        self.ws_url_base = f"{fastapi_url.replace('http', 'ws')}/ws/roleplaying"
        self.record_duration = record_duration
        self.verbose = verbose
        self.sample_rate = 16000

        # 로깅 설정
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)


class MicrophoneController:
    """마이크 입력 제어 (스페이스바 토글)"""

    def __init__(self, sample_rate: int, logger: logging.Logger):
        self.sample_rate = sample_rate
        self.logger = logger
        self.recording = False
        self.audio_data = []

    def start_recording(self) -> None:
        """마이크 활성화"""
        self.recording = True
        self.audio_data = []
        print(
            f"\n{RED}🔴 RECORDING... (스페이스바를 다시 눌러서 종료){NC}\n",
            end="",
            flush=True
        )

    def stop_recording(self) -> None:
        """마이크 비활성화"""
        self.recording = False
        print(f"\n{YELLOW}⏹️  STOPPED{NC}\n", end="", flush=True)

    def record_on_spacebar(self) -> np.ndarray:
        """스페이스바 토글로 녹음 제어"""
        try:
            import pynput
            from pynput.keyboard import Listener, Key
            import time

            self.logger.info("🎤 마이크 준비 완료")
            print(f"{BLUE}스페이스바를 누르면 녹음이 시작/중단됩니다{NC}")
            print(f"{YELLOW}(토글 방식: 1번째 누르면 활성화, 2번째 누르면 비활성화){NC}\n")

            space_pressed = False

            def on_press(key):
                nonlocal space_pressed
                try:
                    if key == Key.space and not space_pressed:
                        space_pressed = True
                        if not self.recording:
                            self.start_recording()
                        else:
                            self.stop_recording()
                except AttributeError:
                    pass

            def on_release(key):
                nonlocal space_pressed
                try:
                    if key == Key.space:
                        space_pressed = False
                except AttributeError:
                    pass

            # 키 리스너 시작
            listener = Listener(on_press=on_press, on_release=on_release)
            listener.start()

            # 오디오 녹음 시작
            def audio_callback(indata, frames, time_obj, status):
                if status:
                    self.logger.warning(f"Audio status: {status}")
                if self.recording:
                    self.audio_data.extend(indata[:, 0].copy())

            start_time = time.time()
            with sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.sample_rate // 10,  # 100ms
                callback=audio_callback
            ):
                # 녹음이 시작될 때까지 대기
                while not self.recording and time.time() - start_time < 30:
                    time.sleep(0.1)

                if not self.recording:
                    self.logger.error("스페이스바 입력이 감지되지 않았습니다")
                    listener.stop()
                    return np.array([], dtype=np.float32)

                # 녹음 진행 - 사용자가 스페이스바를 다시 누를 때까지 대기
                while True:
                    time.sleep(0.1)
                    if not self.recording:
                        break

            listener.stop()
            return np.array(self.audio_data, dtype=np.float32)

        except ImportError:
            print(
                f"{RED}❌ pynput 라이브러리가 필요합니다: pip install pynput{NC}"
            )
            raise
        except Exception as e:
            self.logger.error(f"오디오 입력 오류: {e}")
            raise


class VoiceRoleplayClient:
    """음성 기반 롤플레이 클라이언트"""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.logger = config.logger
        self.mic_controller = MicrophoneController(config.sample_rate, self.logger)
        self.current_turn = 1

    async def create_session(self) -> Tuple[str, dict]:
        """세션 생성"""
        self.logger.info("🔧 세션 생성 중...")

        session_id = "test-session-001"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.fastapi_url}/roleplaying/sessions",
                json={
                    "userId": 1,
                    "scenarioId": 1,
                    "sessionId": session_id
                },
                timeout=10.0
            )
            data = response.json()
            session_id = data.get("session_id")
            scenario = data.get("scenario")
            self.logger.info(f"✅ 세션 생성됨: {session_id}")

        return session_id, scenario

    async def connect_websocket(self, session_id: str):
        """WebSocket 연결"""
        self.logger.info("🔗 WebSocket 연결 중...")
        ws = await websockets.connect(f"{self.config.ws_url_base}/{session_id}")
        self.logger.info("✅ WebSocket 연결됨")
        return ws

    async def send_init_message(
        self,
        ws,
        scenario: dict
    ) -> None:
        """INIT 메시지 전송"""
        self.logger.info("📤 INIT 메시지 전송...")
        init_msg = {
            "type": "INIT",
            "userId": 1,
            "subjectId": scenario.get("subjectId"),
            "myRole": scenario.get("myRole"),
            "aiRole": scenario.get("aiRole"),
            "fixedQuestions": scenario.get("fixedQuestions", [])
        }
        await ws.send(json.dumps(init_msg))

    async def receive_first_question(self, ws) -> str:
        """첫 질문 수신"""
        ack = await ws.recv()
        ai_q1 = await ws.recv()
        data = json.loads(ai_q1)

        print()
        print(f"{CYAN}🤖 AI (Turn 0):{NC} {data.get('text')}")
        print()

        return data.get("text")

    async def send_audio(self, ws, audio: np.ndarray) -> None:
        """오디오를 청크로 나누어 전송"""
        chunk_size = self.config.sample_rate // 10  # 100ms
        sent_count = 0

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            if len(chunk) > 0:
                # float32를 int16으로 변환
                pcm_chunk = (chunk * 32767).astype(np.int16).tobytes()
                await ws.send(pcm_chunk)
                sent_count += 1
                # 첫 프레임 전송 후 최소 대기
                await asyncio.sleep(0.01)

            # 절반 정도 전송되었으면 UTTERANCE_END를 먼저 보내서 STT 시작 유도
            if sent_count == max(1, len(audio) // chunk_size // 2):
                self.logger.info("📤 UTTERANCE_END 메시지 전송 (조기)")
                await ws.send(json.dumps({"type": "UTTERANCE_END"}))
                break

        # 남은 청크가 있으면 계속 전송
        for i in range(sent_count * chunk_size, len(audio), chunk_size):
            chunk = audio[i:i+chunk_size]
            if len(chunk) > 0:
                pcm_chunk = (chunk * 32767).astype(np.int16).tobytes()
                await ws.send(pcm_chunk)
                await asyncio.sleep(0.01)

    async def receive_responses(
        self,
        ws,
        turn: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """STT + AI 응답 수신"""
        stt_result = None
        ai_response = None

        try:
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=20.0)

                # JSON 메시지인지 확인
                try:
                    msg_data = json.loads(response)
                    msg_type = msg_data.get("type")
                except (json.JSONDecodeError, AttributeError):
                    # 바이너리 데이터 (오디오)는 무시
                    continue

                if msg_type == "STT_FINAL":
                    stt_result = msg_data.get("text")
                    print(f"{GREEN}🗣️  You: {stt_result}{NC}")
                    print()
                elif msg_type == "AI_TEXT":
                    ai_response = msg_data.get("text")
                    print(f"{CYAN}🤖 AI (Turn {turn}): {ai_response}{NC}")
                    print()
                    break
                elif msg_type == "ERROR":
                    self.logger.warning(f"서버 에러: {msg_data.get('message')}")

        except asyncio.TimeoutError:
            self.logger.error("❌ AI 응답 타임아웃")

        return stt_result, ai_response

    async def process_turn(self, ws, turn: int) -> bool:
        """단일 턴 처리"""
        print(f"{BLUE}{'='*50}{NC}")
        print(f"{BLUE}Turn {turn}/10{NC}")
        print(f"{BLUE}{'='*50}{NC}")

        try:
            # 스페이스바로 녹음
            print(f"{YELLOW}✋ 스페이스바를 눌러서 마이크를 활성화하세요{NC}")
            audio = self.mic_controller.record_on_spacebar()

            if len(audio) == 0:
                print(f"{RED}⚠️  음성이 감지되지 않았습니다. 다시 시도하세요.{NC}\n")
                return True  # 재시도

            # 오디오를 PCM 16-bit로 변환
            self.logger.info(
                f"📤 오디오 전송 (길이: {len(audio)/self.config.sample_rate:.2f}초)"
            )

            # 오디오 전송과 응답 수신을 동시에 실행
            send_task = asyncio.create_task(self.send_audio(ws, audio))
            recv_task = asyncio.create_task(self.receive_responses(ws, turn))

            try:
                # 응답 수신만 대기 (오디오 전송은 백그라운드에서 계속 진행)
                stt_result, ai_response = await recv_task

                # AI 응답을 받은 후, 오디오 전송이 아직 진행 중이면 백그라운드에서 계속 진행
                if not send_task.done():
                    asyncio.create_task(send_task)

            except Exception as e:
                # 예외 발생 시 두 태스크 모두 취소
                send_task.cancel()
                recv_task.cancel()
                try:
                    await send_task
                except asyncio.CancelledError:
                    pass
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass
                raise

            if ai_response is None:
                self.logger.error("❌ AI 응답을 받지 못했습니다")
                return False

            return True

        except KeyboardInterrupt:
            self.logger.info("사용자가 대화를 종료했습니다")
            return False
        except Exception as e:
            self.logger.error(f"턴 {turn} 오류: {e}")
            return False

    async def run_voice_roleplay(self) -> bool:
        """음성 기반 대화형 롤플레이 실행"""
        try:
            # 1. 세션 생성
            session_id, scenario = await self.create_session()

            # 2. WebSocket 연결
            ws = await self.connect_websocket(session_id)

            # 3. INIT 메시지
            await self.send_init_message(ws, scenario)

            # 4. 첫 질문 수신
            await self.receive_first_question(ws)

            # 5. 대화 루프 (10턴)
            for turn in range(1, 11):
                self.current_turn = turn
                if not await self.process_turn(ws, turn):
                    break

            # 6. 세션 종료
            print(f"{BLUE}{'='*50}{NC}")
            self.logger.info("🛑 END_SESSION 메시지 전송...")
            await ws.send(json.dumps({"type": "END_SESSION"}))

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if json.loads(response).get("type") == "SESSION_ENDED":
                    self.logger.info("✅ 세션 종료됨")
            except asyncio.TimeoutError:
                pass

            await ws.close()
            print()
            print(f"{CYAN}{'='*50}{NC}")
            print(f"{CYAN}✅ 10턴 대화 완료!{NC}")
            print(f"{CYAN}{'='*50}{NC}")
            print()
            return True

        except Exception as e:
            self.logger.error(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """메인 진입점"""
    # 설정 읽기
    record_duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    verbose = sys.argv[2] == "verbose" if len(sys.argv) > 2 else False
    fastapi_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8082"

    # 설정 생성
    config = VoiceConfig(fastapi_url, record_duration, verbose)

    # 클라이언트 실행
    client = VoiceRoleplayClient(config)
    result = asyncio.run(client.run_voice_roleplay())

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()