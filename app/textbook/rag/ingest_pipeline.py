"""
Ingest Pipeline
===============
교재 데이터를 RAG 파이프라인에 투입하기 위한 전체 ingestion 프로세스를 정의하는 모듈.

역할:
    - 교재 텍스트 수집 → 청크 분할 → 임베딩 → 인덱스 저장까지 자동화
    - 신규 교재나 업데이트된 단원에 대한 증분 처리 지원
    - 로그 및 에러 관리 포함

주요 함수(예시):
    - ingest_textbook(source_path, index_path)
    - process_unit(unit_text, metadata)
    - refresh_index()

의존성:
    - chunker.py, embedder.py, index_store.py
"""