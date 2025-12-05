"""
Spring Boot API 클라이언트
피드백을 Spring 백엔드로 전송하는 클라이언트
"""
import httpx
from typing import Dict
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SpringAPIClient:
    """Spring Boot API 클라이언트"""

    def __init__(self, spring_api_url: str = None):
        """
        Args:
            spring_api_url: Spring Boot API URL (기본값: settings에서 가져옴)
        """
        self.spring_api_url = spring_api_url or settings.SPRING_API_URL
        self.timeout = 30.0

    async def save_feedback(
        self,
        session_id: str,
        scenario_id: int,
        total_pronunciation: float,
        total_grammar: float,
        total_diversity: float,
        final_feedback_short: str,
        final_feedback_long: str,
    ) -> Dict:
        """
        피드백을 Spring API로 전송하여 저장

        Args:
            session_id: 세션 ID
            scenario_id: 시나리오 ID
            total_pronunciation: 발음 평균 점수
            total_grammar: 문법 평균 점수
            total_diversity: 적합성 평균 점수
            final_feedback_short: 짧은 피드백 (요약)
            final_feedback_long: 긴 피드백 (상세)

        Returns:
            Spring API 응답 (feedback_id 포함)
        """
        url = f"{self.spring_api_url}/internal/feedback/save"

        payload = {
            "sessionId": session_id,
            "scenarioId": scenario_id,
            "totalPronunciation": total_pronunciation,
            "totalGrammar": total_grammar,
            "totalDiversity": total_diversity,
            "finalFeedbackShort": final_feedback_short,
            "finalFeedbackLong": final_feedback_long,
        }

        logger.info(f"Spring API 호출: {url}, sessionId={session_id}, scenarioId={scenario_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                logger.info(f"Spring API 응답 성공: feedbackId={result.get('feedbackId')}")
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Spring API HTTP 오류: status={e.response.status_code}, body={e.response.text}")
            raise Exception(f"Spring API 호출 실패: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Spring API 연결 오류: {str(e)}")
            raise Exception(f"Spring API 연결 실패: {str(e)}")
        except Exception as e:
            logger.error(f"Spring API 호출 중 예외 발생: {str(e)}")
            raise

    async def health_check(self) -> Dict:
        """
        Spring API 헬스 체크

        Returns:
            헬스 체크 결과
        """
        url = f"{self.spring_api_url}/internal/feedback/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return {"status": "healthy", "message": response.text}
        except Exception as e:
            logger.error(f"Spring API 헬스 체크 실패: {str(e)}")
            raise
