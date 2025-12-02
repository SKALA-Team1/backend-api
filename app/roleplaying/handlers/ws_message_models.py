"""
WebSocket 메시지 모델 (Pydantic 정의)
=====================================
실시간 롤플레잉 WebSocket 통신을 위한 메시지 스키마 정의

메시지 타입:

📥 인바운드 (Client → FastAPI):
    - INIT: 세션 초기화 (시나리오/역할 설정)
    - AUDIO_CHUNK: 오디오 바이너리 청크 (WAV, 16kHz, 16-bit, mono)
    - UTTERANCE_END: 발화 완료 신호
    - USER_TEXT: 텍스트 입력 (테스트용)
    - END_SESSION: 세션 종료 요청

📤 아웃바운드 (FastAPI → Client):
    - ACK: 메시지 수신 확인
    - AI_TEXT: AI 응답 텍스트
    - AI_TEXT_STREAMING: AI 응답 스트리밍 (청크 단위)
    - STT_PARTIAL: STT 부분 결과
    - STT_FINAL: STT 최종 결과
    - UTTERANCE_SAVED: 발화 저장 완료
    - AI_TYPING: AI 응답 생성 중 (로딩)
    - FEEDBACK: 피드백 점수 (발음, 문법, 맥락 0-100)
    - FEEDBACK_STREAMING: 피드백 텍스트 스트리밍
    - RETRY_REQUIRED: 재시도 요청
    - SESSION_ENDED: 세션 종료 완료
    - ERROR: 오류 메시지

🔄 대화 흐름:

    음성 모드:
        1. INIT → 세션 초기화, 첫 질문 전송 (AI_TEXT)
        2. AUDIO_CHUNK (반복) → 오디오 스트리밍
        3. UTTERANCE_END → STT 처리
        4. STT_PARTIAL (0회 이상) → 중간 결과
        5. STT_FINAL → 최종 STT 결과
        6. UTTERANCE_SAVED → DB 저장 완료
        7. AI_TYPING → 응답 생성 중
        8. AI_TEXT 또는 AI_TEXT_STREAMING → AI 응답
        9. FEEDBACK + FEEDBACK_STREAMING → 피드백
        10. RETRY_REQUIRED (옵션) 또는 다음 턴으로...

    텍스트 모드:
        1. INIT → 세션 초기화
        2. USER_TEXT → 텍스트 입력
        3. (STT 생략)
        4. AI_TYPING → 응답 생성 중
        5. AI_TEXT 또는 AI_TEXT_STREAMING → AI 응답
        6. FEEDBACK (발음 점수 0) + FEEDBACK_STREAMING

🔐 고정 질문 (정확히 3개):
    - 턴 1 (AI 턴 1): 대화 시작 (fixedQuestions[0])
    - 턴 4 (AI 턴 4): 대화 흐름 전환 (fixedQuestions[1])
    - 턴 7 (AI 턴 7): 대화 마무리 (fixedQuestions[2])
    - 그 외: LLM이 동적으로 생성

⚙️ 재시도 메커니즘:
    - 교정 필요시 RETRY_REQUIRED 전송
    - 최대 3회까지 같은 질문 반복 가능
    - 3회 초과시 다음 질문으로 진행
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ========================================
# 인바운드 메시지 (Client → FastAPI)
# ========================================


class InitMessage(BaseModel):
    """
    세션 초기화 메시지

    클라이언트가 WebSocket 연결 후 첫 번째로 전송하는 메시지.
    시나리오 컨텍스트를 설정함.
    """

    type: Literal["INIT"] = "INIT"
    userId: int = Field(..., description="사용자 ID", gt=0)
    subjectId: int = Field(..., description="시나리오 주제 ID", gt=0)
    myRole: str = Field(..., description="사용자 직무 역할", min_length=1)
    aiRole: str = Field(
        ..., description="AI 역할 (Tech Lead, QA Engineer 등)", min_length=1
    )
    fixedQuestions: List[str] = Field(
        ...,
        description="고정 질문 3개 (턴 1, 5, 10에 사용)",
        min_length=3,
        max_length=3,
    )

    @field_validator("fixedQuestions")
    @classmethod
    def validate_fixed_questions(cls, v: List[str]) -> List[str]:
        """고정 질문은 정확히 3개여야 함"""
        if len(v) != 3:
            raise ValueError("fixedQuestions must contain exactly 3 questions")

        # 각 질문이 비어있지 않은지 확인
        for i, question in enumerate(v):
            if not question or not question.strip():
                raise ValueError(f"fixedQuestions[{i}] cannot be empty")

        return [q.strip() for q in v]


class AudioChunkMessage(BaseModel):
    """
    오디오 청크 메시지

    실제로는 binary data로 전송되므로 이 모델은 문서화 목적.
    WebSocket에서는 bytes로 수신됨.

    포맷: WAV, 16kHz, 16-bit, mono
    청크 크기: 1024 bytes (약 64ms @ 16kHz)
    """

    type: Literal["AUDIO_CHUNK"] = "AUDIO_CHUNK"
    # chunk: bytes  # WebSocket에서 직접 binary로 처리


class UtteranceEndMessage(BaseModel):
    """
    발화 종료 메시지

    사용자가 말을 끝냈음을 알림.
    FastAPI는 누적된 오디오로 최종 STT 수행.
    """

    type: Literal["UTTERANCE_END"] = "UTTERANCE_END"


class UserTextMessage(BaseModel):
    """
    사용자 텍스트 메시지 (테스트용)

    STT 없이 텍스트로 직접 발화를 전송.
    오디오 녹음 없이 텍스트만으로 롤플레잉 테스트 가능.

    주의:
    - 프로덕션에서는 음성 기반(AUDIO_CHUNK) 사용 권장
    - 테스트 및 디버깅 목적으로만 사용
    """

    type: Literal["USER_TEXT"] = "USER_TEXT"
    text: str = Field(..., description="사용자 발화 텍스트", min_length=1)


class EndSessionMessage(BaseModel):
    """
    세션 종료 요청 메시지

    사용자가 명시적으로 세션을 종료하고자 함.
    """

    type: Literal["END_SESSION"] = "END_SESSION"


# ========================================
# 아웃바운드 메시지 (FastAPI → Client)
# ========================================


class AckMessage(BaseModel):
    """
    수신 확인 메시지

    메시지를 정상적으로 수신했음을 알림.
    """

    type: Literal["ACK"] = "ACK"
    message: str = Field(default="received", description="확인 메시지")


class AiTextMessage(BaseModel):
    """
    AI 응답 텍스트 메시지

    AI 튜터가 생성한 질문 또는 응답.
    클라이언트는 이를 TTS로 변환하여 재생.

    질문 타입:
    - 턴 1, 4, 7: 고정 질문 사용
    - 나머지 턴: LLM이 동적으로 생성
    """

    type: Literal["AI_TEXT"] = "AI_TEXT"
    text: str = Field(..., description="AI 응답 텍스트", min_length=1)
    is_fixed_question: bool = Field(
        default=False, description="고정 질문 여부 (턴 1, 4, 7)"
    )


class AiTextStreamingMessage(BaseModel):
    """
    AI 응답 텍스트 스트리밍 메시지

    AI 응답을 청크 단위로 실시간 전송.
    답변이 한 글자씩 또는 한 단어씩 나타남.

    사용:
    - 동적 질문 생성 중 청크 전송
    - 고정 질문은 한 번에 전송 (is_fixed_question=True일 때)
    """

    type: Literal["AI_TEXT_STREAMING"] = "AI_TEXT_STREAMING"
    chunk: str = Field(..., description="스트리밍 청크 (한 단어 또는 여러 단어)")
    is_fixed_question: bool = Field(
        default=False, description="고정 질문 여부 (턴 1, 4, 7)"
    )


class SttPartialMessage(BaseModel):
    """
    STT 부분 결과 메시지

    오디오 스트리밍 중 중간 STT 결과.
    실시간으로 화면에 표시됨.
    """

    type: Literal["STT_PARTIAL"] = "STT_PARTIAL"
    text: str = Field(..., description="부분 STT 결과")


class SttFinalMessage(BaseModel):
    """
    STT 최종 결과 메시지

    발화 종료 후 전체 오디오에 대한 최종 STT 결과.
    STT 실패 시 빈 문자열이 전송될 수 있음.
    """

    type: Literal["STT_FINAL"] = "STT_FINAL"
    text: str = Field(default="", description="최종 STT 결과 (STT 실패 시 빈 문자열)")


class UtteranceSavedMessage(BaseModel):
    """
    발화 저장 완료 메시지

    Spring 2에 오디오 + STT 텍스트 저장 완료.
    """

    type: Literal["UTTERANCE_SAVED"] = "UTTERANCE_SAVED"
    index: int = Field(..., description="발화 인덱스 (0부터 시작)", ge=0)


class AiTypingMessage(BaseModel):
    """
    AI 응답 생성 중 메시지

    AI가 응답을 생성하는 동안 로딩 표시.
    """

    type: Literal["AI_TYPING"] = "AI_TYPING"


class FeedbackMessage(BaseModel):
    """
    피드백 점수 전송 메시지

    사용자 응답 평가 후 발음, 문법, 맥락 적절성 점수 전송.
    """

    type: Literal["FEEDBACK"] = "FEEDBACK"
    pronunciation_score: int = Field(..., ge=0, le=100, description="발음 점수 (0-100)")
    grammar_score: int = Field(..., ge=0, le=100, description="문법 점수 (0-100)")
    relevance_score: int = Field(..., ge=0, le=100, description="맥락 적절성 점수 (0-100)")
    overall_score: int = Field(..., ge=0, le=100, description="종합 점수 (평균)")


class FeedbackStreamingMessage(BaseModel):
    """
    피드백 텍스트 스트리밍 메시지

    교정 제안을 청크 단위로 실시간 전송.
    """

    type: Literal["FEEDBACK_STREAMING"] = "FEEDBACK_STREAMING"
    chunk: str = Field(..., description="피드백 텍스트 청크")


class RetryRequiredMessage(BaseModel):
    """
    재시도 요청 메시지

    교정이 필요하여 같은 질문 재시도 요청.
    """

    type: Literal["RETRY_REQUIRED"] = "RETRY_REQUIRED"
    reason: str = Field(..., description="재시도 이유 (pronunciation, grammar, relevance 등)")
    retry_count: int = Field(..., ge=1, description="현재 재시도 횟수")
    max_retries: int = Field(..., ge=1, description="최대 재시도 횟수")


class SessionEndedMessage(BaseModel):
    """
    세션 종료 메시지

    세션이 종료되었음을 알림.
    """

    type: Literal["SESSION_ENDED"] = "SESSION_ENDED"
    reason: Literal["user_end", "timeout", "disconnected", "error", "turn_limit"] = Field(
        ..., description="종료 사유"
    )


class ErrorMessage(BaseModel):
    """
    에러 메시지

    처리 중 오류 발생 시 클라이언트에 알림.
    """

    type: Literal["ERROR"] = "ERROR"
    message: str = Field(..., description="에러 메시지")
    code: Optional[str] = Field(None, description="에러 코드 (선택)")


# ========================================
# 유틸리티 타입
# ========================================

# 인바운드 메시지 유니온 타입 (타입 힌트용)
InboundMessage = InitMessage | UtteranceEndMessage | UserTextMessage | EndSessionMessage

# 아웃바운드 메시지 유니온 타입 (타입 힌트용)
OutboundMessage = (
    AckMessage
    | AiTextMessage
    | AiTextStreamingMessage
    | SttPartialMessage
    | SttFinalMessage
    | UtteranceSavedMessage
    | AiTypingMessage
    | FeedbackMessage
    | FeedbackStreamingMessage
    | RetryRequiredMessage
    | SessionEndedMessage
    | ErrorMessage
)


# ========================================
# 고정 질문 턴 상수
# ========================================

FIXED_QUESTION_TURNS = {
    1: 0,  # 턴 1 → fixedQuestions[0] (대화 시작)
    4: 1,  # 턴 4 → fixedQuestions[1] (대화 중반)
    7: 2,  # 턴 7 → fixedQuestions[2] (대화 마무리)
}


def get_fixed_question_index(ai_turn: int) -> Optional[int]:
    """
    AI 턴 번호에 따라 고정 질문 인덱스 반환

    Args:
        ai_turn: AI의 현재 턴 번호 (1부터 시작)

    Returns:
        고정 질문 인덱스 (0-2) 또는 None (동적 질문 생성)

    Examples:
        >>> get_fixed_question_index(1)
        0  # fixedQuestions[0] 사용
        >>> get_fixed_question_index(5)
        1  # fixedQuestions[1] 사용
        >>> get_fixed_question_index(3)
        None  # LLM 동적 생성
    """
    return FIXED_QUESTION_TURNS.get(ai_turn)
