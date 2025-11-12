"""
Text Parser Utility
===================
교재(텍스트, PDF, HTML 등)에서 문단/문장 단위 데이터를 정제하고 구조화하는 유틸리티 모듈.

역할:
    - 원문 텍스트를 구문 단위로 분리 및 토큰화
    - 불필요한 기호, 공백, 주석 제거
    - 문서 내 메타정보(단원, 문항 번호, 제목 등) 추출

주요 함수(예시):
    - extract_sections(text): 단원별 구분
    - split_sentences(paragraph): 문장 단위 분리
    - clean_text(raw): 불필요한 기호 및 공백 정리

의존성:
    - re, nltk, spacy 등 텍스트 전처리 라이브러리
"""