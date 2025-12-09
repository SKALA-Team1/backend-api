"""
IT Explanation Practice Router
===============================
IT 용어 설명 연습 REST API

Endpoints:
- GET /it-explanation/questions/random - 랜덤 질문 조회
- POST /it-explanation/sessions - 설명 연습 세션 생성 및 평가
"""

import logging
from fastapi import APIRouter, HTTPException

from app.it_explanation.models.schemas import (
    PracticeSessionCreate,
    PracticeSessionResponse,
    EvaluationScores,
    QuestionResponse
)
from app.it_explanation.services.evaluation_service import EvaluationService
from app.integrations.clients.spring2_client import spring2_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/it-explanation", tags=["it-explanation"])

# 서비스 초기화
evaluation_service = EvaluationService()


@router.get("/questions/random", response_model=QuestionResponse)
async def get_random_question():
    """
    랜덤 IT 질문 조회

    Returns:
        QuestionResponse: 랜덤 질문 데이터
    """
    try:
        logger.info("🎲 [API] GET /it-explanation/questions/random")

        question = await spring2_client.get_random_it_question()

        if not question:
            raise HTTPException(status_code=404, detail="No questions available")

        return QuestionResponse(
            question_id=question["question_id"],
            question_text=question["question_text"],
            question_text_ko=question.get("question_text_ko"),
            category=question["category"],
            difficulty=question["difficulty"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get random question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions", response_model=PracticeSessionResponse)
async def create_practice_session(request: PracticeSessionCreate):
    """
    설명 연습 세션 생성 및 평가

    사용자의 답변을 평가하고 점수와 피드백을 반환합니다.

    Args:
        request: PracticeSessionCreate
            - question_id: 질문 ID
            - user_answer: 사용자 답변
            - session_type: TEXT or VOICE

    Returns:
        PracticeSessionResponse: 평가 결과 (점수 + 피드백 + 모범 답안)
    """
    try:
        logger.info(f"📝 [API] POST /it-explanation/sessions (question_id={request.question_id})")

        # 1. 질문 조회
        question = await spring2_client.get_it_question_by_id(request.question_id)

        if not question:
            raise HTTPException(status_code=404, detail=f"Question {request.question_id} not found")

        # 2. 답변 평가
        evaluation = await evaluation_service.evaluate_answer(
            question_text=question["question_text"],
            user_answer=request.user_answer,
            key_keywords=question["key_keywords"],
            model_answer=question["model_answer"]
        )

        if not evaluation:
            raise HTTPException(status_code=500, detail="Evaluation failed")

        # 3. Spring 2에 세션 저장
        session_id = await spring2_client.save_practice_session(
            user_id=request.user_id,
            question_id=request.question_id,
            user_answer=request.user_answer,
            clarity_score=evaluation["clarity_score"],
            technical_accuracy_score=evaluation["technical_accuracy_score"],
            terminology_score=evaluation["terminology_score"],
            overall_score=evaluation["overall_score"],
            feedback_en=evaluation["feedback"],
            feedback_ko=None,  # TODO: 번역 서비스 추가
            session_type=request.session_type,
            audio_url=getattr(request, 'audio_url', None)
        )

        if not session_id:
            logger.error("Failed to save session to database.")
            raise HTTPException(status_code=500, detail="Failed to create a practice session.")

        return PracticeSessionResponse(
            session_id=session_id,
            scores=EvaluationScores(
                clarity_score=evaluation["clarity_score"],
                technical_accuracy_score=evaluation["technical_accuracy_score"],
                terminology_score=evaluation["terminology_score"],
                overall_score=evaluation["overall_score"]
            ),
            feedback_en=evaluation["feedback"],
            feedback_ko=None,  # TODO: 번역 서비스 추가
            model_answer=question["model_answer"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create practice session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
