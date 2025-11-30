"""
Index Store (Vector Store)
==========================
임베딩된 청크를 저장하고 검색 인덱스를 관리하는 모듈.

역할:
    - Qdrant 벡터 인덱스 생성/업데이트/저장
    - 메타데이터 포함 검색 및 필터링 지원
    - 교재 단원별, 주제별 인덱스 분리 관리

의존성:
    - qdrant-client, langchain-openai
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from app.textbook.rag.chunker import Chunk
from app.textbook.rag.embedder import get_embedder
from app.config import settings

logger = logging.getLogger(__name__)

# Qdrant 저장 경로 (로컬 파일 기반)
QDRANT_PERSIST_DIR = Path("data/qdrant_db")

# 임베딩 벡터 차원 (OpenAI text-embedding-3-small 기준)
EMBEDDING_DIMENSION = 1536


@dataclass
class SearchResult:
    """검색 결과"""
    id: str
    text: str
    chapter: str
    page_start: int
    page_end: int
    score: float  # 유사도 점수 (높을수록 유사)
    metadata: dict


class VectorStore:
    """Qdrant 기반 벡터 저장소"""

    def __init__(
        self,
        collection_name: str = "ags_textbook",
        persist_directory: Optional[str] = None,
        qdrant_url: Optional[str] = None
    ):
        """
        Args:
            collection_name: Qdrant 컬렉션 이름
            persist_directory: 로컬 영구 저장 디렉토리 (없으면 기본값 사용)
            qdrant_url: Qdrant 서버 URL (없으면 로컬 파일 모드)
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory) if persist_directory else QDRANT_PERSIST_DIR

        # Qdrant URL 설정 (config에서 가져오거나 로컬 모드)
        self.qdrant_url = qdrant_url or getattr(settings, 'QDRANT_URL', None)

        if self.qdrant_url:
            # 원격 Qdrant 서버 연결
            self.client = QdrantClient(url=self.qdrant_url)
            logger.info(f"Connected to Qdrant server: {self.qdrant_url}")
        else:
            # 로컬 파일 기반 Qdrant
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(self.persist_directory))
            logger.info(f"Using local Qdrant: {self.persist_directory}")

        # 컬렉션 생성 또는 확인
        self._ensure_collection()

        # 임베더
        self._embedder = None

        logger.info(
            f"VectorStore initialized: collection={collection_name}"
        )

    def _ensure_collection(self):
        """컬렉션 존재 확인 및 생성"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Collection already exists: {self.collection_name}")

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

            texts = [chunk.text for chunk in batch]

            # 임베딩 생성
            embeddings = self.embedder.embed_texts(texts)

            # Qdrant 포인트 생성
            points = []
            for j, chunk in enumerate(batch):
                # UUID 형식으로 ID 생성 (Qdrant는 UUID 또는 정수 ID 필요)
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))

                payload = {
                    "text": chunk.text,
                    "chunk_id": chunk.id,
                    "chapter": chunk.chapter,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "chunk_index": chunk.chunk_index,
                    "token_count": chunk.token_count,
                    **chunk.metadata
                }

                points.append(PointStruct(
                    id=point_id,
                    vector=embeddings[j],
                    payload=payload
                ))

            # Qdrant에 추가
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
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
        query_filter = None
        if chapter_filter:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="chapter",
                        match=qdrant_models.MatchValue(value=chapter_filter)
                    )
                ]
            )

        # 검색
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=n_results,
            query_filter=query_filter
        )

        # 결과 변환
        search_results = []
        for hit in results.points:
            payload = hit.payload or {}
            search_results.append(SearchResult(
                id=payload.get("chunk_id", str(hit.id)),
                text=payload.get("text", ""),
                chapter=payload.get("chapter", ""),
                page_start=payload.get("page_start", 0),
                page_end=payload.get("page_end", 0),
                score=hit.score,  # Qdrant는 코사인 유사도 (높을수록 유사)
                metadata=payload
            ))

        return search_results

    def get_chunk_count(self) -> int:
        """저장된 청크 수 반환"""
        collection_info = self.client.get_collection(self.collection_name)
        return collection_info.points_count

    def get_chapters(self) -> list[str]:
        """저장된 챕터 목록 반환"""
        # Qdrant에서 모든 포인트의 chapter 필드 조회
        # scroll을 사용하여 페이지네이션 처리
        chapters = set()
        offset = None

        while True:
            results, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["chapter"]
            )

            for point in results:
                if point.payload and "chapter" in point.payload:
                    chapters.add(point.payload["chapter"])

            if offset is None:
                break

        return sorted(list(chapters))

    def delete_collection(self):
        """컬렉션 삭제"""
        self.client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    def reset(self):
        """컬렉션 초기화 (삭제 후 재생성)"""
        self.delete_collection()
        self._ensure_collection()
        logger.info(f"Reset collection: {self.collection_name}")


# 싱글톤 인스턴스
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """VectorStore 싱글톤 반환"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
