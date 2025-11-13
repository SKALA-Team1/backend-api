"""
Ranker
======
검색된 문서나 문항 후보를 관련도에 따라 재정렬하는 모듈.

역할:
    - query-문서 간 벡터 유사도 점수 계산 및 정규화
    - reranking 모델(예: cross-encoder, LLM 기반 reranker) 적용
    - 최종 상위 N개 후보 반환

주요 함수(예시):
    - rank_candidates(query, candidates)
    - apply_cross_encoder_rerank(query, docs)
    - normalize_scores(scores)

의존성:
    - embedder.py
    - sklearn, sentence-transformers, torch
"""