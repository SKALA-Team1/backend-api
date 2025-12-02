"""
LLM Scenario Generator Service
==============================
상황 기반 시나리오 생성

역할:
- 상황 분석 결과를 받아 학습 시나리오 생성
- opening_question, 3개의 follow-up 질문, 배경 설명 생성
- JSON 형식으로 구조화된 시나리오 반환

예시:
    generator = ScenarioGeneratorImpl()
    scenario = await generator.generate_scenario_from_prompt(
        situation="John과 Mary가 프로젝트 계획을 논의 중...",
        my_role="Product Manager",
        ai_role="Team Lead"
    )
    # {"opening_question": "...", "questions": [...], "context": "..."}

의존성:
    - app.roleplaying.services.llm_base (LLM 초기화)
    - app.roleplaying.prompts.constants (프롬프트 관리)
    - app.roleplaying.services.utils (JSON 추출, 질문 정규화)
"""

import json
import logging
from typing import Dict, Any, AsyncGenerator

from app.config import settings
from app.roleplaying.services.llm.llm_base import LLMServiceBase
from app.roleplaying.prompts.constants import SCENARIO_GENERATION_PROMPT
from app.roleplaying.services.utils.service_utils import (
    extract_json_from_response,
    normalize_questions,
)

logger = logging.getLogger(__name__)


class ScenarioGeneratorImpl(LLMServiceBase):
    """
    시나리오 생성 서비스

    상황 기반으로 영어 학습용 시나리오를 생성합니다.

    책임:
        - 상황 텍스트를 받아 시나리오 생성
        - 정확히 3개의 follow-up 질문 생성
        - opening_question, context 포함
        - JSON 형식으로 구조화

    의존성:
        - LLMServiceBase (LLM 프로바이더)
        - SCENARIO_GENERATION_PROMPT (프롬프트 상수)
        - extract_json_from_response (JSON 추출 유틸)
        - normalize_questions (질문 정규화 유틸)
    """

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        시나리오 생성기 초기화

        Args:
            api_key: OpenAI API 키 (기본값: settings.openai_api_key)
            model_name: 모델명 (기본값: settings.OPENAI_MODEL_QUESTION_GENERATION)
            temperature: 창의성 레벨 (기본값: 0.7, 창의적 시나리오용)
        """
        super().__init__(
            api_key=api_key,
            model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
            temperature=temperature
        )

    async def generate_scenario_from_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> Dict[str, Any]:
        """
        상황 기반 시나리오 생성

        상황을 받아 영어 대화 연습용 시나리오를 생성합니다.

        Args:
            situation: 상황 설명 텍스트 (예: "신입 직원 면접")
            my_role: 사용자의 역할 (예: "Product Manager")
            ai_role: AI의 역할 (예: "Team Lead")

        Returns:
            구조화된 시나리오 딕셔너리
            {
                "opening_question": str,           # 대화 시작 질문
                "questions": [str, str, str],      # 정확히 3개의 follow-up 질문
                "context": str                     # 시나리오 배경 설명
            }

        예시:
            scenario = await generator.generate_scenario_from_prompt(
                situation="Project kickoff meeting",
                my_role="Product Manager",
                ai_role="Team Lead"
            )
        """
        try:
            # ====================================
            # Step 1: 프롬프트 구성 (상수에서 가져옴)
            # ====================================
            prompt = SCENARIO_GENERATION_PROMPT.format(
                situation=situation,
                my_role=my_role,
                ai_role=ai_role
            )

            # ====================================
            # Step 2: LLM 호출
            # ====================================
            logger.info("🟡 [시나리오 생성] LLM 호출 중...")
            response = await self.llm.invoke(prompt)

            # ====================================
            # Step 3: JSON 추출 및 검증
            # ====================================
            result = extract_json_from_response(response)

            if result:
                # 질문 정규화 (정확히 3개)
                questions = result.get("questions", [])
                normalized_questions = normalize_questions(questions, expected_count=3)

                # 부족한 질문 채우기
                while len(normalized_questions) < 3:
                    normalized_questions.append(
                        f"Tell me more about {ai_role.lower()}"
                    )

                result["questions"] = normalized_questions[:3]

                logger.info(f"✅ [시나리오 생성 완료] {len(normalized_questions)} 질문 생성")
                return result

            # ====================================
            # Step 4: 폴백 (기본 시나리오)
            # ====================================
            logger.warning("Failed to parse scenario JSON, returning default")
            return {
                "opening_question": f"Hello, I'm a {ai_role}. How can I help you today?",
                "questions": [
                    "Can you tell me more about your project?",
                    "What are your main concerns?",
                    "How do you plan to move forward?",
                ],
                "context": situation,
            }

        except Exception as e:
            logger.error(f"Scenario generation failed: {e}", exc_info=True)
            # ====================================
            # 예외 처리: 기본값 반환
            # ====================================
            return {
                "opening_question": "What would you like to discuss?",
                "questions": [
                    "Can you provide more details?",
                    "What's your perspective?",
                    "How can we solve this?",
                ],
                "context": "Unable to analyze situation",
            }

    async def generate_scenario_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 기반 시나리오 생성

        시나리오를 스트리밍으로 생성합니다.
        (현재는 일반 버전의 결과를 yield함)

        Args:
            situation: 상황 설명
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Yields:
            JSON 문자열 형식의 시나리오
        """
        # LangChain의 스트리밍 API 필요시 확장 가능
        result = await self.generate_scenario_from_prompt(situation, my_role, ai_role)
        yield json.dumps(result, ensure_ascii=False)
