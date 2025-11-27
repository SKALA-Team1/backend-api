"""
Ingest Pipeline
===============
교재 데이터를 RAG 파이프라인에 투입하기 위한 전체 ingestion 프로세스를 정의하는 모듈.

역할:
    - 교재 텍스트 수집 → 청크 분할 → 임베딩 → 인덱스 저장까지 자동화
    - 신규 교재나 업데이트된 단원에 대한 증분 처리 지원
    - 로그 및 에러 관리 포함

의존성:
    - pdf_parser.py, chunker.py, embedder.py, index_store.py
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from app.textbook.rag.pdf_parser import PDFParser, extract_toc_from_content, TOCEntry
from app.textbook.rag.chunker import TextChunker, Chunk, chunk_sections_from_toc
from app.textbook.rag.index_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """인제스트 결과"""
    success: bool
    pdf_name: str
    total_pages: int
    chapters_count: int
    chunks_count: int
    error_message: Optional[str] = None


class IngestPipeline:
    """교재 인제스트 파이프라인"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        vector_store: Optional[VectorStore] = None
    ):
        """
        Args:
            chunk_size: 청크 크기 (토큰)
            chunk_overlap: 청크 오버랩 (토큰)
            vector_store: 벡터 저장소 (없으면 기본값 사용)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store = vector_store or get_vector_store()

        logger.info(
            f"IngestPipeline initialized: chunk_size={chunk_size}, overlap={chunk_overlap}"
        )

    def ingest_pdf(
        self,
        pdf_path: str | Path,
        reset_collection: bool = False
    ) -> IngestResult:
        """
        PDF 교재를 벡터 DB에 인제스트

        Args:
            pdf_path: PDF 파일 경로
            reset_collection: True면 기존 컬렉션을 초기화하고 새로 시작

        Returns:
            인제스트 결과
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return IngestResult(
                success=False,
                pdf_name=pdf_path.name,
                total_pages=0,
                chapters_count=0,
                chunks_count=0,
                error_message=f"PDF file not found: {pdf_path}"
            )

        try:
            logger.info(f"Starting ingestion: {pdf_path.name}")

            # 1. 컬렉션 초기화 (옵션)
            if reset_collection:
                logger.info("Resetting vector collection...")
                self.vector_store.reset()

            # 2. PDF 열기
            with PDFParser(pdf_path) as parser:
                total_pages = parser.page_count
                logger.info(f"PDF opened: {total_pages} pages")

                # 3. TOC 추출 (내용 기반)
                toc_entries = extract_toc_from_content(pdf_path)
                chapters_count = len(toc_entries)
                logger.info(f"TOC extracted: {chapters_count} chapters")

                if not toc_entries:
                    return IngestResult(
                        success=False,
                        pdf_name=pdf_path.name,
                        total_pages=total_pages,
                        chapters_count=0,
                        chunks_count=0,
                        error_message="No TOC entries found in PDF"
                    )

                # 4. 섹션별 청킹
                chunks = chunk_sections_from_toc(
                    pdf_parser=parser,
                    toc_entries=toc_entries,
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                )
                logger.info(f"Text chunked: {len(chunks)} chunks")

                # 5. 벡터 저장소에 추가
                added_count = self.vector_store.add_chunks(chunks)
                logger.info(f"Chunks added to vector store: {added_count}")

            return IngestResult(
                success=True,
                pdf_name=pdf_path.name,
                total_pages=total_pages,
                chapters_count=chapters_count,
                chunks_count=added_count
            )

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return IngestResult(
                success=False,
                pdf_name=pdf_path.name,
                total_pages=0,
                chapters_count=0,
                chunks_count=0,
                error_message=str(e)
            )

    def get_status(self) -> dict:
        """현재 인덱스 상태 조회"""
        return {
            "chunk_count": self.vector_store.get_chunk_count(),
            "chapters": self.vector_store.get_chapters()
        }


# 기본 PDF 경로
DEFAULT_PDF_PATH = Path("data/textbooks/AGS 영어 Intensive Course 교재_fnl(240223).pdf")


def ingest_default_textbook(reset: bool = False) -> IngestResult:
    """
    기본 AGS 교재를 인제스트

    Args:
        reset: True면 기존 데이터 초기화

    Returns:
        인제스트 결과
    """
    pipeline = IngestPipeline()
    return pipeline.ingest_pdf(DEFAULT_PDF_PATH, reset_collection=reset)


# CLI 실행용
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    reset = "--reset" in sys.argv

    print("=" * 50)
    print("AGS 교재 벡터 DB 인제스트")
    print("=" * 50)

    if reset:
        print("주의: 기존 벡터 DB를 초기화합니다!")

    result = ingest_default_textbook(reset=reset)

    print()
    print("결과:")
    print(f"  성공: {result.success}")
    print(f"  PDF: {result.pdf_name}")
    print(f"  총 페이지: {result.total_pages}")
    print(f"  챕터 수: {result.chapters_count}")
    print(f"  청크 수: {result.chunks_count}")

    if result.error_message:
        print(f"  에러: {result.error_message}")

    print("=" * 50)
