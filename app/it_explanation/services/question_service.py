"""
Question Service
================
IT 질문 조회 서비스

역할:
- (현재) Mock 데이터로 질문 제공
- (나중에) Spring 2 API를 통해 질문 조회
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class QuestionService:
    """IT 질문 조회 서비스"""

    def __init__(self):
        """질문 서비스 초기화"""
        logger.info("QuestionService initialized")

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
        # TODO: Spring 2 API 호출로 대체
        # GET /internal/it-questions/random
        logger.info("🎲 [랜덤 질문 조회] Mock 데이터 반환")
        return self._get_mock_question()

    async def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        질문 ID로 조회

        Args:
            question_id: 질문 ID

        Returns:
            질문 데이터 또는 None
        """
        # TODO: Spring 2 API 호출로 대체
        # GET /internal/it-questions/{question_id}
        logger.info(f"🔍 [질문 조회] question_id={question_id} (Mock)")
        return self._get_mock_question()

    def _get_mock_question(self) -> Dict[str, Any]:
        """Mock 질문 데이터 반환"""
        return {
            "question_id": 1,
            "question_text": "Explain the difference between monolithic and microservices architecture.",
            "question_text_ko": "모놀리식과 마이크로서비스 아키텍처의 차이를 설명하세요.",
            "category": "Architecture",
            "difficulty": "MEDIUM",
            "key_keywords": [
                "scalability",
                "deployment",
                "independence",
                "fault isolation",
                "service boundary"
            ],
            "model_answer": (
                "Monolithic architecture is a single unified application where all components "
                "(UI, business logic, data access) are tightly coupled and deployed together. "
                "In contrast, microservices architecture breaks the application into small, "
                "independent services that can be developed, deployed, and scaled separately. "
                "Microservices offer better scalability, fault isolation, and deployment flexibility, "
                "but introduce complexity in service communication and distributed system management."
            ),
            "model_answer_ko": (
                "모놀리식 아키텍처는 모든 컴포넌트(UI, 비즈니스 로직, 데이터 접근)가 "
                "긴밀하게 결합되어 하나의 통합 애플리케이션으로 배포되는 구조입니다. "
                "반면 마이크로서비스 아키텍처는 애플리케이션을 작은 독립적인 서비스들로 나누어 "
                "각각 개발, 배포, 확장할 수 있습니다. "
                "마이크로서비스는 확장성, 장애 격리, 배포 유연성이 뛰어나지만 "
                "서비스 간 통신과 분산 시스템 관리의 복잡성이 증가합니다."
            )
        }
