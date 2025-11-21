"""
Roleplaying Router
==================
AI 롤플레잉(시나리오 기반 대화) 관련 API 엔드포인트를 정의하는 라우터 모듈.

역할:
    - WebSocket을 통한 실시간 음성 기반 롤플레잉 지원
    - STT (Deepgram), AI 응답 생성, 세션 관리

구현된 엔드포인트:

    1. Health Check
        - GET /health/ping
        - 역할: 서버 상태 확인

    2. 내부 API (Spring 2에서 호출)
        - POST /internal/scenarios/analyze-conversation
        - 역할: Slack 대화 분석 및 시나리오 생성

    3. 세션 생성 (HTTP)
        - POST /sessions
        - 역할: 롤플레잉 세션 생성, WebSocket URL 반환

    4. 실시간 대화 (WebSocket)
        - WS /ws/roleplaying/{session_id}
        - 역할: 음성 입력, STT, AI 응답, 세션 관리
        - 메시지 타입:
            - INIT: 세션 초기화
            - AUDIO_CHUNK: 오디오 청크 전송
            - UTTERANCE_END: 발화 종료
            - USER_TEXT: 텍스트 입력 (테스트용)
            - END_SESSION: 세션 종료

참고:
    - 추가 REST API (userInfo, roleplayList 등)는 Spring 2에서 구현
    - FastAPI는 WebSocket + STT + AI 응답에 집중
    - 데이터 관리는 Spring 2 책임
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from app.roleplaying.schemas import (
    AnalysisRequestDto,
    AnalysisResultDto,
    MessageRole,
    SessionCreateRequest,
    SessionCreateResponse
)
from app.roleplaying.services.slack_scenario_service import SlackScenarioService
from app.config import settings
from app.roleplaying.services.session_service import session_service
from app.core.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health/ping")
async def ping():
    return {"status": "ok"}


@router.post("/internal/scenarios/analyze-conversation", response_model=AnalysisResultDto)
async def analyze_conversation(request: AnalysisRequestDto):
    """
    Slack 대화를 분석하고 영어 연습 시나리오를 생성합니다.

    Spring 2 서버에서 호출하는 내부 API입니다.

    Args:
        request: Slack 메시지 및 사용자 정보

    Returns:
        분석된 주제 정보 + 6개의 시나리오

    Raises:
        400: 메시지가 비어있을 때
        500: LLM 분석 실패 또는 기타 서버 오류
    """
    # 입력 검증
    if not request.messages:
        logger.warning(f"Empty messages received for user {request.userId}")
        raise HTTPException(status_code=400, detail="No messages provided")

    conversation_roles = [
        MessageRole(
            content=message.text,
            sender=message.senderName,
            mine=bool(message.myMessage)
        )
        for message in request.messages
    ]

    try:
        # 시나리오 서비스 실행
        service = SlackScenarioService()
        result = await service.analyze_and_generate(
            request=request,
            conversation_roles=conversation_roles
        )

        logger.info(f"Successfully generated scenarios for user {request.userId}")
        return result

    except Exception as e:
        logger.error(f"Failed to analyze conversation for user {request.userId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze conversation: {str(e)}"
        )


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    롤플레잉 세션을 생성합니다.

    DB에서 시나리오를 조회하고, Redis에 세션 정보를 저장한 후,
    WebSocket 연결 URL을 반환합니다.
    """
    try:
        session_id, scenario, expires_at = await session_service.create_session(
            user_id=request.userId,
            scenario_id=request.scenarioId,
            db=db,
            provided_session_id=request.sessionId
        )

        base_ws_url = settings.WS_BASE_URL.rstrip("/")
        ws_url = f"{base_ws_url}/ws/roleplaying/{session_id}"

        logger.info(
            f"Session created successfully: session_id={session_id}, "
            f"user_id={request.userId}, scenario_id={request.scenarioId}"
        )

        return SessionCreateResponse(
            session_id=session_id,
            ws_url=ws_url,
            scenario=scenario,
            expires_at=expires_at
        )

    except ValueError as e:
        logger.warning(f"Scenario not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )
