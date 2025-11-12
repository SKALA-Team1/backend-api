"""
Embedder
========
교재 텍스트 및 문항을 벡터 임베딩으로 변환하는 모듈.

역할:
    - chunk 단위 텍스트 임베딩 생성 (e.g., OpenAI, SentenceTransformers)
    - 임베딩 모델 선택 및 캐싱
    - 벡터 유사도 검색용 데이터 준비

주요 함수(예시):
    - embed_chunks(chunks)
    - load_embedding_model(model_name)
    - vectorize_text(text)

의존성:
    - openai, sentence-transformers, numpy
"""