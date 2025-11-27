"""
Scenario Router (에이전트2 API)
===============================
교재 기반 시나리오 생성 API 엔드포인트.

역할:
    - 시나리오 생성 API
    - 챕터 목록 조회 API
    - 시나리오 유형 목록 API
"""

import logging

from fastapi import APIRouter, HTTPException

from app.scenario.schemas import (
    ScenarioGenerateRequest,
    ScenarioResponse,
    ChapterListResponse,
    ScenarioType,
    DifficultyLevel
)
from app.scenario.scenario_generator import get_scenario_generator
from app.scenario.rag_service import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenario", tags=["시나리오 (에이전트2)"])


@router.post("/generate", response_model=ScenarioResponse)
async def generate_scenario(request: ScenarioGenerateRequest):
    """
    시나리오 생성

    교재 내용을 기반으로 영어 회화 시나리오를 생성합니다.

    - **topic**: 시나리오 주제 (예: "이메일 작성", "전화 응대")
    - **scenario_type**: 시나리오 유형 (business_email, phone_call, meeting 등)
    - **difficulty**: 난이도 (beginner, intermediate, advanced)
    - **num_turns**: 대화 턴 수 (기본 6턴)
    - **chapter_filter**: 특정 챕터로 제한 (옵션)
    - **include_korean_hints**: 한국어 힌트 포함 여부
    """
    try:
        generator = get_scenario_generator()
        scenario = generator.generate_scenario(request)

        logger.info(f"Generated scenario: {scenario.title}")
        return scenario

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")


@router.get("/chapters", response_model=ChapterListResponse)
async def get_chapters():
    """
    사용 가능한 챕터 목록 조회

    시나리오 생성에 사용할 수 있는 교재 챕터 목록을 반환합니다.
    """
    try:
        rag_service = get_rag_service()
        chapters = rag_service.get_available_chapters()

        return ChapterListResponse(
            chapters=chapters,
            total_count=len(chapters)
        )

    except Exception as e:
        logger.error(f"Failed to get chapters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get chapters: {str(e)}")


@router.get("/types")
async def get_scenario_types():
    """
    시나리오 유형 목록 조회

    지원하는 시나리오 유형 목록을 반환합니다.
    """
    return {
        "types": [
            {"value": t.value, "name": t.name.replace("_", " ").title()}
            for t in ScenarioType
        ]
    }


@router.get("/difficulties")
async def get_difficulty_levels():
    """
    난이도 목록 조회

    지원하는 난이도 목록을 반환합니다.
    """
    return {
        "difficulties": [
            {"value": d.value, "name": d.name.title()}
            for d in DifficultyLevel
        ]
    }


@router.get("/status")
async def get_status():
    """
    에이전트2 상태 조회

    RAG 인덱스 상태와 시나리오 생성기 상태를 반환합니다.
    """
    try:
        rag_service = get_rag_service()

        return {
            "status": "ready",
            "rag_index": {
                "chunk_count": rag_service.get_chunk_count(),
                "chapters_count": len(rag_service.get_available_chapters())
            }
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
