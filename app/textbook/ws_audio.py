"""
WebSocket Audio Handler (Textbook)
==================================
교재 레슨 중 실시간 음성(STT/TTS) 상호작용을 처리하는 모듈.

역할:
    - 학습자 음성 입력 스트림 수신 → STT 변환 → 질문/평가 로직 연동
    - AI 합성 음성(TTS) 스트리밍 응답
    - 연결/세션 관리, 레이턴시 제어, 에러 복구

주요 함수(예시):
    - handle_audio_session(ws, lesson_id)
    - transcribe_chunk(audio_chunk)     # STT
    - stream_tts(text)                  # TTS

의존성:
    - Core/audio_processor.py (STT/TTS)
    - Services/question_flow_service.py
    - Services/submit_answer_service.py
"""