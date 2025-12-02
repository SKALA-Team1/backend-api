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
    user_id: int = Field(..., description="사용자 ID (Spring DB 저장용)")
    topic: str = Field(..., min_length=1, max_length=200, description="시나리오 주제")
    scenario_type: ScenarioType = Field(ScenarioType.GENERAL, description="시나리오 유형")
    difficulty: DifficultyLevel = Field(DifficultyLevel.INTERMEDIATE, description="난이도")
    num_turns: int = Field(10, ge=2, le=30, description="대화 턴 수 (AI 5턴 + User 5턴 = 총 10턴)")
    chapter_filter: str = Field(..., description="특정 챕터 선택 (필수) - /scenario/chapters API로 챕터 목록 조회")
    include_korean_hints: bool = Field(True, description="한국어 힌트 포함 여부")
    save_to_db: bool = Field(True, description="DB에 저장 여부")


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

    # DB 저장 정보
    db_scenario_id: Optional[int] = Field(None, description="DB에 저장된 시나리오 ID")
    saved_to_db: bool = Field(False, description="DB 저장 성공 여부")


class UnitChapters(BaseModel):
    """Unit별 챕터"""
    unit_number: int = Field(..., description="Unit 번호 (1-4)")
    unit_name: str = Field(..., description="Unit 이름")
    chapters: list[str] = Field(..., description="해당 Unit의 챕터 목록")


class ChapterListResponse(BaseModel):
    """챕터 목록 응답"""
    units: list[UnitChapters] = Field(..., description="Unit별 챕터 목록")
    all_chapters: list[str] = Field(..., description="전체 챕터 목록 (하위 호환)")
    total_count: int = Field(..., description="총 챕터 수")
