"""
ReAct Agent for Feedback Decision

구조:
1. FeedbackDecisionAgentImpl: ReAct 로직 직접 구현
2. Tool 실행 및 LLM 추론
3. 평가 결과 기반 피드백/질문 판단
"""

import logging
import json
import asyncio
import re
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI

from app.config import settings
from app.roleplaying.services.feedback.agent_tools import (
    evaluate_response_tool,
    analyze_retry_context_tool,
)

logger = logging.getLogger(__name__)


class FeedbackDecisionAgentImpl:
    """
    ReAct 기반 피드백/질문 결정 에이전트 (SOLID 준수)

    책임:
    - ReAct 패턴을 통한 피드백/질문 판단
    - Tool 실행 및 결과 종합
    - Fallback 처리

    의존성:
    - FeedbackOrchestrator: 평가 실행
    - LLM Provider: OpenAI 또는 Ollama
    """

    def __init__(
        self,
        feedback_orchestrator,
        llm_provider: str = "openai",
        api_key: str = None,
        model_name: str = None,
        temperature: float = 0.3,
    ):
        """
        ReAct Agent 초기화

        Args:
            feedback_orchestrator: FeedbackOrchestrator 인스턴스
            llm_provider: LLM 프로바이더 ("openai" 또는 "ollama")
            api_key: OpenAI API 키
            model_name: 모델명
            temperature: 창의성 레벨 (판단 용 - 낮을수록 일관성)
        """
        self.feedback_orchestrator = feedback_orchestrator
        self.llm_provider = llm_provider
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.OPENAI_MODEL_FEEDBACK
        self.temperature = temperature

        # LangChain LLM 초기화
        if llm_provider == "openai":
            self.llm = ChatOpenAI(
                model_name=self.model_name,
                api_key=self.api_key,
                temperature=temperature,
            )
        else:
            from langchain_community.llms import Ollama

            self.llm = Ollama(model=self.model_name, temperature=temperature)

        logger.info(
            f"✅ FeedbackDecisionAgentImpl initialized with {llm_provider} provider"
        )

    async def decide_feedback_or_question(
        self,
        session_state: Any,
        user_text: str,
        audio_data: Optional[bytes],
        retry_count: int,
        can_use_azure: bool = False,
    ) -> Dict[str, Any]:
        """
        ReAct 로직을 통한 피드백/질문 판단

        Args:
            session_state: 세션 상태 (대화 히스토리, 역할 등)
            user_text: 사용자 발화 텍스트
            audio_data: 사용자 오디오 데이터 (선택사항)
            retry_count: 현재 질문 재시도 횟수
            can_use_azure: Azure 발음 평가 사용 가능 여부

        Returns:
            {
                "action": "FEEDBACK" | "NEXT_QUESTION",
                "feedback_result": {...} | None,
                "reasoning": str,
                "confidence": float (0-1)
            }
        """
        try:
            logger.info(
                f"🤖 [ReAct] Starting decision: user_text='{user_text[:30]}...', retry={retry_count}"
            )

            # Step 1: 평가 실행 (Tool)
            logger.info("🔧 [ReAct] Step 1: Evaluating response...")

            evaluation_result = await evaluate_response_tool(
                feedback_orchestrator=self.feedback_orchestrator,
                user_text=user_text,
                audio_data=audio_data if can_use_azure else None,
                conversation_history=session_state.history if session_state else [],
                scenario_context={
                    "my_role": session_state.my_role if session_state else "",
                    "ai_role": session_state.ai_role if session_state else "",
                    "current_question": session_state.current_question_text if session_state else "",
                },
                retry_count=retry_count,
            )

            logger.info(
                f"📊 [ReAct] Evaluation result: "
                f"pronunciation={evaluation_result.get('pronunciation_score')}, "
                f"grammar={evaluation_result.get('grammar_score')}, "
                f"relevance={evaluation_result.get('relevance_score')}"
            )

            # Step 2: 재시도 컨텍스트 분석 (Tool)
            logger.info("🔧 [ReAct] Step 2: Analyzing retry context...")

            retry_context = await analyze_retry_context_tool(
                session_state=session_state,
                retry_count=retry_count,
                can_use_azure=can_use_azure,
            )

            logger.info(
                f"🔄 [ReAct] Retry context: "
                f"count={retry_context['retry_count']}, "
                f"max_exceeded={retry_context['is_max_retries_exceeded']}"
            )

            # Step 3: LLM의 최종 판단 (Thinking)
            logger.info("🔧 [ReAct] Step 3: LLM making final decision...")

            decision_prompt = self._format_decision_prompt(
                evaluation_result=evaluation_result,
                retry_context=retry_context,
                session_state=session_state,
                retry_count=retry_count,
            )

            # 동기 LLM 호출
            loop = asyncio.get_event_loop()
            llm_response = await loop.run_in_executor(
                None,
                lambda: self.llm.invoke(decision_prompt),
            )

            decision_text = (
                llm_response.content
                if hasattr(llm_response, "content")
                else str(llm_response)
            )

            logger.info(f"💭 [ReAct] LLM decision: {decision_text[:100]}...")

            # Step 4: 응답 파싱
            parsed_decision = self._parse_decision(decision_text)

            # ✅ FEEDBACK 결정 시 평가 결과를 feedback_result에 포함
            if parsed_decision["action"] == "FEEDBACK":
                primary_issue = evaluation_result.get("primary_issue", "")
                full_feedback_text = evaluation_result.get("feedback_text", "")

                # 필터링: primary_issue에 해당하는 피드백만 추출
                filtered_feedback = self._filter_feedback_text(
                    full_feedback_text,
                    primary_issue
                )

                parsed_decision["feedback_result"] = {
                    "scores": {
                        "pronunciation_score": evaluation_result.get("pronunciation_score"),
                        "grammar_score": evaluation_result.get("grammar_score"),
                        "relevance_score": evaluation_result.get("relevance_score"),
                        "overall_score": evaluation_result.get("overall_score"),
                    },
                    "feedback_text": filtered_feedback,
                    "needs_correction": evaluation_result.get("needs_correction", False),
                    "primary_issue": primary_issue,
                    "feedback_sections": evaluation_result.get("feedback_sections", []),
                    "retry_count": evaluation_result.get("retry_count", retry_count),
                    # 🔑 Raw evaluation objects for streaming feedback sections
                    "pronunciation": evaluation_result.get("pronunciation"),
                    "grammar": evaluation_result.get("grammar"),
                    "relevance": evaluation_result.get("relevance"),
                }

            logger.info(
                f"✅ [ReAct] Final decision: action={parsed_decision['action']}, "
                f"confidence={parsed_decision['confidence']:.2f}"
            )

            return parsed_decision

        except Exception as e:
            logger.error(f"❌ [ReAct] Error: {e}", exc_info=True)
            # Fallback: 기존 로직으로 돌아가기
            return await self._fallback_decision(
                session_state=session_state,
                user_text=user_text,
                audio_data=audio_data,
                retry_count=retry_count,
                can_use_azure=can_use_azure,
            )

    def _format_decision_prompt(
        self,
        evaluation_result: Dict[str, Any],
        retry_context: Dict[str, Any],
        session_state: Any,
        retry_count: int,
    ) -> str:
        """
        LLM 최종 판단용 프롬프트 구성
        """
        prompt = f"""Based on the evaluation results and context, decide whether to provide FEEDBACK or proceed to NEXT_QUESTION.

Evaluation Results:
- Pronunciation Score: {evaluation_result.get('pronunciation_score')}
- Grammar Score: {evaluation_result.get('grammar_score')}
- Relevance Score: {evaluation_result.get('relevance_score')}
- Overall Score: {evaluation_result.get('overall_score')}
- Primary Issue: {evaluation_result.get('primary_issue')}

Retry Context:
- Current Retry Count: {retry_context['retry_count']}/{retry_context['max_retries']}
- Max Retries Exceeded: {retry_context['is_max_retries_exceeded']}
- Conversation Turn: {retry_context['conversation_turn']}
- Learning Progress: {retry_context['estimated_learning_progress']}

Decision Criteria:
1. If all evaluations failed → NEXT_QUESTION
2. If max retries exceeded → NEXT_QUESTION (force pass)
3. If pronunciation < 65 → FEEDBACK (pronunciation issue)
4. If grammar < 70 → FEEDBACK (grammar issue)
5. If relevance < 75 → FEEDBACK (relevance issue)
6. Otherwise → NEXT_QUESTION (learner doing well)

Respond in JSON format ONLY (no other text):
{{
    "action": "FEEDBACK" or "NEXT_QUESTION",
    "reasoning": "Brief 1-2 sentence explanation",
    "confidence": <float 0.0-1.0>
}}"""
        return prompt

    def _filter_feedback_text(self, feedback_text: str, primary_issue: str) -> str:
        """
        Primary issue에 해당하는 피드백만 필터링

        Args:
            feedback_text: 전체 피드백 텍스트 (여러 종류 포함)
            primary_issue: 주요 문제 (pronunciation, grammar, relevance)

        Returns:
            필터링된 피드백 텍스트
        """
        if not feedback_text or not primary_issue:
            return feedback_text

        # primary_issue를 한글 키워드로 매핑
        issue_keywords = {
            "pronunciation": ["발음", "pronunciation"],
            "grammar": ["문법", "grammar"],
            "relevance": ["맥락", "context", "relevance", "관련성"],
        }

        keywords = issue_keywords.get(primary_issue.lower(), [])

        # 해당 키워드가 포함된 라인만 추출
        lines = feedback_text.split("\n")
        filtered_lines = []

        for line in lines:
            if any(keyword.lower() in line.lower() for keyword in keywords):
                filtered_lines.append(line)

        if filtered_lines:
            result = "\n".join(filtered_lines)
            logger.info(f"✂️ [Filter] Extracted {primary_issue} feedback")
            return result

        # 필터링 실패 시 전체 반환
        logger.warning(
            f"⚠️ [Filter] Could not filter feedback for issue={primary_issue}, returning full text"
        )
        return feedback_text

    def _parse_decision(self, llm_response: str) -> Dict[str, Any]:
        """
        LLM 응답 파싱
        """
        try:
            # JSON 블록 찾기
            json_match = re.search(r'\{[^{}]*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)

                return {
                    "action": parsed.get("action", "NEXT_QUESTION"),
                    "feedback_result": None,  # 별도로 생성
                    "reasoning": parsed.get("reasoning", "Agent decision"),
                    "confidence": float(parsed.get("confidence", 0.5)),
                }
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        # Fallback
        return {
            "action": "NEXT_QUESTION",
            "feedback_result": None,
            "reasoning": "Failed to parse LLM response, defaulting to NEXT_QUESTION",
            "confidence": 0.3,
        }

    async def _fallback_decision(
        self,
        session_state: Any,
        user_text: str,
        audio_data: Optional[bytes],
        retry_count: int,
        can_use_azure: bool,
    ) -> Dict[str, Any]:
        """
        Fallback: Agent 실패 시 기존 FeedbackJudge 로직 사용

        안정성 보장 (Production Safety)
        """
        logger.warning("🔄 [Fallback] Using traditional feedback evaluation")

        try:
            # 평가 실행
            feedback_result = await self.feedback_orchestrator.evaluate_response_fast(
                user_text=user_text,
                audio_data=audio_data if can_use_azure else None,
                conversation_history=session_state.history if session_state else [],
                scenario_context={
                    "my_role": session_state.my_role if session_state else "",
                    "ai_role": session_state.ai_role if session_state else "",
                    "current_question": session_state.current_question_text if session_state else "",
                },
                retry_count=retry_count,
            )

            if feedback_result and feedback_result.get("needs_correction"):
                return {
                    "action": "FEEDBACK",
                    "feedback_result": feedback_result,
                    "reasoning": f"Fallback: {feedback_result.get('primary_issue')} issue detected",
                    "confidence": 0.6,
                }
            else:
                return {
                    "action": "NEXT_QUESTION",
                    "feedback_result": None,
                    "reasoning": "Fallback: No correction needed",
                    "confidence": 0.6,
                }

        except Exception as e:
            logger.error(f"Fallback decision failed: {e}", exc_info=True)
            return {
                "action": "NEXT_QUESTION",
                "feedback_result": None,
                "reasoning": "Error in fallback decision, proceeding to next question",
                "confidence": 0.1,
            }
