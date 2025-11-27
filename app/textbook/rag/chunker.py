"""
Text Chunker
============
교재 텍스트를 RAG 파이프라인에서 활용하기 위한 단위 청크(chunk)로 분리하는 모듈.

역할:
    - 텍스트 길이에 맞춰 문단/문장 단위로 분할
    - 문맥 유지를 위한 overlap 제어
    - chunk 메타정보(id, 위치, 단원, 페이지 등) 관리

의존성:
    - langchain, tiktoken
"""

import logging
import hashlib
from typing import Optional
from dataclasses import dataclass, field

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """텍스트 청크"""
    id: str  # 고유 ID (해시)
    text: str  # 텍스트 내용
    chapter: str  # 챕터 제목
    page_start: int  # 시작 페이지
    page_end: int  # 끝 페이지
    chunk_index: int  # 챕터 내 청크 인덱스
    token_count: int  # 토큰 수
    metadata: dict = field(default_factory=dict)


class TextChunker:
    """텍스트 청킹 클래스"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Args:
            chunk_size: 청크당 최대 토큰 수
            chunk_overlap: 청크 간 오버랩 토큰 수
            encoding_name: tiktoken 인코딩 이름 (cl100k_base for GPT-4)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoding_name = encoding_name

        # tiktoken 인코더
        self.tokenizer = tiktoken.get_encoding(encoding_name)

        # LangChain 텍스트 스플리터 (토큰 기반)
        self.splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name=encoding_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        logger.info(
            f"TextChunker initialized: size={chunk_size}, overlap={chunk_overlap}"
        )

    def count_tokens(self, text: str) -> int:
        """토큰 수 계산"""
        return len(self.tokenizer.encode(text))

    def generate_chunk_id(self, chapter: str, chunk_index: int, text: str) -> str:
        """청크 고유 ID 생성 (해시 기반)"""
        content = f"{chapter}:{chunk_index}:{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def chunk_section(
        self,
        text: str,
        chapter: str,
        page_start: int,
        page_end: int,
        extra_metadata: Optional[dict] = None
    ) -> list[Chunk]:
        """
        섹션(챕터) 텍스트를 청크로 분할

        Args:
            text: 섹션 텍스트
            chapter: 챕터 제목
            page_start: 시작 페이지
            page_end: 끝 페이지
            extra_metadata: 추가 메타데이터

        Returns:
            청크 리스트
        """
        # 텍스트 정리
        text = self._clean_text(text)

        if not text.strip():
            return []

        # LangChain으로 분할
        split_texts = self.splitter.split_text(text)

        chunks = []
        for i, chunk_text in enumerate(split_texts):
            chunk_id = self.generate_chunk_id(chapter, i, chunk_text)
            token_count = self.count_tokens(chunk_text)

            metadata = {
                "source": "AGS_textbook",
                "chapter": chapter,
                "page_start": page_start,
                "page_end": page_end,
                "chunk_index": i,
                "total_chunks": len(split_texts)
            }

            if extra_metadata:
                metadata.update(extra_metadata)

            chunk = Chunk(
                id=chunk_id,
                text=chunk_text,
                chapter=chapter,
                page_start=page_start,
                page_end=page_end,
                chunk_index=i,
                token_count=token_count,
                metadata=metadata
            )
            chunks.append(chunk)

        logger.debug(f"Chunked '{chapter}': {len(chunks)} chunks")
        return chunks

    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        # 과도한 공백 제거
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)

        text = '\n'.join(lines)

        # 연속 줄바꿈 정리
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')

        return text.strip()


def chunk_sections_from_toc(
    pdf_parser,
    toc_entries: list,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> list[Chunk]:
    """
    TOC 기반으로 PDF를 섹션별로 청킹

    Args:
        pdf_parser: 열린 PDFParser 인스턴스
        toc_entries: TOC 항목 리스트
        chunk_size: 청크 크기
        chunk_overlap: 오버랩 크기

    Returns:
        전체 청크 리스트
    """
    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []

    for i, entry in enumerate(toc_entries):
        # 다음 섹션의 시작 페이지 또는 문서 끝
        if i + 1 < len(toc_entries):
            end_page = toc_entries[i + 1].page_num - 1
        else:
            end_page = pdf_parser.page_count

        start_page = entry.page_num - 1  # 0-based 변환

        # 텍스트 추출
        text = pdf_parser.get_text_range(start_page, end_page)

        # 청킹
        chunks = chunker.chunk_section(
            text=text,
            chapter=entry.title,
            page_start=entry.page_num,
            page_end=end_page
        )

        all_chunks.extend(chunks)

    logger.info(f"Total chunks created: {len(all_chunks)}")
    return all_chunks
