"""
Spring 2 Client
===============
Spring 2 백엔드 서버와 통신하는 HTTP 클라이언트.

역할:
- 발화 저장 API 호출 (오디오 + STT 텍스트 → S3 + DB)
- 세션 완료 API 호출 (세션 상태 업데이트)
- 비동기 HTTP 통신 (httpx)

Spring 2 API:
- POST /internal/sessions/{session_id}/utterances: 발화 저장
- POST /internal/sessions/{session_id}/complete: 세션 완료

의존성:
- httpx (비동기 HTTP 클라이언트)
- app.config (Spring2 BASE_URL)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class Spring2Client:
    """
    Spring 2 백엔드 서버 HTTP 클라이언트

    FastAPI는 READ-ONLY 원칙을 따르므로, 모든 쓰기 작업은
    Spring 2를 통해 수행됩니다.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Spring2Client 초기화

        Args:
            base_url: Spring 2 서버 BASE URL (기본값: settings.SPRING2_BASE_URL)
        """
        self.base_url = base_url or settings.SPRING2_BASE_URL
        self.client: Optional[httpx.AsyncClient] = None
        logger.info(f"Spring2Client initialized: {self.base_url}")

    async def __aenter__(self):
        """async with 지원"""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async with 지원"""
        if self.client:
            await self.client.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        """httpx.AsyncClient 인스턴스 반환 (lazy init)"""
        if self.client is None:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self.client

    async def save_utterance(
        self,
        session_id: str,
        stt_text: str,
        utterance_index: int,
        speaker: str = "user",
        text: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
    ) -> dict:
        """
        발화 저장 API 호출

        Spring 2는:
        1. (오디오 있을 경우) S3에 오디오 업로드: s3://skala/sessions/{session_id}/utterance_{index}.wav
        2. MySQL에 메타데이터 저장 (텍스트는 항상 저장)

        Args:
            session_id: 세션 ID
            stt_text: STT 결과 또는 사용자 텍스트
            utterance_index: 발화 인덱스 (0부터 시작)
            audio_data: 오디오 바이너리 데이터 (WAV, 선택사항)
            started_at: 발화 시작 시각
            ended_at: 발화 종료 시각

        Returns:
            API 응답 ({"success": true, "s3_url": "...", "utterance_id": 123})

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)
        if ended_at is None:
            ended_at = datetime.now(timezone.utc)

        def _to_offset(dt: datetime) -> str:
            """Ensure datetime is timezone-aware and return ISO8601 string with offset."""
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        url = f"/internal/sessions/{session_id}/utterances"

        data = {
            "stt_text": stt_text,
            "utterance_index": str(utterance_index),
            "started_at": _to_offset(started_at),
            "ended_at": _to_offset(ended_at),
            "speaker": (speaker or "user").lower(),
            "text": text or stt_text,
        }

        try:
            client = await self._get_client()

            # 오디오가 있으면 multipart/form-data, 없으면 JSON
            if audio_data:
                # multipart/form-data: 오디오 + 모든 메타데이터
                files = {
                    "audio": ("audio.wav", audio_data, "audio/wav"),
                    "stt_text": (None, data["stt_text"]),
                    "utterance_index": (None, data["utterance_index"]),
                    "started_at": (None, data["started_at"]),
                    "ended_at": (None, data["ended_at"]),
                    "speaker": (None, data["speaker"]),
                    "text": (None, data["text"]),
                }
                response = await client.post(url, files=files)
            else:
                # 텍스트만 전송 (오디오 없음)
                response = await client.post(url, json=data)

            response.raise_for_status()

            result = response.json()

            if audio_data:
                logger.info(
                    f"Utterance saved (with audio): session={session_id}, index={utterance_index}, "
                    f"s3_url={result.get('s3_url')}"
                )
            else:
                logger.info(
                    f"Utterance saved (text only): session={session_id}, index={utterance_index}"
                )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to save utterance: session={session_id}, index={utterance_index}, "
                f"status={e.response.status_code}, error={e}"
            )
            raise

        except Exception as e:
            logger.error(f"Utterance save error: {e}", exc_info=True)
            raise

    async def get_session(self, session_id: str) -> Optional[dict]:
        """
        Spring 2에서 세션 정보 조회

        Args:
            session_id: 세션 ID (UUID)

        Returns:
            {"success": true, "user_id": 1, "scenario_id": 31, "status": "ACTIVE"}
            또는 None (세션 없음)
        """
        url = f"/internal/sessions/{session_id}"

        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Session retrieved: session_id={session_id}")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Session not found: {session_id}")
                return None
            logger.error(
                f"Failed to get session: session_id={session_id}, "
                f"status={e.response.status_code}"
            )
            raise

        except Exception as e:
            logger.error(f"Session retrieval error: {e}", exc_info=True)
            raise

    async def complete_session(
        self, session_id: str, status: str = "FINISHED", reason: str = "user_end"
    ) -> dict:
        """
        세션 완료 API 호출

        Spring 2는 MySQL의 sessions 테이블을 업데이트합니다:
        - status = 'FINISHED'
        - ended_at = NOW()
        - end_reason = reason

        Args:
            session_id: 세션 ID
            status: 세션 상태 ("FINISHED", "ERROR" 등)
            reason: 종료 사유 ("user_end", "timeout", "disconnected", "error")

        Returns:
            API 응답 ({"success": true, "session_id": "...", "ended_at": "..."})

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = f"/internal/sessions/{session_id}/complete"

        payload = {"status": status, "reason": reason}

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Session completed: session={session_id}, status={status}, reason={reason}"
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to complete session: session={session_id}, "
                f"status={e.response.status_code}, error={e}"
            )
            raise

        except Exception as e:
            logger.error(f"Session completion error: {e}", exc_info=True)
            raise

    async def close(self):
        """HTTP 클라이언트 종료"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Spring2Client closed")


# 전역 Spring 2 클라이언트 인스턴스
spring2_client = Spring2Client()
