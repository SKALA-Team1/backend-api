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
        played_turns: Optional[int] = None,
        completed_all_turns: bool = False,
        finish_reason: Optional[str] = None,
        status: str = "IN_PROGRESS",
        pronunciation_score: Optional[int] = None,
        grammar_score: Optional[int] = None,
        relevance_score: Optional[int] = None,
        overall_score: Optional[int] = None,
        needs_correction: Optional[bool] = None,
        retry_count: Optional[int] = None,
        primary_issue: Optional[str] = None,
        feedback_sections: Optional[list] = None,
        question_ko: Optional[str] = None,
        recommended_keywords: Optional[list] = None,
    ) -> dict:
        """
        발화 저장 API 호출 (바이링궐 피드백 포함)

        Spring 2는:
        1. (오디오 있을 경우) S3에 오디오 업로드: s3://skala/sessions/{session_id}/utterance_{index}.wav
        2. MySQL의 scenario_message에 메타데이터 저장 (텍스트, 피드백 등)
        3. scenario_message.feedback_sections에 구조화된 바이링궐 피드백 저장 (NEW)
        4. scenario_session 테이블 업데이트 (turnCount, completedAllTurns, status 등)

        Args:
            session_id: 세션 ID
            stt_text: STT 결과 또는 사용자 텍스트
            utterance_index: 발화 인덱스 (0부터 시작)
            audio_data: 오디오 바이너리 데이터 (WAV, 선택사항)
            started_at: 발화 시작 시각
            ended_at: 발화 종료 시각
            played_turns: AI가 한 질문의 총 개수
            completed_all_turns: 모든 턴(10개)을 완료했는지 여부
            finish_reason: 세션 종료 사유 (turn_limit, user_end, timeout, error 등)
            status: 세션 상태 (IN_PROGRESS, FINISHED, ERROR)
            pronunciation_score / grammar_score / relevance_score / overall_score:
                피드백 점수 (없으면 None)
            needs_correction: 재시도 필요 여부
            retry_count: 현재 재시도 횟수
            primary_issue: 피드백 이슈 분류 (pronunciation, grammar, relevance 등)
            feedback_sections: 구조화된 바이링궐 피드백 (NEW - optional)
                [
                    {
                        "type": "pronunciation",
                        "feedback_en": "...",
                        "feedback_ko": "...",
                        "score": 70
                    },
                    ...
                ]

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

        # Spring2 API requires: speaker, text, utteranceIndex (as JSON)
        # Optional: audio (as base64-encoded string), startedAt, endedAt
        import base64

        normalized_speaker = (speaker or "user").lower()
        final_text = text or stt_text

        try:
            client = await self._get_client()

            # Build JSON payload
            # Note: Spring2 uses snake_case for JSON field names (@JsonNaming)
            payload = {
                "speaker": normalized_speaker,
                "text": final_text,
                "utterance_index": utterance_index,
            }

            # Add optional timestamp fields if available
            if started_at:
                payload["started_at"] = _to_offset(started_at)
            if ended_at:
                payload["ended_at"] = _to_offset(ended_at)

            # Add scenario_session update fields
            if played_turns is not None:
                payload["played_turns"] = played_turns
            payload["completed_all_turns"] = completed_all_turns
            if finish_reason is not None:
                payload["finish_reason"] = finish_reason
            payload["status"] = status

            # Add audio as base64-encoded string if provided
            if audio_data:
                payload["audio"] = base64.b64encode(audio_data).decode('utf-8')

            # Feedback metadata (nullable)
            # needs_correction: Convert Python Boolean to Integer (0/1) for DB
            needs_correction_int = None
            if needs_correction is not None:
                needs_correction_int = 1 if needs_correction else 0

            payload.update(
                pronunciation_score=pronunciation_score,
                grammar_score=grammar_score,
                relevance_score=relevance_score,
                overall_score=overall_score,
                needs_correction=needs_correction_int,  # ✅ Integer 0/1
                retry_count=retry_count,
                primary_issue=primary_issue,
            )

            # Structured bilingual feedback sections (NEW - optional)
            if feedback_sections:
                payload["feedback_sections"] = feedback_sections

            # AI question fields (bilingual + keywords) - stored directly in scenario_message
            if question_ko:
                payload["question_ko"] = question_ko
            if recommended_keywords:
                payload["recommended_keywords"] = recommended_keywords

            # 로그용 payload 생성 (오디오 데이터 제외)
            log_payload = payload.copy()
            if "audio" in log_payload:
                audio_len = len(log_payload["audio"]) if log_payload["audio"] else 0
                log_payload["audio"] = f"<base64_audio_data:{audio_len}_bytes>" if audio_len > 0 else None
            
            logger.info(f"📤 [Spring2] Sending payload: {log_payload}")

            response = await client.post(url, json=payload)

            logger.info(f"📥 [Spring2] Response status: {response.status_code}")

            response.raise_for_status()

            result = response.json()
            logger.info(f"📥 [Spring2] Response body: {result}")

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
        self,
        session_id: str,
        status: str = "FINISHED",
        reason: str = "user_end",
        played_turns: Optional[int] = None,
        completed_all_turns: bool = False,
        finish_reason: Optional[str] = None,
        finished_at: Optional[datetime] = None,
    ) -> dict:
        """
        세션 완료 API 호출

        Spring 2는 MySQL의 sessions 테이블을 업데이트합니다:
        - status = 'FINISHED'
        - ended_at = NOW()
        - end_reason = reason
        - scenario_session 테이블도 함께 업데이트

        Args:
            session_id: 세션 ID
            status: 세션 상태 ("FINISHED", "ERROR" 등)
            reason: 종료 사유 ("user_end", "timeout", "disconnected", "error")
            played_turns: AI가 한 질문의 총 개수
            completed_all_turns: 모든 턴(10개)을 완료했는지 여부
            finish_reason: 세션 종료 사유
            finished_at: 세션 종료 시각

        Returns:
            API 응답 ({"success": true, "session_id": "...", "ended_at": "..."})

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = f"/internal/sessions/{session_id}/complete"

        def _to_offset(dt: datetime) -> str:
            """Ensure datetime is timezone-aware and return ISO8601 string with offset."""
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        payload = {"status": status, "reason": reason}

        # Add scenario_session update fields
        if played_turns is not None:
            payload["played_turns"] = played_turns
        payload["completed_all_turns"] = completed_all_turns
        if finish_reason is not None:
            payload["finish_reason"] = finish_reason
        if finished_at is not None:
            payload["finished_at"] = _to_offset(finished_at)

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

    async def get_random_it_question(self) -> Optional[dict]:
        """
        랜덤 IT 질문 조회 API 호출

        Spring 2는 MySQL의 it_question 테이블에서 랜덤 질문을 반환합니다.

        Returns:
            질문 데이터 또는 None (질문이 없을 경우)
            {
                "question_id": int,
                "question_text": str,
                "question_text_ko": str,
                "category": str,
                "difficulty": str,
                "key_keywords": list,
                "model_answer": str
            }

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = "/internal/it-questions/random"

        try:
            client = await self._get_client()
            response = await client.get(url)

            logger.info(f"📥 [Spring2] Random question response status: {response.status_code}")

            if response.status_code == 204:
                logger.warning("No questions available in database")
                return None

            response.raise_for_status()

            data = response.json()
            logger.info(f"Random question fetched: question_id={data.get('question_id')}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch random question: status={e.response.status_code}, error={e}")
            raise

        except Exception as e:
            logger.error(f"Random question fetch error: {e}", exc_info=True)
            raise

    async def get_it_question_by_id(self, question_id: int) -> Optional[dict]:
        """
        IT 질문 ID로 조회 API 호출

        Spring 2는 MySQL의 it_question 테이블에서 특정 질문을 반환합니다.

        Args:
            question_id: 질문 ID

        Returns:
            질문 데이터 또는 None (질문이 없을 경우)

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = f"/internal/it-questions/{question_id}"

        try:
            client = await self._get_client()
            response = await client.get(url)

            logger.info(f"📥 [Spring2] Question by ID response status: {response.status_code}")

            if response.status_code == 404:
                logger.warning(f"Question {question_id} not found")
                return None

            response.raise_for_status()

            data = response.json()
            logger.info(f"Question fetched: question_id={question_id}")

            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to fetch question {question_id}: status={e.response.status_code}, error={e}")
            raise

        except Exception as e:
            logger.error(f"Question fetch error: {e}", exc_info=True)
            raise

    async def save_practice_session(
        self,
        user_id: int,
        question_id: int,
        user_answer: str,
        clarity_score: int,
        technical_accuracy_score: int,
        terminology_score: int,
        overall_score: int,
        feedback: str,
        session_type: str = "TEXT",
        audio_url: Optional[str] = None,
    ) -> Optional[int]:
        """
        IT 연습 세션 저장 API 호출

        Spring 2는 MySQL의 it_practice_session 테이블에 평가 결과를 저장합니다.

        Args:
            user_id: 사용자 ID
            question_id: 질문 ID
            user_answer: 사용자 답변
            clarity_score: 명확성 점수 (0-100)
            technical_accuracy_score: 기술적 정확성 점수 (0-100)
            terminology_score: 전문용어 사용 점수 (0-100)
            overall_score: 종합 점수 (0-100)
            feedback: 한국어 피드백
            session_type: TEXT or VOICE
            audio_url: 음성 URL (선택)

        Returns:
            session_id 또는 None (실패 시)

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = "/internal/it-practice/sessions"

        payload = {
            "user_id": user_id,
            "question_id": question_id,
            "user_answer": user_answer,
            "clarity_score": clarity_score,
            "technical_accuracy_score": technical_accuracy_score,
            "terminology_score": terminology_score,
            "overall_score": overall_score,
            "feedback": feedback,
            "session_type": session_type,
            "audio_url": audio_url,
        }

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)

            logger.info(f"📥 [Spring2] Practice session save response status: {response.status_code}")

            if response.status_code == 400:
                logger.error(f"Bad request when creating practice session: {response.text}")
                return None

            response.raise_for_status()

            result = response.json()
            session_id = result.get("session_id") or result.get("sessionId")
            logger.info(f"Practice session saved: user_id={user_id}, session_id={session_id}")

            return session_id

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to save practice session: user_id={user_id}, "
                f"status={e.response.status_code}, error={e}"
            )
            raise

        except Exception as e:
            logger.error(f"Practice session save error: {e}", exc_info=True)
            raise

    async def save_chatbot_conversation(
        self,
        user_id: int,
        user_message: str,
        bot_response: str,
        context: Optional[str] = None,
    ) -> dict:
        """
        IT 챗봇 대화 저장 API 호출

        Spring 2는 MySQL의 it_chatbot_conversation 테이블에 대화를 저장합니다.

        Args:
            user_id: 사용자 ID
            user_message: 사용자 질문/메시지
            bot_response: 챗봇 응답
            context: 대화 컨텍스트 (JSON 문자열, 선택사항)

        Returns:
            API 응답 ({"conversationId": 1, "userId": 6, ...})

        Raises:
            httpx.HTTPStatusError: HTTP 에러 발생 시
        """
        url = "/internal/it-chatbot/conversations"

        payload = {
            "user_id": user_id,
            "user_message": user_message,
            "bot_response": bot_response,
        }

        if context:
            payload["context"] = context

        try:
            client = await self._get_client()
            response = await client.post(url, json=payload)

            logger.info(f"📥 [Spring2] Chatbot conversation save response status: {response.status_code}")

            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Chatbot conversation saved: user_id={user_id}, conversation_id={result.get('conversationId')}"
            )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to save chatbot conversation: user_id={user_id}, "
                f"status={e.response.status_code}, error={e}"
            )
            raise

        except Exception as e:
            logger.error(f"Chatbot conversation save error: {e}", exc_info=True)
            raise

    async def close(self):
        """HTTP 클라이언트 종료"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Spring2Client closed")


# 전역 Spring 2 클라이언트 인스턴스
spring2_client = Spring2Client()
