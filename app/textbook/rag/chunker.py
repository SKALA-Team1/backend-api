"""
Text Chunker
============
교재 텍스트를 RAG 파이프라인에서 활용하기 위한 단위 청크(chunk)로 분리하는 모듈.

역할:
    - 텍스트 길이에 맞춰 문단/문장 단위로 분할
    - 문맥 유지를 위한 overlap 제어
    - chunk 메타정보(id, 위치, 단원, 페이지 등) 관리

주요 함수(예시):
    - chunk_text(text, max_tokens=512, overlap=50)
    - attach_metadata(chunks, source_info)

의존성:
    - utils/text_parser.py
    - tokenizer (e.g., tiktoken)
"""