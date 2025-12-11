"""
Question Service
================
IT 질문 조회 서비스

역할:
- Spring 2 API를 통해 질문 조회
"""

import logging
import json
from typing import Optional, Dict, Any, List
import httpx
import os

logger = logging.getLogger(__name__)


class QuestionService:
    """IT 질문 조회 서비스"""

    def __init__(self):
        """질문 서비스 초기화"""
        self.spring2_base_url = os.getenv("SPRING2_BASE_URL", "http://localhost:8081")
        logger.info(f"QuestionService initialized (Spring2: {self.spring2_base_url})")

    async def get_random_question(self) -> Optional[Dict[str, Any]]:
        """
        랜덤 질문 조회

        Returns:
            {
                "question_id": int,
                "question_text": str,
                "question_text_ko": str,
                "category": str,
                "difficulty": str,
                "key_keywords": list,
                "model_answer": str
            }
            또는 None
        """
        try:
            url = f"{self.spring2_base_url}/internal/it-questions/random"
            logger.info(f"🎲 [랜덤 질문 조회] Spring 2 API 호출: {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code == 204:
                    logger.warning("No questions available in database")
                    return None

                response.raise_for_status()
                data = response.json()

                # Spring 2가 이미 snake_case로 보냄 (@JsonProperty)
                return {
                    "question_id": data["question_id"],
                    "question_text": data["question_text"],
                    "question_text_ko": data.get("question_text_ko"),
                    "category": data["category"],
                    "difficulty": data["difficulty"],
                    "key_keywords": data.get("key_keywords", []),
                    "model_answer": data.get("model_answer", "")
                }
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spring 2 for random question: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch random question from Spring 2 (HTTP error): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching random question: {e}")
            return None

    async def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        질문 ID로 조회

        Args:
            question_id: 질문 ID

        Returns:
            질문 데이터 또는 None
        """
        try:
            url = f"{self.spring2_base_url}/internal/it-questions/{question_id}"
            logger.info(f"🔍 [질문 조회] Spring 2 API 호출: {url}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    logger.warning(f"Question {question_id} not found")
                    return None

                response.raise_for_status()
                data = response.json()

                # Spring 2가 이미 snake_case로 보냄 (@JsonProperty)
                return {
                    "question_id": data["question_id"],
                    "question_text": data["question_text"],
                    "question_text_ko": data.get("question_text_ko"),
                    "category": data["category"],
                    "difficulty": data["difficulty"],
                    "key_keywords": data.get("key_keywords", []),
                    "model_answer": data.get("model_answer", "")
                }
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spring 2 for question {question_id}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch question {question_id} from Spring 2 (HTTP error): {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching question {question_id}: {e}")
            return None
