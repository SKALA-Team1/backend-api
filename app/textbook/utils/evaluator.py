"""
Evaluator Utility
=================
사용자 답안 또는 모델 생성 결과를 평가하는 범용 유틸리티 모듈.

역할:
    - 텍스트 유사도, 의미 일치도, 정답률 등의 평가 지표 계산
    - 정답 키 기반 규칙형 채점 또는 LLM 기반 평가 지원
    - RAG, QA, 번역 등 다양한 도메인에서 재사용 가능

주요 함수(예시):
    - compute_accuracy(pred, target)
    - semantic_similarity(a, b)
    - llm_based_evaluate(question, answer, reference)

의존성:
    - sklearn.metrics, sentence-transformers, Core/llm_client.py
"""