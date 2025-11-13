"""
Retriever
==========
RAG 질의응답 파이프라인에서 실제 검색 단계를 수행하는 모듈.

역할:
    - 사용자 질문 → 벡터 임베딩 → 인덱스 검색 → 상위 청크 반환
    - Ranker와 연동하여 최종 문맥 선택
    - 질의응답 또는 문항 생성에 필요한 컨텍스트 구성

주요 함수(예시):
    - retrieve_context(query, top_k=5)
    - retrieve_with_rerank(query, top_k=10)
    - format_context_results(results)

의존성:
    - embedder.py
    - index_store.py
    - ranker.py
"""