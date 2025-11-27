"""
Scenario Schemas (에이전트2)
============================
시나리오 생성 API용 Pydantic 스키마.

역할:
    - 시나리오 생성 요청/응답 모델 정의
    - 시나리오 대화 턴 구조 정의
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class DifficultyLevel(str, Enum):
    """난이도 레벨"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ScenarioType(str, Enum):
    """시나리오 유형"""
    BUSINESS_EMAIL = "business_email"
    PHONE_CALL = "phone_call"
    MEETING = "meeting"
    PRESENTATION = "presentation"
    NEGOTIATION = "negotiation"
    CUSTOMER_SERVICE = "customer_service"
    INTERVIEW = "interview"
    GENERAL = "general"


class DialogueTurn(BaseModel):
    """대화 턴"""
    turn_number: int = Field(..., description="턴 번호")
    speaker: str = Field(..., description="화자 (AI/User)")
    text: str = Field(..., description="대화 내용")
    korean_hint: Optional[str] = Field(None, description="한국어 힌트")
    key_expressions: list[str] = Field(default_factory=list, description="핵심 표현")


class ScenarioGenerateRequest(BaseModel):
    """시나리오 생성 요청"""
    topic: str = Field(..., min_length=1, max_length=200, description="시나리오 주제")
    scenario_type: ScenarioType = Field(ScenarioType.GENERAL, description="시나리오 유형")
    difficulty: DifficultyLevel = Field(DifficultyLevel.INTERMEDIATE, description="난이도")
    num_turns: int = Field(6, ge=2, le=20, description="대화 턴 수")
    chapter_filter: Optional[str] = Field(None, description="특정 챕터로 제한")
    include_korean_hints: bool = Field(True, description="한국어 힌트 포함 여부")


class ScenarioResponse(BaseModel):
    """시나리오 생성 응답"""
    scenario_id: str = Field(..., description="시나리오 고유 ID")
    title: str = Field(..., description="시나리오 제목")
    description: str = Field(..., description="시나리오 설명")
    scenario_type: ScenarioType = Field(..., description="시나리오 유형")
    difficulty: DifficultyLevel = Field(..., description="난이도")

    # 상황 설정
    situation: str = Field(..., description="상황 설명")
    user_role: str = Field(..., description="사용자 역할")
    ai_role: str = Field(..., description="AI 역할")

    # 대화 내용
    dialogues: list[DialogueTurn] = Field(..., description="대화 턴 목록")

    # 학습 포인트
    key_expressions: list[str] = Field(..., description="핵심 표현 목록")
    vocabulary: list[str] = Field(default_factory=list, description="주요 어휘")
    grammar_points: list[str] = Field(default_factory=list, description="문법 포인트")

    # 메타데이터
    source_chapters: list[str] = Field(default_factory=list, description="참조 챕터 목록")


class ChapterListResponse(BaseModel):
    """챕터 목록 응답"""
    chapters: list[str] = Field(..., description="사용 가능한 챕터 목록")
    total_count: int = Field(..., description="총 챕터 수")
