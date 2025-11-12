"""
Question Builder
================
RAG 기반으로 교재 콘텐츠로부터 자동 문항(퀴즈, comprehension question 등)을 생성하는 모듈.

역할:
    - chunk 기반 지문에서 핵심 문장 추출
    - LLM을 활용하여 질문/보기/정답 생성
    - 학습 목표(Grammar, Vocabulary, Reading 등)에 따른 문항 타입 분류

주요 함수(예시):
    - build_questions_from_chunks(chunks)
    - generate_multiple_choice(context)
    - validate_generated_question(question)

의존성:
    - Core/llm_client.py
    - utils/evaluator.py
"""