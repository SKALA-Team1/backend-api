"""
Roleplaying Schemas
===================
시나리오 관련 API 요청/응답에 사용되는 Pydantic 스키마 정의 모듈.

역할:
    - 데이터 유효성 검증 및 직렬화
    - Models.py의 ORM 객체를 안전하게 API 응답용 형태로 변환

주요 스키마:
    - ScenarioCreateSchema / ScenarioResponseSchema
    - MessageSchema / TurnSchema
    - ScenarioStatusSchema
    - Slack 시나리오 생성 관련 스키마

의존성:
    - Models.py
"""

from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


# =====================================================
# Slack 시나리오 생성 관련 스키마
# =====================================================

class SlackMessageDto(BaseModel):
    """Slack 메시지 DTO"""
    timestamp: datetime = Field(..., description="메시지 전송 시각 (ISO 8601)")
    senderName: str = Field(..., description="메시지 발신자 이름")
    text: str = Field(..., description="메시지 내용")
    myMessage: bool | None = Field(
        default=False,
        description="해당 메시지가 사용자 본인의 발화인지 여부"
    )


class MessageRole(BaseModel):
    """LLM 처리를 위한 메시지 역할 정보"""
    content: str = Field(..., description="메시지 텍스트")
    sender: str = Field(..., description="발화자 이름")
    mine: bool = Field(default=False, description="사용자 본인 발화 여부")


class AnalysisRequestDto(BaseModel):
    """Slack 대화 분석 요청 DTO (Spring 2 → FastAPI)"""
    userId: int = Field(..., description="사용자 ID")
    myRole: str = Field(..., description="사용자의 직무 역할 (DB에서 제공, LLM 분석 불필요)")
    conversationDate: date = Field(..., description="대화 날짜 (LocalDate)")
    messages: List[SlackMessageDto] = Field(..., description="해당 날짜의 Slack 메시지 목록")
    aiRoles: List[str] = Field(..., description="시나리오 생성할 AI 역할 목록")


class SubjectInfoDto(BaseModel):
    """대화 주제 정보 DTO"""
    myRole: str = Field(..., description="대화에서 유추한 사용자 역할")
    situation: str = Field(..., description="대화 주제 및 상황 (1-2문장)")
    conversationDate: date = Field(..., description="대화 날짜")
    messageCount: int = Field(..., description="메시지 개수")


class ScenarioInfoDto(BaseModel):
    """생성된 시나리오 정보 DTO"""
    aiRole: str = Field(..., description="AI 역할 (Project Manager, Tech Lead, QA Engineer)")
    topicType: str = Field(..., description="토픽 타입 (overview, detail)")
    title: str = Field(..., max_length=200, description="시나리오 제목")
    fixedQuestions: List[str] = Field(..., min_items=3, max_items=3, description="고정 질문 목록 (3개)")


class AnalysisResultDto(BaseModel):
    """Slack 대화 분석 결과 DTO (FastAPI → Spring 2)"""
    subject: SubjectInfoDto = Field(..., description="대화 주제 정보")
    scenarios: List[ScenarioInfoDto] = Field(..., min_items=4, max_items=4, description="생성된 시나리오 목록 (4개 - overview, project manager detail, tech lead detail, qa engineer detail)")


# =====================================================
# 롤플레잉 세션 생성 관련 스키마
# =====================================================

class SessionCreateRequest(BaseModel):
    """세션 생성 요청 DTO"""
    userId: int = Field(..., description="사용자 ID", gt=0)
    scenarioId: int = Field(..., description="시나리오 ID (DB에 저장된 시나리오)", gt=0)
    sessionId: str | None = Field(
        default=None,
        description="기존에 발급된 세션 ID (UUID 문자열). 없으면 FastAPI가 UUID를 생성"
    )


class ScenarioDetail(BaseModel):
    """세션 생성 응답에 포함되는 시나리오 상세 정보"""
    scenarioId: int = Field(..., description="시나리오 ID")
    subjectId: int = Field(..., description="주제 ID")
    myRole: str = Field(..., description="사용자 역할")
    aiRole: str = Field(..., description="AI 역할")
    title: str = Field(..., description="시나리오 제목")
    topicType: str = Field(..., description="토픽 타입 (overview, detail)")
    fixedQuestions: List[str] = Field(..., description="고정 질문 3개", min_length=3, max_length=3)


class SessionCreateResponse(BaseModel):
    """세션 생성 응답 DTO"""
    session_id: str = Field(..., description="생성된 세션 ID")
    ws_url: str = Field(..., description="WebSocket 연결 URL")
    scenario: ScenarioDetail = Field(..., description="선택된 시나리오 정보")
    expires_at: datetime = Field(..., description="세션 만료 시각")
