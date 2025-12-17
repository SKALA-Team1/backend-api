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
        Character alignment에서 정교한 Viseme 값 계산
        
        개선사항:
        - Character 단위로 처리하여 더 정밀한 타이밍
        - Phoneme 기반 viseme 매핑으로 더 자연스러운 입 모양
        - 유성음/무성음, 모음/자음 구분
        """
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
        
        if not characters or not start_times or not end_times:
            return visemes
        
        # Character 단위로 viseme 계산 (더 정밀한 동기화)
        for i, char in enumerate(characters):
            if i >= len(start_times) or i >= len(end_times):
                continue
            
            char_lower = char.lower()
            start_time = start_times[i]
            end_time = end_times[i]
            
            # Phoneme 기반 viseme 값 계산
            viseme_value = self._char_to_viseme(char_lower)
            
            # 너무 짧은 구간은 병합 (최소 0.05초)
            duration = end_time - start_time
            if duration < 0.05 and visemes:
                # 이전 viseme과 병합
                prev_viseme = visemes[-1]
                prev_viseme['end_time'] = end_time
                # 가중 평균으로 viseme 값 조정
                prev_duration = prev_viseme['end_time'] - prev_viseme['start_time']
                total_duration = prev_duration + duration
                if total_duration > 0:
                    prev_viseme['value'] = (
                        prev_viseme['value'] * prev_duration + viseme_value * duration
                    ) / total_duration
            else:
                visemes.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'value': viseme_value
                })
        
        return visemes
    
    def _char_to_viseme(self, char: str) -> float:
        """
        Character를 viseme 값으로 변환 (0.0 ~ 1.0)
        
        Phoneme-to-viseme 매핑 기반:
        - 모음 (a, e, i, o, u): 높은 값 (0.7 ~ 1.0)
        - 유성 자음 (b, d, g, v, z, m, n, l, r): 중간 값 (0.4 ~ 0.6)
        - 무성 자음 (p, t, k, f, s, h): 낮은 값 (0.2 ~ 0.4)
        - 조용한 자음 (c, q, x): 매우 낮은 값 (0.1 ~ 0.2)
        """
        # 모음 - 입이 많이 열림
        if char in 'aeiou':
            if char in 'ao':  # 'a', 'o' - 가장 큰 입 모양
                return 0.95
            elif char in 'eu':  # 'e', 'u' - 중간
                return 0.85
            else:  # 'i' - 약간 작은 입 모양
                return 0.75
        
        # 유성 자음 - 입이 약간 열림
        elif char in 'bdgvzmnlrwy':
            if char in 'mn':  # 'm', 'n' - 입이 닫히지만 소리 있음
                return 0.35
            elif char in 'lr':  # 'l', 'r' - 혀 위치 중요
                return 0.50
            elif char in 'wy':  # 'w', 'y' - 반모음
                return 0.70
            else:  # 'b', 'd', 'g', 'v', 'z'
                return 0.45
        
        # 무성 자음 - 입이 거의 닫힘
        elif char in 'ptkfsh':
            if char in 'ptk':  # 폐쇄음
                return 0.25
            elif char in 'fs':  # 마찰음
                return 0.30
            else:  # 'h'
                return 0.40
        
        # 조용한 자음/특수 문자
        elif char in 'cqxj':
            return 0.15
        
        # 공백, 구두점 등
        elif char in ' .,!?;:\'"':
            return 0.10
        
        # 기타 문자 (숫자 등)
        else:
            return 0.30


# 전역 인스턴스
_tts_adapter: Optional[ElevenLabsTTSAdapter] = None


def get_tts_adapter() -> ElevenLabsTTSAdapter:
    """TTS Adapter 싱글톤"""
    global _tts_adapter
    if _tts_adapter is None:
        _tts_adapter = ElevenLabsTTSAdapter()
    return _tts_adapter
