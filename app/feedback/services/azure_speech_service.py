"""
Azure Speech Service - 발음 평가 서비스

역할:
    - Azure Speech SDK를 사용하여 음성 파일의 발음을 평가
    - 4가지 평가 기준: Accuracy, Fluency, Completeness, Pronunciation
    - MP3/WAV 파일 또는 URL을 입력받아 평가 수행

평가 기준:
    - AccuracyScore: 발음의 정확도 (0-100)
    - FluencyScore: 말하기의 유창성 (0-100)
    - CompletenessScore: 문장 완성도 (0-100)
    - PronScore: 종합 발음 점수 (0-100)
"""

import os
import tempfile
import logging
from typing import Optional
from dataclasses import dataclass

import azure.cognitiveservices.speech as speechsdk

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PronunciationResult:
    """발음 평가 결과 데이터 클래스"""
    accuracy_score: float  # 정확도
    fluency_score: float  # 유창성
    completeness_score: float  # 완성도
    pronunciation_score: float  # 종합 발음 점수
    recognized_text: str  # 인식된 텍스트
    words: list[dict]  # 단어별 상세 평가


class AzureSpeechService:
    """Azure Speech 발음 평가 서비스"""

    def __init__(self):
        self.speech_key = settings.azure_speech_key
        self.speech_region = settings.azure_speech_region

        if not self.speech_key:
            raise ValueError("AZURE_SPEECH_KEY is not configured")

    def _create_speech_config(self) -> speechsdk.SpeechConfig:
        """Speech Config 생성"""
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        speech_config.speech_recognition_language = "en-US"
        return speech_config

    def evaluate_pronunciation_from_file(
        self,
        audio_file_path: str,
        reference_text: str
    ) -> Optional[PronunciationResult]:
        """
        로컬 파일에서 발음 평가 수행

        Args:
            audio_file_path: 음성 파일 경로 (WAV/MP3)
            reference_text: 참조 텍스트 (사용자가 읽어야 할 문장)

        Returns:
            PronunciationResult: 발음 평가 결과
        """
        try:
            speech_config = self._create_speech_config()

            # 오디오 설정
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

            # 발음 평가 설정
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Word,
                enable_miscue=True
            )

            # Speech Recognizer 생성
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )

            # 발음 평가 적용
            pronunciation_config.apply_to(speech_recognizer)

            # 인식 수행
            result = speech_recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)

                # 단어별 상세 결과
                words = []
                for word in pronunciation_result.words:
                    words.append({
                        "word": word.word,
                        "accuracy_score": word.accuracy_score,
                        "error_type": word.error_type
                    })

                return PronunciationResult(
                    accuracy_score=pronunciation_result.accuracy_score,
                    fluency_score=pronunciation_result.fluency_score,
                    completeness_score=pronunciation_result.completeness_score,
                    pronunciation_score=pronunciation_result.pronunciation_score,
                    recognized_text=result.text,
                    words=words
                )

            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning(f"No speech recognized: {result.no_match_details}")
                return None

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"Speech recognition canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation.error_details}")
                return None

        except Exception as e:
            logger.error(f"Pronunciation evaluation failed: {e}")
            raise

    def evaluate_pronunciation_from_bytes(
        self,
        audio_bytes: bytes,
        reference_text: str,
        file_format: str = "wav"
    ) -> Optional[PronunciationResult]:
        """
        바이트 데이터에서 발음 평가 수행

        Args:
            audio_bytes: 음성 데이터 바이트
            reference_text: 참조 텍스트
            file_format: 파일 형식 (wav, mp3)

        Returns:
            PronunciationResult: 발음 평가 결과
        """
        # 임시 파일로 저장 후 평가
        with tempfile.NamedTemporaryFile(
            suffix=f".{file_format}",
            delete=False
        ) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            return self.evaluate_pronunciation_from_file(temp_path, reference_text)
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def evaluate_without_reference(
        self,
        audio_file_path: str
    ) -> Optional[PronunciationResult]:
        """
        참조 텍스트 없이 발음 평가 (자유 발화)

        Args:
            audio_file_path: 음성 파일 경로

        Returns:
            PronunciationResult: 발음 평가 결과
        """
        try:
            speech_config = self._create_speech_config()
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)

            # 참조 텍스트 없는 발음 평가 설정
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Word
            )
            pronunciation_config.enable_prosody_assessment()

            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            pronunciation_config.apply_to(speech_recognizer)

            result = speech_recognizer.recognize_once()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)

                words = []
                for word in pronunciation_result.words:
                    words.append({
                        "word": word.word,
                        "accuracy_score": word.accuracy_score,
                        "error_type": word.error_type
                    })

                return PronunciationResult(
                    accuracy_score=pronunciation_result.accuracy_score,
                    fluency_score=pronunciation_result.fluency_score,
                    completeness_score=pronunciation_result.completeness_score,
                    pronunciation_score=pronunciation_result.pronunciation_score,
                    recognized_text=result.text,
                    words=words
                )

            logger.warning(f"Recognition result: {result.reason}")
            return None

        except Exception as e:
            logger.error(f"Pronunciation evaluation failed: {e}")
            raise


# 싱글톤 인스턴스
_azure_speech_service: Optional[AzureSpeechService] = None


def get_azure_speech_service() -> AzureSpeechService:
    """Azure Speech Service 인스턴스 반환"""
    global _azure_speech_service
    if _azure_speech_service is None:
        _azure_speech_service = AzureSpeechService()
    return _azure_speech_service
