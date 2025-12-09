"""
Service Interfaces (Protocols)
==============================
롤플레잉 서비스 계층의 인터페이스를 typing.Protocol로 정의합니다.
SOLID 원칙을 준수하기 위해 책임별로 인터페이스를 분리했습니다.

Protocol 장점:
- Python 3.8+ 표준 (추가 라이브러리 불필요)
- Duck Typing과 호환
- IDE 타입 체킹 지원
- 런타임 오버헤드 없음
"""

from typing import Protocol, Dict, List, Any, AsyncGenerator, Optional
from abc import abstractmethod


# ============================================
# LLM Service Interfaces (책임별 분리)
# ============================================

class ConversationAnalyzer(Protocol):
    """대화 분석 전용 인터페이스

    Slack 대화를 분석하여 상황 요약을 생성합니다.
    """

    @abstractmethod
    async def analyze_situation(
        self,
        messages: List[Dict[str, Any]],
        my_role: str,
        conversation_date: str
    ) -> str:
        """
        대화 상황 분석

        Args:
            messages: 사용자-AI 메시지 리스트
            my_role: 사용자의 역할 (예: 'Software Engineer')
            conversation_date: 대화 날짜 (예: '2025-01-01')

        Returns:
            상황 분석 결과 텍스트
        """
        ...


class ScenarioGenerator(Protocol):
    """시나리오 생성 전용 인터페이스

    상황 기반으로 학습 시나리오를 생성합니다.
    """

    @abstractmethod
    async def generate_scenario_from_prompt(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> Dict[str, Any]:
        """
        프롬프트 기반 시나리오 생성

        Args:
            situation: 대화 상황 분석 결과
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            {
                "opening_question": str,
                "questions": [str, str, str],  # 정확히 3개
                "context": str
            }
        """
        ...

    @abstractmethod
    async def generate_scenario_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 시나리오 생성"""
        ...


class QuestionGenerator(Protocol):
    """질문 생성 전용 인터페이스

    대화 히스토리 기반으로 다음 질문을 생성합니다.
    """

    @abstractmethod
    async def generate_next_question(
        self,
        situation: str,
        conversation_history: List[Dict[str, str]],
        role: str = "AI",
        user_text: str = None
    ) -> str:
        """
        다음 질문 생성

        Args:
            situation: 시나리오 상황
            conversation_history: 이전 대화 히스토리
            role: AI의 역할 (기본값: "AI")
            user_text: 사용자의 최근 메시지 (None이면 conversation_history에서 자동 추출)

        Returns:
            생성된 질문 텍스트
        """
        ...

    @abstractmethod
    async def generate_followup_question(self, prompt: str) -> str:
        """
        Follow-up 질문 생성

        Args:
            prompt: 질문 생성 프롬프트

        Returns:
            생성된 follow-up 질문
        """
        ...

    @abstractmethod
    async def generate_followup_question_stream(
        self,
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 Follow-up 질문 생성"""
        ...


class AIResponseGenerator(Protocol):
    """AI 응답 생성 전용 인터페이스

    시나리오 기반으로 AI의 응답을 생성합니다.
    """

    @abstractmethod
    async def generate_ai_response(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        AI 응답 생성

        Args:
            situation: 시나리오 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할
            conversation_history: 이전 대화 히스토리

        Returns:
            생성된 AI 응답
        """
        ...

    @abstractmethod
    async def generate_ai_response_streaming(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        conversation_history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """스트리밍 기반 AI 응답 생성"""
        ...


# ============================================
# Feedback Service Interfaces (책임별 분리)
# ============================================

class PronunciationEvaluator(Protocol):
    """발음 평가 전용 인터페이스

    Azure Speech API를 사용하여 발음을 평가합니다.
    """

    @abstractmethod
    async def evaluate_pronunciation(
        self,
        audio_data: Optional[bytes],
        reference_text: str
    ) -> Dict[str, Any]:
        """
        발음 평가

        Args:
            audio_data: PCM 형식 음성 데이터
            reference_text: 참조 텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str,
                "accuracy_score": int,
                "fluency_score": int,
                "completeness_score": int
            }
        """
        ...


class GrammarEvaluator(Protocol):
    """문법 평가 전용 인터페이스

    LLM을 사용하여 문법을 평가합니다.
    """

    @abstractmethod
    async def evaluate_grammar(self, user_text: str) -> Dict[str, Any]:
        """
        문법 평가

        Args:
            user_text: 사용자 발화 텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str
            }
        """
        ...


class RelevanceEvaluator(Protocol):
    """맥락 평가 전용 인터페이스

    대화 맥락과의 관련성을 평가합니다.
    """

    @abstractmethod
    async def evaluate_relevance(
        self,
        user_text: str,
        conversation_history: list,
        scenario_context: dict
    ) -> Dict[str, Any]:
        """
        맥락 평가

        Args:
            user_text: 사용자 발화 텍스트
            conversation_history: 대화 히스토리
            scenario_context: 시나리오 컨텍스트

        Returns:
            {
                "score": int (0-100),
                "feedback": str
            }
        """
        ...


class FeedbackJudge(Protocol):
    """피드백 판단 전용 인터페이스

    평가 결과를 바탕으로 교정 필요 여부를 판단합니다.
    """

    @abstractmethod
    def judge_correction_needed(
        self,
        pronunciation_score: float,
        grammar_score: float,
        relevance_score: float,
        retry_count: int
    ) -> tuple[bool, str]:
        """
        교정 필요 여부 판단

        Args:
            pronunciation_score: 발음 점수 (0-100)
            grammar_score: 문법 점수 (0-100)
            relevance_score: 맥락 점수 (0-100)
            retry_count: 현재 재시도 횟수

        Returns:
            (needs_correction: bool, primary_issue: str)
            primary_issue: "pronunciation", "grammar", "relevance", "max_retries_exceeded", "none"
        """
        ...


class FeedbackOrchestrator(Protocol):
    """피드백 조율 전용 인터페이스

    전체 평가 프로세스를 조율합니다.
    """

    @abstractmethod
    async def evaluate_response_fast(
        self,
        user_text: str,
        audio_data: Optional[bytes],
        conversation_history: list,
        scenario_context: dict,
        retry_count: int
    ) -> Dict[str, Any]:
        """
        빠른 응답 평가 (병렬 처리)

        Args:
            user_text: 사용자 STT 결과 텍스트
            audio_data: 사용자 오디오 데이터 (선택사항)
            conversation_history: 대화 히스토리
            scenario_context: 시나리오 컨텍스트
            retry_count: 현재 질문 재시도 횟수

        Returns:
            {
                "needs_correction": bool,
                "primary_issue": str,
                "scores": {
                    "pronunciation_score": int,
                    "grammar_score": int,
                    "relevance_score": int,
                    "overall_score": int
                },
                "feedback_text": str,
                "retry_count": int
            }
        """
        ...


class FeedbackDecisionAgent(Protocol):
    """피드백/질문 결정 ReAct 에이전트 인터페이스

    평가 결과를 기반으로 피드백 vs 다음 질문 판단을 ReAct 패턴으로 수행합니다.
    """

    @abstractmethod
    async def decide_feedback_or_question(
        self,
        session_state: Any,
        user_text: str,
        audio_data: Optional[bytes],
        retry_count: int
    ) -> Dict[str, Any]:
        """
        ReAct 에이전트를 통한 피드백/질문 판단

        Args:
            session_state: 세션 상태 (대화 히스토리, 역할 등)
            user_text: 사용자 발화 텍스트
            audio_data: 사용자 오디오 데이터 (선택사항)
            retry_count: 현재 질문 재시도 횟수

        Returns:
            {
                "action": "FEEDBACK" | "NEXT_QUESTION",
                "feedback_result": {
                    "needs_correction": bool,
                    "primary_issue": str,
                    "scores": {
                        "pronunciation_score": int | None,
                        "grammar_score": int | None,
                        "relevance_score": int | None,
                        "overall_score": int | None
                    },
                    "feedback_text": str,
                    "retry_count": int
                } | None,
                "reasoning": str,
                "confidence": float (0-1)
            }
        """
        ...


# ============================================
# Repository Interfaces (데이터 접근 계층)
# ============================================

class SessionRepository(Protocol):
    """세션 저장소 인터페이스

    Redis 기반 세션 CRUD 작업을 담당합니다.
    """

    @abstractmethod
    async def save_session(
        self,
        session_id: str,
        user_id: int,
        expires_at: Optional[Any],
        interaction_mode: str
    ) -> None:
        """
        세션 저장

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            expires_at: 만료 시간
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """
        세션 삭제

        Args:
            session_id: 세션 ID
        """
        ...


class ScenarioRepository(Protocol):
    """시나리오 저장소 인터페이스

    MySQL 기반 시나리오 READ-ONLY 작업을 담당합니다.
    """

    @abstractmethod
    async def get_scenario(
        self,
        scenario_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        시나리오 조회 (READ-ONLY)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (권한 확인용)

        Returns:
            {
                "id": int,
                "title": str,
                "description": str,
                "my_role": str,
                "ai_role": str,
                "questions": [str, str, str],
                ...
            }
        """
        ...

    @abstractmethod
    async def get_user_scenarios(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        사용자의 시나리오 목록 조회

        Args:
            user_id: 사용자 ID
            limit: 조회 개수 제한

        Returns:
            시나리오 리스트
        """
        ...


# ============================================
# STT Interfaces
# ============================================

class STTEngine(Protocol):
    """STT 엔진 인터페이스"""

    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """
        오디오를 텍스트로 변환

        Args:
            audio_data: PCM 형식 음성 데이터

        Returns:
            인식된 텍스트
        """
        ...


# ============================================
# Audio Processing Interfaces
# ============================================

class AudioProcessor(Protocol):
    """오디오 처리 인터페이스"""

    @abstractmethod
    def pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """
        PCM 형식을 WAV로 변환

        Args:
            pcm_data: PCM 형식 데이터

        Returns:
            WAV 형식 데이터
        """
        ...

    @abstractmethod
    def apply_agc(self, audio_data: bytes) -> bytes:
        """
        자동 게인 조절 적용

        Args:
            audio_data: 오디오 데이터

        Returns:
            AGC 적용된 오디오 데이터
        """
        ...


# ============================================
# Message Summarization Interfaces
# ============================================

class MessageSummarizer(Protocol):
    """메시지 요약 전용 인터페이스

    메시지 리스트를 요약합니다.
    """

    @abstractmethod
    async def summarize_messages(
        self,
        messages: List[str],
        perspective: str
    ) -> str:
        """
        메시지 요약

        Args:
            messages: 요약할 메시지 리스트
            perspective: 관점 ("user" 또는 "counterpart")

        Returns:
            요약된 텍스트
        """
        ...


# ============================================
# Fixed Question Builder Interfaces
# ============================================

class FixedQuestionBuilder(Protocol):
    """고정 질문 생성 전용 인터페이스

    메시지 요약을 기반으로 고정 질문을 생성합니다.
    """

    @abstractmethod
    async def build_fixed_questions(
        self,
        user_summary: str,
        counterpart_summary: str
    ) -> List[str]:
        """
        고정 질문 생성

        Args:
            user_summary: 사용자 메시지 요약
            counterpart_summary: 상대방 메시지 요약

        Returns:
            정확히 3개의 질문 리스트
        """
        ...


# ============================================
# Scenario Enhancement Interfaces
# ============================================

class ScenarioEnhancer(Protocol):
    """시나리오 강화 전용 인터페이스

    사용자 입력을 구체화하고 제목 생성, 질문 생성합니다.
    """

    @abstractmethod
    async def enhance_situation(
        self,
        situation: str,
        my_role: str,
        ai_role: str,
        context: List[Dict[str, Any]] = None
    ) -> str:
        """
        상황 구체화

        Args:
            situation: 사용자 입력 상황
            my_role: 사용자의 역할
            ai_role: AI의 역할
            context: 과거 시나리오 컨텍스트 (선택사항)

        Returns:
            구체화된 상황 텍스트
        """
        ...

    @abstractmethod
    async def generate_title(
        self,
        situation: str,
        ai_role: str,
        my_role: str
    ) -> str:
        """
        시나리오 제목 생성

        Args:
            situation: 상황 텍스트
            ai_role: AI의 역할
            my_role: 사용자의 역할

        Returns:
            생성된 제목
        """
        ...

    @abstractmethod
    async def generate_prompt_questions(
        self,
        situation: str,
        my_role: str,
        ai_role: str
    ) -> List[str]:
        """
        프롬프트 기반 고정 질문 생성

        Args:
            situation: 상황 텍스트
            my_role: 사용자의 역할
            ai_role: AI의 역할

        Returns:
            정확히 3개의 질문 리스트
        """
        ...
