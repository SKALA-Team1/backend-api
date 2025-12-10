"""
📄 파일명: router.py
📌 역할: FastAPI 라우터 정의. 피드백 관련 API 엔드포인트 제공.
        - 학습 요약, 피드백 상세 조회, 제안문 복습 API 등을 포함.
🧩 관련 모듈:
  - services/*.py: 실제 로직을 수행하는 서비스 계층
  - schemas.py: 요청/응답 검증 및 직렬화
🧠 주요 엔드포인트:
  - GET /feedback/comprehensive/{session_id} → 종합 피드백 생성 및 반환
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.feedback.services.aggregation_service import generate_comprehensive_feedback

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health/ping")
async def ping():
    """헬스 체크"""
    return {"status": "ok"}


@router.post("/sessions/{session_id}/end-hook")
async def session_end_hook(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    세션 종료 Hook - 종합 피드백 자동 생성

    롤플레잉 세션이 종료될 때 호출되어 종합 피드백을 자동으로 생성하고 DB에 저장합니다.
    외부 시스템(WebSocket handler, Spring 2 등)에서 세션 종료 시 호출해야 합니다.

    Args:
        session_id: 종료된 롤플레잉 세션 ID (UUID)
        db: SQLAlchemy 세션 (자동 주입)

    Returns:
        {
            "success": true,
            "session_id": "...",
            "comprehensive_feedback": {...}
        }

    Raises:
        HTTPException(404): 세션 데이터를 찾을 수 없음
        HTTPException(500): 종합 피드백 생성 실패
    """
    try:
        logger.info(f"📊 [세션 종료 Hook 호출] session_id={session_id}")

        # 종합 피드백 생성 (DB 저장 포함)
        result = await generate_comprehensive_feedback(
            session_id=session_id,
            db=db
        )

        if result:
            logger.info(f"✅ [세션 종료 Hook 성공] session_id={session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "comprehensive_feedback": result
            }
        else:
            logger.warning(f"⚠️  [종합 피드백 데이터 없음] session_id={session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No feedback data found for session: {session_id}"
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ [세션 종료 Hook 실패] session_id={session_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comprehensive feedback: {str(e)}"
        )


@router.get("/comprehensive/{session_id}")
async def get_comprehensive_feedback(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    종합 피드백 생성 및 반환

    Args:
        session_id: 롤플레잉 세션 ID (UUID)
        db: SQLAlchemy 세션 (자동 주입)

    Returns:
        {
            "session_id": "...",
            "total_pronunciation": 85.5,
            "total_grammar": 78.3,
            "total_diversity": 82.0,
            "feedback_short": "전반적으로 잘하셨어요! ...",
            "feedback_long": "오늘 회의 고생하셨어요! ..."
        }

    Raises:
        HTTPException(404): 세션을 찾을 수 없음
        HTTPException(500): 피드백 생성 실패
    """
    try:
        logger.info(f"📊 종합 피드백 요청: session_id={session_id}")

        # 종합 피드백 생성
        result = await generate_comprehensive_feedback(
            session_id=session_id,
            db=db
        )

        if not result:
            logger.warning(f"종합 피드백 생성 실패: session_id={session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or no feedback data available: {session_id}"
            )

        # 응답에 session_id 추가
        result["session_id"] = session_id

        logger.info(f"✅ 종합 피드백 반환 성공: session_id={session_id}")
        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"❌ 종합 피드백 생성 중 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate comprehensive feedback: {str(e)}"
        )
