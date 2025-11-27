"""
Index Store (Vector Store)
==========================
임베딩된 청크를 저장하고 검색 인덱스를 관리하는 모듈.

역할:
    - ChromaDB 벡터 인덱스 생성/업데이트/저장
    - 메타데이터 포함 검색 및 필터링 지원
    - 교재 단원별, 주제별 인덱스 분리 관리

의존성:
    - chromadb, langchain-openai
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.textbook.rag.chunker import Chunk
from app.textbook.rag.embedder import get_embedder

logger = logging.getLogger(__name__)

# ChromaDB 저장 경로
CHROMA_PERSIST_DIR = Path("data/chroma_db")


@dataclass
class SearchResult:
    """검색 결과"""
    id: str
    text: str
    chapter: str
    page_start: int
    page_end: int
    score: float  # 유사도 점수 (거리가 작을수록 유사)
    metadata: dict


class VectorStore:
    """ChromaDB 기반 벡터 저장소"""

    def __init__(
        self,
        collection_name: str = "ags_textbook",
        persist_directory: Optional[str] = None
    ):
        """
        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: 영구 저장 디렉토리 (없으면 기본값 사용)
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory) if persist_directory else CHROMA_PERSIST_DIR

        # 디렉토리 생성
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 (영구 저장)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 컬렉션 가져오기 또는 생성
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "AGS English Textbook Embeddings"}
        )

        # 임베더
        self._embedder = None

        logger.info(
            f"VectorStore initialized: collection={collection_name}, "
            f"persist_dir={self.persist_directory}"
        )

    @property
    def embedder(self):
        """임베더 lazy loading"""
        if self._embedder is None:
            self._embedder = get_embedder()
        return self._embedder

    def add_chunks(self, chunks: list[Chunk], batch_size: int = 100) -> int:
        """
        청크들을 벡터 저장소에 추가

        Args:
            chunks: 청크 리스트
            batch_size: 배치 크기

        Returns:
            추가된 청크 수
        """
        if not chunks:
            return 0

        total_added = 0

        # 배치 처리
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            ids = [chunk.id for chunk in batch]
            texts = [chunk.text for chunk in batch]
            metadatas = [
                {
                    "chapter": chunk.chapter,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    **chunk.metadata
                }
                for chunk in batch
            ]

            # 임베딩 생성
            embeddings = self.embedder.embed_texts(texts)

            # ChromaDB에 추가
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )

            total_added += len(batch)
            logger.info(f"Added batch {i // batch_size + 1}: {len(batch)} chunks")

        logger.info(f"Total chunks added: {total_added}")
        return total_added

    def search(
        self,
        query: str,
        n_results: int = 5,
        chapter_filter: Optional[str] = None
    ) -> list[SearchResult]:
        """
        유사도 검색

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            chapter_filter: 특정 챕터로 필터링 (옵션)

        Returns:
            검색 결과 리스트
        """
        # 쿼리 임베딩
        query_embedding = self.embedder.embed_text(query)

        # 필터 설정
        where_filter = None
        if chapter_filter:
            where_filter = {"chapter": {"$eq": chapter_filter}}

        # 검색
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # 결과 변환
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                search_results.append(SearchResult(
                    id=doc_id,
                    text=results["documents"][0][i] if results["documents"] else "",
                    chapter=metadata.get("chapter", ""),
                    page_start=metadata.get("page_start", 0),
                    page_end=metadata.get("page_end", 0),
                    score=results["distances"][0][i] if results["distances"] else 0,
                    metadata=metadata
                ))

        return search_results

    def get_chunk_count(self) -> int:
        """저장된 청크 수 반환"""
        return self.collection.count()

    def get_chapters(self) -> list[str]:
        """저장된 챕터 목록 반환"""
        # 모든 메타데이터에서 chapter 추출
        result = self.collection.get(include=["metadatas"])
        chapters = set()
        if result["metadatas"]:
            for metadata in result["metadatas"]:
                if "chapter" in metadata:
                    chapters.add(metadata["chapter"])
        return sorted(list(chapters))

    def delete_collection(self):
        """컬렉션 삭제"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    def reset(self):
        """컬렉션 초기화 (삭제 후 재생성)"""
        self.delete_collection()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "AGS English Textbook Embeddings"}
        )
        logger.info(f"Reset collection: {self.collection_name}")


# 싱글톤 인스턴스
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """VectorStore 싱글톤 반환"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
