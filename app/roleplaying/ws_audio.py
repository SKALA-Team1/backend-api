"""
WebSocket Audio Handler
=======================
실시간 음성 대화(WebRTC / WebSocket 기반)를 처리하는 모듈.

역할:
    - 클라이언트와 서버 간 음성 데이터 스트림 관리
    - STT(Speech-To-Text), TTS(Text-To-Speech) 파이프라인 연동
    - 실시간 상태 업데이트 및 연결 관리

주요 함수:
    - handle_audio_stream(ws)
    - transcribe_audio(audio_chunk)
    - stream_tts_response(text)

의존성:
    - Core/audio_processor.py (음성 변환)
    - Services/message_flow_service.py
"""