"""
WebSocket 메시지 모델
==================
실시간 롤플레잉 WebSocket 통신을 위한 Pydantic 모델 정의.

메시지 타입:
- 인바운드 (Client → FastAPI): INIT, AUDIO_CHUNK, UTTERANCE_END, END_SESSION
- 아웃바운드 (FastAPI → Client): ACK, AI_TEXT, STT_PARTIAL, STT_FINAL, UTTERANCE_SAVED, AI_TYPING, SESSION_ENDED, ERROR

중요:
- 모든 대화는 음성으로만 진행됨 (텍스트 입력 없음)
- 고정 질문은 정확히 3개 (턴 1, 5, 10에 사용)
  - fixedQuestions[0]: 턴 1 - 대화 시작
  - fixedQuestions[1]: 턴 5 - 대화 흐름 전환
  - fixedQuestions[2]: 턴 10 - 대화 마무리
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
    aiRole: str = Field(..., description="AI 역할 (Tech Lead, QA Engineer 등)", min_length=1)
    fixedQuestions: List[str] = Field(
        ...,
        description="고정 질문 3개 (턴 1, 5, 10에 사용)",
        min_length=3,
        max_length=3
    )

    @field_validator('fixedQuestions')
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
    - 턴 1, 5, 10: 고정 질문 사용
    - 나머지 턴: LLM이 동적으로 생성
    """
    type: Literal["AI_TEXT"] = "AI_TEXT"
    text: str = Field(..., description="AI 응답 텍스트", min_length=1)
    is_fixed_question: bool = Field(
        default=False,
        description="고정 질문 여부 (턴 1, 5, 10)"
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
    """
    type: Literal["STT_FINAL"] = "STT_FINAL"
    text: str = Field(..., description="최종 STT 결과", min_length=1)


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


class SessionEndedMessage(BaseModel):
    """
    세션 종료 메시지

    세션이 종료되었음을 알림.
    """
    type: Literal["SESSION_ENDED"] = "SESSION_ENDED"
    reason: Literal["user_end", "timeout", "disconnected", "error"] = Field(
        ...,
        description="종료 사유"
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
InboundMessage = (
    InitMessage
    | UtteranceEndMessage
    | EndSessionMessage
)

# 아웃바운드 메시지 유니온 타입 (타입 힌트용)
OutboundMessage = (
    AckMessage
    | AiTextMessage
    | SttPartialMessage
    | SttFinalMessage
    | UtteranceSavedMessage
    | AiTypingMessage
    | SessionEndedMessage
    | ErrorMessage
)


# ========================================
# 고정 질문 턴 상수
# ========================================

FIXED_QUESTION_TURNS = {
    1: 0,   # 턴 1 → fixedQuestions[0] (대화 시작)
    5: 1,   # 턴 5 → fixedQuestions[1] (대화 흐름 전환)
    10: 2   # 턴 10 → fixedQuestions[2] (대화 마무리)
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