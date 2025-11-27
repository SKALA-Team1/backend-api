"""
📄 파일명: router.py
📌 역할: FastAPI 라우터 정의. 피드백 관련 API 엔드포인트 제공.
🧩 관련 모듈:
  - services/*.py: 실제 로직을 수행하는 서비스 계층
  - schemas.py: 요청/응답 검증 및 직렬화
🧠 주요 엔드포인트:
  - POST /feedback/audio/batch  → 여러 오디오 파일 배치 피드백 생성
  - GET /feedback/session/{id}  → 세션 전체 피드백 조회

흐름:
  FastAPI (피드백 생성) → Spring API (DB 저장) → MySQL
"""

import os
import tempfile
import logging

from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.feedback.schemas import (
    TurnFeedbackRequest,
    TurnFeedbackResponse,
    SessionFeedbackResponse,
    BatchAudioFeedbackResponse,
    SimpleTurnFeedback,
    ScoreDetail
)
from app.feedback.services.feedback_service import get_feedback_service
from app.feedback.services.openai_feedback_service import get_openai_feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/health/ping")
async def ping():
    """헬스 체크"""
    return {"status": "ok"}


@router.get("/session/{session_id}", response_model=SessionFeedbackResponse)
async def get_session_feedback(
    session_id: int,
    scenario_id: int,
):
    """
    세션 전체 피드백 조회

    세션의 모든 턴(짝수 turn_index만)에 대한 피드백을 조회합니다.
    평균 점수와 턴별 상세 피드백을 포함합니다.
    Spring API를 통해 조회합니다.
    """
    try:
        service = get_feedback_service()
        result = await service.get_session_feedback(session_id, scenario_id)
        return result
    except Exception as e:
        logger.error(f"Session feedback retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio/batch", response_model=BatchAudioFeedbackResponse)
async def create_batch_feedback_from_audio(
    audio_files: List[UploadFile] = File(..., description="여러 개의 MP3 또는 WAV 오디오 파일 (파일명 순서 = 턴 순서)"),
    session_id: str = Form(..., description="세션 ID (UUID 문자열)"),
    scenario_id: int = Form(..., description="시나리오 ID"),
):
    """
    여러 오디오 파일 일괄 업로드 후 피드백 생성

    여러 개의 MP3/WAV 파일을 한 번에 업로드하면:
    1. scenario_message 테이블에서 짝수 turn_index 메시지 자동 조회
    2. 각 파일에 대해 Azure Speech로 발음 평가
    3. OpenAI로 종합 피드백 + 추천 문장 생성
    4. Spring API를 통해 DB에 저장

    파일 순서 = 턴 번호 순서 (0, 2, 4, 6, ...)
    모든 음성은 사용자 발화입니다.

    메시지는 DB에서 자동으로 가져옵니다.
    """
    service = get_feedback_service()

    # 1. DB에서 세션의 메시지 조회 (짝수 turn_index = 사용자 발화)
    try:
        messages = await service.get_session_messages(session_id, scenario_id)
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"세션 메시지 조회 실패: {e}"
        )

    # 짝수 turn_index만 필터 (사용자 발화)
    user_messages = [m for m in messages if m["turn_index"] % 2 == 0]

    # 파일 개수와 메시지 개수 확인
    if len(audio_files) != len(user_messages):
        raise HTTPException(
            status_code=400,
            detail=f"오디오 파일 수({len(audio_files)})와 DB의 사용자 발화 수({len(user_messages)})가 일치하지 않습니다."
        )

    results = []
    temp_paths = []

    try:
        # 모든 파일을 임시 저장
        for i, audio_file in enumerate(audio_files):
            filename = audio_file.filename or f"audio_{i}.mp3"
            ext = filename.split(".")[-1].lower()

            if ext not in ["mp3", "wav"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"파일 {filename}: 지원하지 않는 파일 형식입니다. MP3 또는 WAV 파일만 업로드 가능합니다."
                )

            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_paths.append(temp_file.name)

        # 각 파일에 대해 피드백 생성
        for i, temp_path in enumerate(temp_paths):
            user_msg = user_messages[i]
            turn_number = user_msg["turn_index"]

            # 이전 턴(AI 질문) 가져오기
            system_message = ""
            if turn_number > 0:
                prev_messages = [m for m in messages if m["turn_index"] == turn_number - 1]
                if prev_messages:
                    system_message = prev_messages[0].get("content", "")

            request = TurnFeedbackRequest(
                session_id=session_id,
                scenario_id=scenario_id,
                turn_number=turn_number,
                user_message=user_msg.get("content", ""),
                system_message=system_message,
                audio_file_path=temp_path
            )

            try:
                result = await service.generate_turn_feedback(request)
                results.append(result)
                logger.info(f"Batch feedback {i+1}/{len(temp_paths)} completed: turn={turn_number}")
            except Exception as e:
                logger.error(f"Batch feedback failed for turn {turn_number}: {e}")
                results.append(None)

        # 성공한 결과만 필터링
        successful_results = [r for r in results if r is not None]

        # ========== 턴별 추천 문장만 추출 (주석처리: 종합피드백과 Azure 평가만 사용) ==========
        # turn_feedbacks = [
        #     SimpleTurnFeedback(
        #         turn_number=r.turn_number,
        #         user_message=r.user_message,
        #         system_message=r.system_message,
        #         suggested_sentence=r.suggested_sentence
        #     )
        #     for r in successful_results
        # ]
        turn_feedbacks = []  # 빈 리스트로 대체

        # ========== 전체 대화 종료 후 통합 피드백 ==========
        # 평균 점수 계산
        if successful_results:
            total_accuracy = sum(r.accuracy.score for r in successful_results)
            total_fluency = sum(r.fluency.score for r in successful_results)
            total_completeness = sum(r.completeness.score for r in successful_results)
            total_pronunciation = sum(r.pronunciation.score for r in successful_results)

            count = len(successful_results)
            avg_accuracy_score = round(total_accuracy / count, 2)
            avg_fluency_score = round(total_fluency / count, 2)
            avg_completeness_score = round(total_completeness / count, 2)
            avg_pronunciation_score = round(total_pronunciation / count, 2)
            overall_score = round((avg_accuracy_score + avg_fluency_score + avg_completeness_score + avg_pronunciation_score) / 4, 2)
        else:
            avg_accuracy_score = avg_fluency_score = avg_completeness_score = avg_pronunciation_score = overall_score = 0.0

        # 점수를 레벨로 변환하는 헬퍼 함수
        def score_to_level(score: float) -> str:
            if score >= 90:
                return "Excellent"
            elif score >= 75:
                return "Good"
            elif score >= 60:
                return "Fair"
            elif score >= 40:
                return "Poor"
            else:
                return "VeryPoor"

        # ScoreDetail 객체 생성
        avg_accuracy = ScoreDetail(score=avg_accuracy_score, level=score_to_level(avg_accuracy_score))
        avg_fluency = ScoreDetail(score=avg_fluency_score, level=score_to_level(avg_fluency_score))
        avg_completeness = ScoreDetail(score=avg_completeness_score, level=score_to_level(avg_completeness_score))
        avg_pronunciation = ScoreDetail(score=avg_pronunciation_score, level=score_to_level(avg_pronunciation_score))

        # 최종 종합 피드백 생성 (5줄)
        final_feedback = ""
        if successful_results:
            try:
                openai_service = get_openai_feedback_service()
                avg_scores = {
                    "avg_accuracy": avg_accuracy_score,
                    "avg_fluency": avg_fluency_score,
                    "avg_completeness": avg_completeness_score,
                    "avg_pronunciation": avg_pronunciation_score,
                    "overall_score": overall_score
                }
                # 주석처리: suggested_sentence, grammar_notes 제외
                # turn_summaries = [
                #     {
                #         "turn_number": r.turn_number,
                #         "user_message": r.user_message,
                #         "suggested_sentence": r.suggested_sentence,
                #         "grammar_notes": r.grammar_notes
                #     }
                #     for r in successful_results
                # ]
                turn_summaries = [
                    {
                        "turn_number": r.turn_number,
                        "user_message": r.user_message
                    }
                    for r in successful_results
                ]
                final_feedback = openai_service.generate_final_feedback(avg_scores, turn_summaries)
                logger.info("Final feedback generated successfully")
            except Exception as e:
                logger.error(f"Failed to generate final feedback: {e}")
                final_feedback = "최종 피드백 생성에 실패했습니다."

        return BatchAudioFeedbackResponse(
            session_id=session_id,
            scenario_id=scenario_id,
            total_files=len(audio_files),
            processed_count=len(successful_results),
            failed_count=len(audio_files) - len(successful_results),
            turn_feedbacks=turn_feedbacks,
            avg_accuracy=avg_accuracy,
            avg_fluency=avg_fluency,
            avg_completeness=avg_completeness,
            avg_pronunciation=avg_pronunciation,
            overall_score=overall_score,
            final_feedback=final_feedback
        )

    finally:
        # 모든 임시 파일 삭제
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                os.remove(temp_path)
