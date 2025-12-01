"""
LLM Service (Legacy Compatibility Layer)
========================================
⚠️ DEPRECATED: 하위 호환성을 위해 유지됩니다.

마이그레이션 가이드:
    기존: from app.roleplaying.services.llm_service import LLMService
    신규: from app.roleplaying.services.llm_service_refactored import ConversationAnalyzerImpl
    신규: from app.roleplaying.services.dependencies import ConversationAnalyzerDep

구조:
    - LLMService: 레거시 호환성 Facade
    - 내부적으로 llm_service_refactored의 구현체들을 위임
    - 모든 메서드는 Deprecated 경고 발생
    - 기능은 동일하게 유지

목표:
    - 기존 코드 파괴 방지
    - 점진적 마이그레이션 지원
    - 새 코드는 llm_service_refactored 직접 사용
"""

import warnings
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    ⚠️ DEPRECATED: OpenAI 기반 LLM 서비스 (레거시)

    마이그레이션:
        LLMService(purpose="analysis")
        → ConversationAnalyzerImpl(...)

        LLMService(purpose="question_generation")
        → QuestionGeneratorImpl(...)

        LLMService(purpose="ai_response")
        → AIResponseGeneratorImpl(...)
    """

    def __init__(self, purpose: str = "ai_response", model_name: str = None):
        """
        Args:
            purpose: 사용 목적 ("analysis", "question_generation", "ai_response")
            model_name: 커스텀 모델명 (선택사항)

        ⚠️ Deprecated: 새 코드는 llm_service_refactored의 구현체 직접 사용
        """
        warnings.warn(
            "LLMService is deprecated. Use specific service classes:\n"
            "- ConversationAnalyzerImpl for conversation analysis\n"
            "- QuestionGeneratorImpl for question generation\n"
            "- AIResponseGeneratorImpl for AI responses\n"
            "Import from app.roleplaying.services.llm_service_refactored",
            DeprecationWarning,
            stacklevel=2
        )

        self.purpose = purpose
        self._impl = None
        self._initialize_impl(model_name)

    def _initialize_impl(self, model_name: str = None):
        """목적에 맞는 구현체 초기화"""
        # Lazy import to avoid circular dependency
        from app.roleplaying.services.llm_service_refactored import (
            ConversationAnalyzerImpl,
            QuestionGeneratorImpl,
            AIResponseGeneratorImpl
        )

        if self.purpose == "analysis":
            self._impl = ConversationAnalyzerImpl(
                api_key=settings.openai_api_key,
                model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
                temperature=0.3
            )
        elif self.purpose == "question_generation":
            self._impl = QuestionGeneratorImpl(
                api_key=settings.openai_api_key,
                model_name=model_name or settings.OPENAI_MODEL_QUESTION_GENERATION,
                temperature=0.7
            )
        else:  # ai_response
            self._impl = AIResponseGeneratorImpl(
                api_key=settings.openai_api_key,
                model_name=model_name or settings.OPENAI_MODEL_AI_RESPONSE,
                temperature=0.7
            )

        logger.info(f"LLMService initialized for: {self.purpose}")

    # ============================================
    # ConversationAnalyzer 메서드 위임
    # ============================================

    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """대화 상황 분석 (위임)"""
        if hasattr(self._impl, 'analyze_situation'):
            return await self._impl.analyze_situation(messages, my_role, conversation_date)
        raise NotImplementedError(f"analyze_situation not available for purpose={self.purpose}")

    # ============================================
    # ScenarioGenerator 메서드 위임
    # ============================================

    async def generate_scenario_from_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> Dict[str, Any]:
        """시나리오 생성 (위임)"""
        if hasattr(self._impl, 'generate_scenario_from_prompt'):
            return await self._impl.generate_scenario_from_prompt(situation, my_role, ai_role)
        raise NotImplementedError(f"generate_scenario_from_prompt not available for purpose={self.purpose}")

    async def generate_scenario_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> AsyncGenerator[str, None]:
        """시나리오 생성 스트리밍 (위임)"""
        if hasattr(self._impl, 'generate_scenario_streaming'):
            async for chunk in self._impl.generate_scenario_streaming(situation, my_role, ai_role):
                yield chunk
        else:
            raise NotImplementedError(f"generate_scenario_streaming not available for purpose={self.purpose}")

    # ============================================
    # QuestionGenerator 메서드 위임
    # ============================================

    async def generate_next_question(
        self,
        situation: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """다음 질문 생성 (위임)"""
        if hasattr(self._impl, 'generate_next_question'):
            return await self._impl.generate_next_question(situation, conversation_history)
        raise NotImplementedError(f"generate_next_question not available for purpose={self.purpose}")

    async def generate_followup_question(self, prompt: str) -> str:
        """Follow-up 질문 생성 (위임)"""
        if hasattr(self._impl, 'generate_followup_question'):
            return await self._impl.generate_followup_question(prompt)
        raise NotImplementedError(f"generate_followup_question not available for purpose={self.purpose}")

    async def generate_followup_question_stream(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Follow-up 질문 생성 스트리밍 (위임)"""
        if hasattr(self._impl, 'generate_followup_question_stream'):
            async for chunk in self._impl.generate_followup_question_stream(prompt):
                yield chunk
        else:
            raise NotImplementedError(f"generate_followup_question_stream not available for purpose={self.purpose}")

    # ============================================
    # AIResponseGenerator 메서드 위임
    # ============================================

    async def generate_ai_response(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """AI 응답 생성 (위임)"""
        if hasattr(self._impl, 'generate_ai_response'):
            return await self._impl.generate_ai_response(situation, my_role, ai_role, conversation_history)
        raise NotImplementedError(f"generate_ai_response not available for purpose={self.purpose}")

    async def generate_ai_response_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """AI 응답 생성 스트리밍 (위임)"""
        if hasattr(self._impl, 'generate_ai_response_streaming'):
            async for chunk in self._impl.generate_ai_response_streaming(situation, my_role, ai_role, conversation_history):
                yield chunk
        else:
            raise NotImplementedError(f"generate_ai_response_streaming not available for purpose={self.purpose}")


# ============================================
# 전역 인스턴스 (레거시 호환성용)
# ============================================

# ⚠️ DEPRECATED: 새 코드는 dependencies.py의 Depends()를 사용하세요
llm_service = LLMService()
