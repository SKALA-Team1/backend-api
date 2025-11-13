"""
Index Store
===========
임베딩된 청크를 저장하고 검색 인덱스를 관리하는 모듈.

역할:
    - 벡터 인덱스 생성/업데이트/저장 (FAISS, Milvus, Qdrant 등)
    - 메타데이터 포함 검색 및 필터링 지원
    - 교재 단원별, 주제별 인덱스 분리 관리

주요 함수(예시):
    - create_index(embeddings)
    - search(query_vector, top_k)
    - save_index(path)
    - load_index(path)

의존성:
    - faiss, numpy, pandas
"""