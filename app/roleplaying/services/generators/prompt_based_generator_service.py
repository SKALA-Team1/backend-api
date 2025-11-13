"""
Prompt-Based Generator Service
==============================
프롬프트 기반으로 시나리오를 생성하는 AI Generator 모듈.

역할:
    - 사용자가 입력한 시나리오 주제(prompt)를 기반으로 대화 맥락 생성
    - 대화의 기본 설정 (캐릭터, 목표, 환경) 자동 구성
    - OpenAI / LLM API를 활용하여 시작 대사 및 지문 생성

주요 함수:
    - generate_intro(prompt)
    - generate_background(prompt)
    - generate_first_turn()

의존성:
    - Core/llm_client.py (LLM API 호출)
    - keyword_engine.py (핵심 키워드 추출)
"""