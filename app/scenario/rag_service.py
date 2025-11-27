"""
RAG Service (에이전트2)
=======================
에이전트1(RAG)과 연동하여 교재 내용 검색.

역할:
    - 시나리오 주제에 맞는 교재 내용 검색
    - 검색 결과를 LLM 컨텍스트용으로 포맷팅
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.textbook.rag.index_store import get_vector_store, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class TextbookContext:
    """교재 컨텍스트"""
    query: str
    chapters: list[str]
    contents: list[str]
    combined_text: str


class RAGService:
    """RAG 검색 서비스"""

    def __init__(self):
        self.vector_store = get_vector_store()
        logger.info("RAGService initialized")

    def search_textbook(
        self,
        query: str,
        n_results: int = 5,
        chapter_filter: Optional[str] = None
    ) -> list[SearchResult]:
        """
        교재 내용 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            chapter_filter: 특정 챕터로 필터링

        Returns:
            검색 결과 리스트
        """
        results = self.vector_store.search(
            query=query,
            n_results=n_results,
            chapter_filter=chapter_filter
        )
        logger.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results

    def get_context_for_scenario(
        self,
        topic: str,
        scenario_type: str,
        n_results: int = 5,
        chapter_filter: Optional[str] = None
    ) -> TextbookContext:
        """
        시나리오 생성용 교재 컨텍스트 조회

        Args:
            topic: 시나리오 주제
            scenario_type: 시나리오 유형
            n_results: 검색 결과 수
            chapter_filter: 챕터 필터

        Returns:
            TextbookContext 객체
        """
        # 주제와 유형을 조합한 검색 쿼리
        search_query = f"{topic} {scenario_type.replace('_', ' ')}"

        results = self.search_textbook(
            query=search_query,
            n_results=n_results,
            chapter_filter=chapter_filter
        )

        # 검색 결과 정리
        chapters = list(set(r.chapter for r in results))
        contents = [r.text for r in results]

        # 컨텍스트 텍스트 생성
        combined_parts = []
        for r in results:
            combined_parts.append(f"[{r.chapter}]\n{r.text}")

        combined_text = "\n\n---\n\n".join(combined_parts)

        return TextbookContext(
            query=search_query,
            chapters=chapters,
            contents=contents,
            combined_text=combined_text
        )

    def get_available_chapters(self) -> list[str]:
        """사용 가능한 챕터 목록"""
        return self.vector_store.get_chapters()

    def get_chunk_count(self) -> int:
        """인덱싱된 청크 수"""
        return self.vector_store.get_chunk_count()


# 싱글톤 인스턴스
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """RAGService 싱글톤 반환"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
