"""
Keyword Engine
==============
대화 중 핵심 키워드 및 주제를 추출하는 모듈.

역할:
    - 사용자의 메시지나 시나리오 텍스트에서 핵심 개념, 감정, 인물명 추출
    - 다음 응답 생성 또는 단계 전이 판단 시 활용

주요 함수:
    - extract_keywords(text)
    - detect_emotional_tone(text)
    - cluster_related_terms()

의존성:
    - NLP 라이브러리 또는 LLM 기반 키워드 분석
"""