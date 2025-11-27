"""
RAG Router (에이전트1 API)
==========================
교재 기반 RAG 검색 및 인제스트 API 엔드포인트.

역할:
    - 교재 내용 검색 API
    - 인제스트 상태 조회 API
    - 인제스트 실행 API (관리자용)

의존성:
    - index_store.py, ingest_pipeline.py
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.textbook.rag.index_store import get_vector_store, SearchResult
from app.textbook.rag.ingest_pipeline import IngestPipeline, ingest_default_textbook, IngestResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG (에이전트1)"])


# ============================================================
# Schemas
# ============================================================

class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., min_length=1, max_length=500, description="검색 쿼리")
    top_k: int = Field(5, ge=1, le=20, description="반환할 결과 수")
    chapter_filter: Optional[str] = Field(None, description="특정 챕터로 필터링")


class SearchResultItem(BaseModel):
    """검색 결과 항목"""
    id: str
    text: str
    chapter: str
    page_start: int
    page_end: int
    score: float
    chunk_index: int


class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    results_count: int
    results: list[SearchResultItem]


class IndexStatusResponse(BaseModel):
    """인덱스 상태 응답"""
    chunk_count: int
    chapters: list[str]


class IngestResponse(BaseModel):
    """인제스트 응답"""
    success: bool
    pdf_name: str
    total_pages: int
    chapters_count: int
    chunks_count: int
    error_message: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.post("/search", response_model=SearchResponse)
async def search_textbook(request: SearchRequest):
    """
    교재 내용 검색

    쿼리와 관련된 교재 내용을 벡터 유사도 기반으로 검색합니다.

    - **query**: 검색할 내용 (영어/한국어 모두 가능)
    - **top_k**: 반환할 결과 수 (기본값: 5, 최대: 20)
    - **chapter_filter**: 특정 챕터만 검색 (옵션)
    """
    try:
        store = get_vector_store()

        results = store.search(
            query=request.query,
            n_results=request.top_k,
            chapter_filter=request.chapter_filter
        )

        result_items = [
            SearchResultItem(
                id=r.id,
                text=r.text,
                chapter=r.chapter,
                page_start=r.page_start,
                page_end=r.page_end,
                score=r.score,
                chunk_index=r.metadata.get("chunk_index", 0)
            )
            for r in results
        ]

        return SearchResponse(
            query=request.query,
            results_count=len(result_items),
            results=result_items
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search", response_model=SearchResponse)
async def search_textbook_get(
    query: str = Query(..., min_length=1, max_length=500, description="검색 쿼리"),
    top_k: int = Query(5, ge=1, le=20, description="반환할 결과 수"),
    chapter: Optional[str] = Query(None, description="특정 챕터로 필터링")
):
    """
    교재 내용 검색 (GET 방식)

    간단한 검색용 GET 엔드포인트입니다.
    """
    request = SearchRequest(query=query, top_k=top_k, chapter_filter=chapter)
    return await search_textbook(request)


@router.get("/status", response_model=IndexStatusResponse)
async def get_index_status():
    """
    인덱스 상태 조회

    현재 벡터 DB에 저장된 청크 수와 챕터 목록을 반환합니다.
    """
    try:
        store = get_vector_store()

        return IndexStatusResponse(
            chunk_count=store.get_chunk_count(),
            chapters=store.get_chapters()
        )

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.get("/chapters", response_model=list[str])
async def get_chapters():
    """
    챕터 목록 조회

    인덱싱된 모든 챕터 목록을 반환합니다.
    """
    try:
        store = get_vector_store()
        return store.get_chapters()

    except Exception as e:
        logger.error(f"Chapters list failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chapters list failed: {str(e)}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_textbook(
    reset: bool = Query(False, description="기존 데이터 초기화 후 새로 인제스트")
):
    """
    교재 인제스트 실행

    AGS 교재 PDF를 벡터 DB에 인제스트합니다.

    **주의**: 이 작업은 시간이 걸릴 수 있습니다.

    - **reset**: True면 기존 벡터 DB를 초기화하고 새로 시작
    """
    try:
        logger.info(f"Starting ingest, reset={reset}")

        result = ingest_default_textbook(reset=reset)

        return IngestResponse(
            success=result.success,
            pdf_name=result.pdf_name,
            total_pages=result.total_pages,
            chapters_count=result.chapters_count,
            chunks_count=result.chunks_count,
            error_message=result.error_message
        )

    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")
