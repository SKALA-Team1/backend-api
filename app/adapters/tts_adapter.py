"""
📄 파일명: tts_adapter.py
📌 역할: 텍스트 → 음성 변환 (Text-to-Speech) - ElevenLabs 통합
"""

from typing import List, Dict, Optional
from elevenlabs import ElevenLabs
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class ElevenLabsTTSAdapter:
    """ElevenLabs TTS Adapter"""
    
    def __init__(self):
        if not settings.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY is not set")
        self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        self.voice_id = settings.ELEVENLABS_VOICE_ID
    
    async def synthesize_with_viseme(
        self, 
        text: str
    ) -> Dict:
        """
        TTS 생성 및 간단한 Viseme 데이터 계산
        
        Returns:
            {
                'audio_base64': str,
                'visemes': List[Dict]  # [{'start_time': float, 'end_time': float, 'value': float}]
            }
        """
        try:
            # ElevenLabs API 호출
            response = self.client.text_to_speech.convert_with_timestamps(
                voice_id=self.voice_id,
                text=text
            )
            
            # 응답 객체에서 오디오 데이터 가져오기
            # Pydantic 모델이므로 model_dump()로 딕셔너리 변환 후 접근
            import base64
            
            # 실제 속성 이름: 'audio_base_64' (언더스코어 포함)
            # Pydantic 모델이므로 직접 속성 접근 또는 model_dump() 사용
            audio_base64 = None
            
            # 방법 1: 직접 속성 접근 (audio_base_64)
            if hasattr(response, 'audio_base_64'):
                audio_base64 = response.audio_base_64
                logger.debug("Found audio_base_64 via direct attribute access")
            
            # 방법 2: model_dump()로 딕셔너리 변환 후 접근
            if audio_base64 is None and hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
                # 딕셔너리 키도 확인 (Pydantic이 키 이름을 변환할 수 있음)
                audio_base64 = response_dict.get('audio_base_64') or response_dict.get('audioBase64') or response_dict.get('audio_base64')
                if audio_base64:
                    logger.debug("Found audio_base_64 via model_dump()")
            
            # 방법 3: audio 속성이 bytes인 경우 base64 인코딩
            if audio_base64 is None and hasattr(response, 'audio'):
                audio_bytes = response.audio
                if audio_bytes:
                    if isinstance(audio_bytes, bytes):
                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.debug("Found audio bytes, encoded to base64")
                    elif isinstance(audio_bytes, str):
                        audio_base64 = audio_bytes
                        logger.debug("Found audio as string")
            
            # 방법 4: 딕셔너리인 경우
            if audio_base64 is None and isinstance(response, dict):
                audio_base64 = response.get('audio_base_64') or response.get('audio_base64')
                if audio_base64 is None:
                    audio_bytes = response.get('audio')
                    if audio_bytes:
                        if isinstance(audio_bytes, bytes):
                            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                        elif isinstance(audio_bytes, str):
                            audio_base64 = audio_bytes
            
            if audio_base64 is None:
                # 디버깅: 응답 객체의 속성 확인
                response_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
                if hasattr(response, 'model_dump'):
                    response_dict = response.model_dump()
                    logger.error(f"Response dict keys: {list(response_dict.keys())}")
                logger.error(f"Response attributes: {response_attrs}")
                raise ValueError(
                    f"응답 객체에서 audio 데이터를 찾을 수 없습니다. "
                    f"응답 타입: {type(response)}, "
                    f"사용 가능한 속성: {response_attrs}"
                )
            
            # alignment 가져오기
            # Pydantic 모델인 경우 model_dump()로 딕셔너리 변환 후 접근
            if hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
                alignment = response_dict.get('alignment')
            elif hasattr(response, 'alignment'):
                alignment = response.alignment
            elif isinstance(response, dict):
                alignment = response.get('alignment')
            else:
                alignment = None
            
            # 간단한 Viseme 추정 (단어 단위)
            visemes = self._estimate_visemes(text, alignment)
            
            return {
                'audio_base64': audio_base64,
                'visemes': visemes
            }
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}", exc_info=True)
            raise
    
    def _estimate_visemes(
        self, 
        text: str, 
        alignment: Optional[Dict]
    ) -> List[Dict]:
        """
        Character alignment에서 간단한 Viseme 값 계산
        
        규칙:
        - 단어 단위로 처리
        - 모음 비율에 따라 viseme 값 계산 (0.2 ~ 0.8)
        """
        words = text.split()
        visemes = []
        
        if not alignment:
            return visemes
        
        # alignment가 객체일 수도 있고 딕셔너리일 수도 있음
        if hasattr(alignment, 'characters'):
            # 객체인 경우 속성 접근
            characters = alignment.characters
            start_times = alignment.character_start_times_seconds
            end_times = alignment.character_end_times_seconds
        elif isinstance(alignment, dict):
            # 딕셔너리인 경우
            if 'characters' not in alignment:
                return visemes
            characters = alignment.get('characters', [])
            start_times = alignment.get('character_start_times_seconds', [])
            end_times = alignment.get('character_end_times_seconds', [])
        else:
            return visemes
        
        char_times = list(zip(characters, start_times, end_times))
        
        char_idx = 0
        for word in words:
            if char_idx >= len(char_times):
                break
            
            # 단어의 시작/종료 시간 찾기
            word_start = char_times[char_idx][1] if char_idx < len(char_times) else 0
            
            # 단어의 문자 개수만큼 이동
            word_char_count = len(word)
            end_char_idx = min(char_idx + word_char_count - 1, len(char_times) - 1)
            word_end = char_times[end_char_idx][2] if end_char_idx < len(char_times) else word_start + 0.5
            
            # 모음 비율 계산
            vowel_count = sum(1 for c in word.lower() if c in 'aeiou')
            vowel_ratio = vowel_count / len(word) if word else 0
            
            # Viseme 값: 0.2 (닫힘) ~ 0.8 (열림)
            viseme_value = 0.2 + (vowel_ratio * 0.6)
            
            visemes.append({
                'start_time': word_start,
                'end_time': word_end,
                'value': viseme_value
            })
            
            char_idx += word_char_count + 1  # +1 for space
        
        return visemes


# 전역 인스턴스
_tts_adapter: Optional[ElevenLabsTTSAdapter] = None


def get_tts_adapter() -> ElevenLabsTTSAdapter:
    """TTS Adapter 싱글톤"""
    global _tts_adapter
    if _tts_adapter is None:
        _tts_adapter = ElevenLabsTTSAdapter()
    return _tts_adapter
