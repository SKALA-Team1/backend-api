"""
Session Service
================
IT 연습 세션 저장 서비스

역할:
- Spring 2 API를 통해 세션 저장
- 평가 결과를 MySQL에 영구 저장
"""

import logging
from typing import Optional, Dict, Any
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """IT 연습 세션 저장 서비스"""

    def __init__(self):
        """세션 서비스 초기화"""
        self.spring2_base_url = settings.SPRING2_BASE_URL
        logger.info(f"SessionService initialized (Spring2: {self.spring2_base_url})")

    async def create_session(
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
        audio_url: str = None
    ) -> Optional[int]:
        """
        세션 생성 및 저장

        Args:
            user_id: 사용자 ID
            question_id: 질문 ID
            user_answer: 사용자 답변
            clarity_score: 명확성 점수
            technical_accuracy_score: 기술적 정확성 점수
            terminology_score: 전문용어 점수
            overall_score: 종합 점수
            feedback: 피드백 (한국어 우선)
            session_type: TEXT or VOICE
            audio_url: 음성 URL (선택)

        Returns:
            session_id 또는 None (실패 시)
        """
        try:
            url = f"{self.spring2_base_url}/internal/it-practice/sessions"
            logger.info(f"💾 [세션 저장] Spring 2 API 호출: {url}")

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
                "audio_url": audio_url
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 400:
                    logger.error(f"Bad request when creating session: {response.text}")
                    return None

                response.raise_for_status()
                data = response.json()

                session_id = data.get("session_id")
                logger.info(f"✅ [세션 저장 완료] session_id={session_id}")

                return session_id

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spring 2 to create session: {e}", exc_info=True)
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create session (HTTP error): {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while creating session: {e}", exc_info=True)
            return None

    async def get_user_sessions(self, user_id: int) -> Optional[list]:
        """
        사용자의 세션 목록 조회

        Args:
            user_id: 사용자 ID

        Returns:
            세션 목록 또는 None
        """
        try:
            url = f"{self.spring2_base_url}/internal/it-practice/sessions/{user_id}"
            logger.info(f"📋 [세션 목록 조회] Spring 2 API 호출: {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                sessions = response.json()
                logger.info(f"✅ [세션 목록 조회 완료] {len(sessions)}개 세션")

                return sessions

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spring 2 to fetch user sessions: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch user sessions (HTTP error): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching user sessions: {e}")
            return None

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            통계 정보 또는 None
        """
        try:
            url = f"{self.spring2_base_url}/internal/it-practice/stats/{user_id}"
            logger.info(f"📊 [통계 조회] Spring 2 API 호출: {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                stats = response.json()
                logger.info(f"✅ [통계 조회 완료]")

                return stats

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spring 2 to fetch user stats: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch user stats (HTTP error): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching user stats: {e}")
            return None
