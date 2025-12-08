"""
IT Explanation Pydantic Models
===============================
Request/Response 스키마 정의
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# ========================================
# Request Models
# ========================================

class PracticeSessionCreate(BaseModel):
    """설명 연습 세션 생성 요청"""
    user_id: int = Field(..., description="사용자 ID (Gateway에서 JWT로 추출)")
    question_id: int = Field(..., description="질문 ID")
    user_answer: str = Field(..., description="사용자 답변 (텍스트)")
    session_type: str = Field(default="TEXT", description="세션 타입 (TEXT or VOICE)")
    audio_url: Optional[str] = Field(None, description="음성 답변 S3 URL (선택)")


class ChatbotMessage(BaseModel):
    """챗봇 메시지 요청"""
    user_message: str = Field(..., description="사용자 질문")
    conversation_history: List[Dict[str, str]] = Field(
        default=[],
        description="대화 히스토리 [{'role': 'user', 'content': '...'}]"
    )


# ========================================
# Response Models
# ========================================

class EvaluationScores(BaseModel):
    """평가 점수"""
    clarity_score: int = Field(..., ge=0, le=100, description="명확성 점수 (0-100)")
    technical_accuracy_score: int = Field(..., ge=0, le=100, description="기술적 정확성 점수 (0-100)")
    terminology_score: int = Field(..., ge=0, le=100, description="전문용어 사용 점수 (0-100)")
    overall_score: int = Field(..., ge=0, le=100, description="종합 점수 (0-100)")


class PracticeSessionResponse(BaseModel):
    """설명 연습 세션 응답"""
    session_id: int = Field(..., description="세션 ID")
    scores: EvaluationScores = Field(..., description="평가 점수")
    feedback_en: str = Field(..., description="피드백 (영문)")
    feedback_ko: Optional[str] = Field(None, description="피드백 (한글)")
    model_answer: str = Field(..., description="모범 답안")


class ChatbotResponse(BaseModel):
    """챗봇 응답"""
    bot_response: str = Field(..., description="챗봇 응답 텍스트")
    conversation_id: Optional[int] = Field(None, description="대화 ID (DB 저장 시)")


class QuestionResponse(BaseModel):
    """질문 응답"""
    question_id: int = Field(..., description="질문 ID")
    question_text: str = Field(..., description="질문 내용 (영문)")
    question_text_ko: Optional[str] = Field(None, description="질문 내용 (한글)")
    category: str = Field(..., description="카테고리 (예: Architecture, Database)")
    difficulty: str = Field(..., description="난이도 (EASY, MEDIUM, HARD)")


class StatsResponse(BaseModel):
    """통계 응답"""
    total_completed: int = Field(..., description="총 완료 개수")
    average_score: float = Field(..., description="평균 점수")
    category_breakdown: Dict[str, Dict[str, float]] = Field(
        ...,
        description="카테고리별 통계 {'Architecture': {'count': 10, 'avg_score': 85}}"
    )
