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
        self.model_id = settings.ELEVENLABS_MODEL_ID
    
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
            # ElevenLabs API 호출 (저렴한 모델 사용)
            response = self.client.text_to_speech.convert_with_timestamps(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id
            )
            
            # Pydantic 모델이므로 model_dump()로 딕셔너리 변환 후 접근
            # convert_with_timestamps는 일관되게 audio_base_64와 alignment를 반환함
            response_dict = response.model_dump()
            audio_base64 = response_dict['audio_base_64']
            alignment = response_dict.get('alignment')
            
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
            
            # Viseme 값: 0.3 (닫힘) ~ 1.0 (열림) - 더 자연스러운 입 모양을 위해 범위 확대
            viseme_value = 0.3 + (vowel_ratio * 0.7)
            
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
