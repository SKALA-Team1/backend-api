#!/usr/bin/env python3

"""
음성 기반 롤플레잉 테스트 클라이언트 (마이크 불필요)

마이크 없이 더미 오디오로 음성 기반 롤플레잉을 테스트합니다.

사용법:
    python scripts/test_voice_client.py [옵션]

옵션:
    --fastapi-url       FastAPI 베이스 URL (기본값: http://localhost:8082)
    --user-id           사용자 ID (기본값: 1)
    --scenario-id       시나리오 ID (기본값: 1)
    --verbose           상세 로깅 활성화

예시:
    python scripts/test_voice_client.py
    python scripts/test_voice_client.py --user-id 2 --scenario-id 5 --verbose
"""

import asyncio
import json
import logging
import sys
import argparse
from typing import Optional, Dict, Any
import httpx
import websockets

# ============================================================================
# 설정
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# 음성 데이터 생성기 (마이크 대체)
# ============================================================================

class DummyAudioGenerator:
    """마이크 없이 더미 오디오 데이터를 생성합니다."""

    @staticmethod
    def generate_silence_chunk(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
        """
        무음 오디오 청크 생성 (PCM 16-bit)

        Args:
            duration_ms: 지속 시간 (밀리초)
            sample_rate: 샘플링 레이트 (Hz)

        Returns:
            PCM 바이너리 데이터
        """
        num_samples = int(sample_rate * duration_ms / 1000)
        # 16-bit PCM = 2 바이트 per sample
        # 무음 = 0x0000
        return b'\x00\x00' * num_samples

    @staticmethod
    def generate_tone_chunk(
        frequency: int = 440,
        duration_ms: int = 100,
        sample_rate: int = 16000,
        amplitude: int = 1000
    ) -> bytes:
        """
        정현파 톤 생성 (PCM 16-bit)

        Args:
            frequency: 주파수 (Hz)
            duration_ms: 지속 시간 (밀리초)
            sample_rate: 샘플링 레이트 (Hz)
            amplitude: 진폭

        Returns:
            PCM 바이너리 데이터
        """
        import math
        import struct

        num_samples = int(sample_rate * duration_ms / 1000)
        data = []

        for i in range(num_samples):
            # 정현파 생성
            sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
            # 16-bit 정수로 변환
            sample = int(sample)
            data.append(struct.pack('<h', sample))

        return b''.join(data)

    @staticmethod
    def generate_speech_like_audio(duration_ms: int = 500) -> bytes:
        """
        음성처럼 들리는 오디오 생성 (다양한 주파수)

        Args:
            duration_ms: 지속 시간 (밀리초)

        Returns:
            PCM 바이너리 데이터
        """
        chunks = []

        # 저음역대 (100-300 Hz) - 자음/자모음
        chunks.append(DummyAudioGenerator.generate_tone_chunk(
            frequency=150,
            duration_ms=duration_ms // 3,
            amplitude=800
        ))

        # 중음역대 (300-1000 Hz) - 모음
        chunks.append(DummyAudioGenerator.generate_tone_chunk(
            frequency=500,
            duration_ms=duration_ms // 3,
            amplitude=1000
        ))

        # 고음역대 (1000-4000 Hz) - 자음
        chunks.append(DummyAudioGenerator.generate_tone_chunk(
            frequency=2000,
            duration_ms=duration_ms // 3,
            amplitude=600
        ))

        return b''.join(chunks)


# ============================================================================
# WebSocket 클라이언트
# ============================================================================

class VoiceRoleplayClient:
    """음성 기반 롤플레잉 WebSocket 클라이언트"""

    def __init__(
        self,
        fastapi_url: str = "http://localhost:8082",
        user_id: int = 1,
        scenario_id: int = 1,
        verbose: bool = False
    ):
        """
        Args:
            fastapi_url: FastAPI 베이스 URL
            user_id: 사용자 ID
            scenario_id: 시나리오 ID
            verbose: 상세 로깅 활성화
        """
        self.fastapi_url = fastapi_url.rstrip('/')
        self.user_id = user_id
        self.scenario_id = scenario_id
        self.verbose = verbose

        if verbose:
            logger.setLevel(logging.DEBUG)

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.ws_url: Optional[str] = None
        self.scenario: Optional[Dict[str, Any]] = None

    async def create_session(self) -> bool:
        """REST API로 세션 생성"""
        logger.info(f"세션 생성 중... (user_id={self.user_id}, scenario_id={self.scenario_id})")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.fastapi_url}/roleplaying/sessions",
                    json={
                        "userId": self.user_id,
                        "scenarioId": self.scenario_id
                    },
                    timeout=10.0
                )
                response.raise_for_status()

            data = response.json()
            self.session_id = data.get("session_id")
            self.ws_url = data.get("ws_url")
            self.scenario = data.get("scenario")

            logger.info(f"✅ 세션 생성됨: {self.session_id}")
            logger.debug(f"   WebSocket URL: {self.ws_url}")
            logger.debug(f"   시나리오: {self.scenario.get('title')}")

            return True

        except Exception as e:
            logger.error(f"❌ 세션 생성 실패: {e}")
            return False

    async def connect(self) -> bool:
        """WebSocket 연결"""
        if not self.ws_url:
            logger.error("WebSocket URL이 없습니다")
            return False

        logger.info(f"WebSocket 연결 중... ({self.ws_url})")

        try:
            self.websocket = await websockets.connect(self.ws_url)
            logger.info("✅ WebSocket 연결됨")
            return True

        except Exception as e:
            logger.error(f"❌ WebSocket 연결 실패: {e}")
            return False

    async def send_init_message(self) -> bool:
        """INIT 메시지 전송"""
        if not self.websocket or not self.scenario:
            return False

        init_msg = {
            "type": "INIT",
            "userId": self.user_id,
            "subjectId": self.scenario.get("subjectId"),
            "myRole": self.scenario.get("myRole"),
            "aiRole": self.scenario.get("aiRole"),
            "fixedQuestions": self.scenario.get("fixedQuestions", [])
        }

        logger.info("📤 INIT 메시지 전송")
        logger.debug(f"   {init_msg}")

        try:
            await self.websocket.send(json.dumps(init_msg))

            # ACK 수신
            ack = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            logger.debug(f"📥 ACK 수신: {ack}")

            # 첫 AI 질문 수신
            response = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "AI_TEXT":
                ai_text = data.get("text")
                logger.info(f"🤖 AI (Turn 1): {ai_text}")
                return True
            else:
                logger.error(f"예상치 못한 메시지: {data}")
                return False

        except asyncio.TimeoutError:
            logger.error("❌ INIT 응답 타임아웃")
            return False
        except Exception as e:
            logger.error(f"❌ INIT 처리 실패: {e}")
            return False

    async def send_audio_chunks(self, num_chunks: int = 3) -> bool:
        """오디오 청크 전송 (마이크 대체)"""
        if not self.websocket:
            return False

        logger.info(f"📤 오디오 청크 전송 ({num_chunks}개)")

        try:
            for i in range(num_chunks):
                # 더미 음성 오디오 생성
                audio_chunk = DummyAudioGenerator.generate_speech_like_audio(
                    duration_ms=100
                )

                await self.websocket.send(audio_chunk)
                logger.debug(f"   청크 {i+1}/{num_chunks} 전송 ({len(audio_chunk)} bytes)")
                await asyncio.sleep(0.1)  # 송신 간격

            logger.info("✅ 오디오 청크 전송 완료")
            return True

        except Exception as e:
            logger.error(f"❌ 오디오 청크 전송 실패: {e}")
            return False

    async def send_utterance_end(self) -> bool:
        """UTTERANCE_END 메시지 전송 및 STT/AI 응답 수신"""
        if not self.websocket:
            return False

        logger.info("📤 UTTERANCE_END 메시지 전송")

        try:
            msg = {"type": "UTTERANCE_END"}
            await self.websocket.send(json.dumps(msg))

            # 메시지 수신 루프 (STT → UTTERANCE_SAVED → AI_TYPING → AI_TEXT 순서)
            ai_text = None
            is_fixed = False
            max_iterations = 10
            iteration = 0

            try:
                while iteration < max_iterations:
                    iteration += 1
                    response = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=5.0
                    )
                    data = json.loads(response)
                    msg_type = data.get("type")

                    if msg_type == "STT_PARTIAL":
                        logger.info(f"   STT (부분): {data.get('text')}")

                    elif msg_type == "STT_FINAL":
                        stt_text = data.get("text", "(empty)")
                        logger.info(f"✅ STT (최종): {stt_text}")

                    elif msg_type == "UTTERANCE_SAVED":
                        logger.debug(f"   발화 저장됨 (index={data.get('index')})")

                    elif msg_type == "AI_TYPING":
                        logger.info("   💭 AI 생각 중...")

                    elif msg_type == "AI_TEXT":
                        ai_text = data.get("text")
                        is_fixed = data.get("is_fixed_question", False)
                        logger.info(f"🤖 AI 응답 ({'고정' if is_fixed else '동적'}): {ai_text}")
                        return True

                    elif msg_type == "ERROR":
                        logger.error(f"   에러: {data.get('message')}")
                        # 에러가 나도 AI 응답이 나올 수 있으므로 계속 진행
                        pass

                    else:
                        logger.debug(f"   기타 메시지: {msg_type}")

            except asyncio.TimeoutError:
                logger.error("❌ AI 응답 수신 타임아웃")
                return False

            # AI_TEXT를 받지 못했으면 실패
            if ai_text is None:
                logger.error("❌ AI 응답을 받지 못했습니다")
                return False

            return True

        except asyncio.TimeoutError:
            logger.error("❌ 응답 타임아웃")
            return False
        except Exception as e:
            logger.error(f"❌ UTTERANCE_END 처리 실패: {e}")
            return False

    async def send_end_session(self) -> bool:
        """END_SESSION 메시지 전송"""
        if not self.websocket:
            return False

        logger.info("📤 END_SESSION 메시지 전송")

        try:
            msg = {"type": "END_SESSION"}
            await self.websocket.send(json.dumps(msg))

            # SESSION_ENDED 응답 수신
            response = await asyncio.wait_for(
                self.websocket.recv(),
                timeout=5.0
            )
            data = json.loads(response)

            if data.get("type") == "SESSION_ENDED":
                logger.info(f"✅ 세션 종료됨 (reason: {data.get('reason')})")
                return True
            else:
                logger.warning(f"예상치 못한 메시지: {data}")
                return True

        except asyncio.TimeoutError:
            logger.warning("SESSION_ENDED 응답 타임아웃")
            return True
        except Exception as e:
            logger.error(f"❌ END_SESSION 처리 실패: {e}")
            return True

    async def close(self):
        """WebSocket 연결 종료"""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket 연결 종료")

    async def run(self) -> bool:
        """전체 테스트 실행"""
        logger.info("=" * 50)
        logger.info("음성 기반 롤플레잉 테스트 시작")
        logger.info("=" * 50)

        try:
            # 1. 세션 생성
            if not await self.create_session():
                return False

            # 2. WebSocket 연결
            if not await self.connect():
                return False

            # 3. INIT 메시지
            if not await self.send_init_message():
                return False

            # 4. 오디오 청크 전송
            if not await self.send_audio_chunks(num_chunks=3):
                return False

            # 5. UTTERANCE_END 및 STT/AI 응답
            if not await self.send_utterance_end():
                return False

            # 6. 세션 종료
            if not await self.send_end_session():
                return False

            logger.info("=" * 50)
            logger.info("✅ 모든 테스트 통과!")
            logger.info("=" * 50)
            return True

        except Exception as e:
            logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
            return False

        finally:
            await self.close()


# ============================================================================
# 메인 실행
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="음성 기반 롤플레잉 테스트 클라이언트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/test_voice_client.py
  python scripts/test_voice_client.py --fastapi-url http://localhost:8082
  python scripts/test_voice_client.py --user-id 2 --scenario-id 5 --verbose
        """
    )

    parser.add_argument(
        "--fastapi-url",
        default="http://localhost:8082",
        help="FastAPI 베이스 URL (기본값: http://localhost:8082)"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="사용자 ID (기본값: 1)"
    )
    parser.add_argument(
        "--scenario-id",
        type=int,
        default=1,
        help="시나리오 ID (기본값: 1)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 로깅 활성화"
    )

    args = parser.parse_args()

    # 클라이언트 생성 및 실행
    client = VoiceRoleplayClient(
        fastapi_url=args.fastapi_url,
        user_id=args.user_id,
        scenario_id=args.scenario_id,
        verbose=args.verbose
    )

    success = await client.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())