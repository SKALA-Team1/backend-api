"""
Embedder
========
교재 텍스트 및 문항을 벡터 임베딩으로 변환하는 모듈.

역할:
    - chunk 단위 텍스트 임베딩 생성 (OpenAI text-embedding)
    - 임베딩 모델 선택 및 캐싱
    - 벡터 유사도 검색용 데이터 준비

의존성:
    - openai, langchain-openai
"""

import logging
from typing import Optional

from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


class TextEmbedder:
    """텍스트 임베딩 클래스"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None
    ):
        """
        Args:
            model: OpenAI 임베딩 모델 이름
            api_key: OpenAI API 키 (없으면 설정에서 가져옴)
        """
        self.model = model
        self.api_key = api_key or settings.openai_api_key

        if not self.api_key:
            raise ValueError("OpenAI API key is required for embeddings")

        self.embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=self.api_key
        )

        logger.info(f"TextEmbedder initialized with model: {model}")

    def embed_text(self, text: str) -> list[float]:
        """
        단일 텍스트 임베딩

        Args:
            text: 입력 텍스트

        Returns:
            임베딩 벡터
        """
        return self.embeddings.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        다중 텍스트 임베딩 (배치)

        Args:
            texts: 텍스트 리스트

        Returns:
            임베딩 벡터 리스트
        """
        return self.embeddings.embed_documents(texts)

    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072
        if "small" in self.model:
            return 1536
        elif "large" in self.model:
            return 3072
        else:
            # 기본값
            return 1536


# 싱글톤 인스턴스
_embedder: Optional[TextEmbedder] = None


def get_embedder() -> TextEmbedder:
    """TextEmbedder 싱글톤 반환"""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedder()
    return _embedder
