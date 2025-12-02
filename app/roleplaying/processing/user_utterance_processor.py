"""
발화 처리 및 저장
===============================================

역할:
- STT 처리
- 침묵 감지
- 히스토리 저장
- Spring 2 연동
"""

import asyncio
import logging
from typing import Optional

from app.config import settings
from app.integrations.clients.spring2_client import spring2_client
from app.roleplaying.core.session_state_manager import session_manager
from app.roleplaying.core.session_message_handler import SessionMessageHandler

logger = logging.getLogger(__name__)


class SilenceDetector:
    """침묵 감지"""

    MIN_TEXT_LENGTH = settings.AUDIO_MIN_TEXT_LENGTH

    @staticmethod
    def is_silence(text: Optional[str], min_length: int = MIN_TEXT_LENGTH) -> bool:
        """침묵 여부 판단"""
        return not text or len(text.strip()) < min_length

    @staticmethod
    def detect_with_logging(
        text: Optional[str],
        audio_length: Optional[int] = None
    ) -> bool:
        """로깅과 함께 침묵 감지"""
        if SilenceDetector.is_silence(text):
            if audio_length:
                logger.warning(
                    f"Silence detected: {audio_length} bytes of audio but no speech"
                )
            else:
                logger.warning("Silence detected: no speech recognized")
            return True
        return False


class UtteranceProcessor:
    """발화 처리 (STT + 히스토리)"""

    @staticmethod
    async def process_stt(audio_data: bytes) -> Optional[str]:
        """
        STT 처리

        Returns:
            인식된 텍스트 또는 None (침묵 감지)
        """
        try:
            from app.roleplaying.services.stt.speech_to_text_service import stt_service

            stt_text = await stt_service.transcribe(audio_data)

            if SilenceDetector.detect_with_logging(stt_text, len(audio_data)):
                return None

            logger.info(f"STT completed: {stt_text}")
            return stt_text

        except Exception as e:
            logger.error(f"STT processing error: {e}", exc_info=True)
            return None

    @staticmethod
    async def save_to_history(
        session_id: str,
        speaker: str,
        text: str,
        audio_s3_url: Optional[str] = None
    ) -> None:
        """히스토리에 저장"""
        try:
            await SessionMessageHandler.append_message_async(
                session_id=session_id,
                speaker=speaker,
                text=text,
                audio_s3_url=audio_s3_url
            )
            logger.debug(f"Saved to history: {speaker}={text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save to history: {e}", exc_info=True)
            raise


class UtterancePersistence:
    """발화 저장 (Spring 2 연동)"""

    @staticmethod
    def schedule_save(
        session_id: str,
        text: str,
        utterance_index: int,
        speaker: str,
        audio_data: Optional[bytes] = None
    ) -> None:
        """비동기 발화 저장 스케줄"""
        asyncio.create_task(
            UtterancePersistence._save_with_retry(
                session_id, text, utterance_index, speaker, audio_data
            )
        )

    @staticmethod
    async def _save_with_retry(
        session_id: str,
        text: str,
        utterance_index: int,
        speaker: str,
        audio_data: Optional[bytes] = None,
        max_retries: int = 3
    ) -> None:
        """재시도 로직이 포함된 저장"""
        normalized_speaker = speaker.lower() if speaker else "user"

        for attempt in range(max_retries):
            try:
                await spring2_client.save_utterance(
                    session_id=session_id,
                    stt_text=text,
                    utterance_index=utterance_index,
                    speaker=normalized_speaker,
                    text=text,
                    audio_data=audio_data,
                )
                logger.info(
                    f"Utterance saved to Spring 2: "
                    f"session={session_id}, index={utterance_index}, speaker={normalized_speaker}"
                )
                return

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 지수 백오프
                    logger.warning(
                        f"Save failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to save utterance after {max_retries} attempts: {e}",
                        exc_info=True
                    )


class TextUtteranceProcessor:
    """텍스트 기반 발화 처리 (STT 없이)"""

    @staticmethod
    async def process_and_save(
        session_id: str,
        user_text: str,
        utterance_index: int
    ) -> None:
        """
        사용자 텍스트를 처리하고 저장

        Args:
            session_id: 세션 ID
            user_text: 사용자 입력 텍스트
            utterance_index: 발화 인덱스
        """
        try:
            # 히스토리 저장
            await UtteranceProcessor.save_to_history(
                session_id=session_id,
                speaker="user",
                text=user_text,
                audio_s3_url=None
            )

            # Spring 2에 비동기 저장
            UtterancePersistence.schedule_save(
                session_id=session_id,
                text=user_text,
                utterance_index=utterance_index,
                speaker="user",
                audio_data=None
            )

            logger.info(f"Text utterance processed: {user_text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to process text utterance: {e}", exc_info=True)
            raise