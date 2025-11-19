"""
Roleplaying Router
==================
AI 롤플레잉(시나리오 기반 대화) 관련 API 엔드포인트를 정의하는 라우터 모듈.

역할:
    - 시나리오 시작, 메시지 주고받기, 상태 조회, 종료 등 모든 흐름의 진입점 제공.
    - WebSocket 및 HTTP 기반 요청을 서비스 계층으로 전달.

엔드포인트:
    - 사용자 정보
        - GET /roleplaying/userInfo
        - Request Spec
            - Headers: Authorization: Bearer <access_token>
        - Response Spec
            {
              "id": "user_001",
              "name": "땡땡",
              "email": "user@example.com",
              "using_days": 12,              // 앱 사용 n일째
              "profile_image_url": "https://.../avatar.png",
              "integrations": {
                "slack_connected": true,
                "github_connected": false
          }

    - 사용자 이용 데이터 조회
        - GET /roleplaying/userStatics
        - Request Spec
            - Headers: Authorization: Bearer <access_token>
        - Response Spec
            {
              "conversation_minutes": 100,
              "team_rank": 3,
              "personal_rank": 10,
              "team_name": "Platform Team",
              "updated_at": "2025-11-13T09:00:00Z"
            }

    - 롤플레잉 리스트 조회
        - GET /roleplaying/roleplayList
        - Request Spec
            - Headers: Authorization: Bearer <access_token>
            - Query Params
                - page
                - size
                - status
                - source_type
                - order
                - created_from
                - created_to
        - Response Spec
            {
              "items": [
                {
                  "id": "rp_101",
                  "title": "어제 스탠드업 미팅 기반 롤플레이",
                  "summary": "팀 스탠드업에서 나왔던 이슈를 영어로 다시 이야기해보는 시나리오입니다.",
                  "source_type": "slack",          // "slack" | "github" | "prompt" ...
                  "status": "READY",               // "READY" | "IN_PROGRESS" | "FINISHED" | "CREATING" ...
                  "created_at": "2025-11-12T09:00:00Z",
                  "updated_at": "2025-11-12T10:30:00Z"
                }
              ],
              "page": 1,
              "size": 10,
              "total": 25
            }

    - 프롬프트 기반 롤플레잉 생성
        - POST /roleplaying/prompt_create
        - Request Spec
            - Headers
                - Authorization: Bearer <access_token>
                - Content-Type: application/json
            - Body
                {
                  "ai_role": "면접관으로서 질문하기",
                  "user_role": "지원자로서 답변하기",
                  "situation": "AI 회사 면접 상황에서 자기소개 연습",
                  "total_turns": 10,
                }
        - Response Spec
            {
              "roleplay": {
                "id": "rp_501",
                "title": "AI 회사 면접 자기소개 롤플레이",
                "summary": "면접관과 지원자 역할로 진행되는 자기소개 연습 롤플레이입니다.",
                "source_type": "prompt",
                "status": "READY",
                "created_at": "2025-11-13T10:00:00Z"
              },
              "turn_plan": {
                "total_turns": 10,
                "key_turn_indices": [1, 5, 10],
                "key_turns": [
                  {
                    "turn_index": 1,
                    "speaker": "ai",
                    "turn_type": "OPENING",
                    "goal": "라포 형성과 긴장 완화",
                    "question_template": "간단하게 자기소개를 해 주세요."
                  },
                  {
                    "turn_index": 5,
                    "speaker": "ai",
                    "turn_type": "DEEP_DIVE",
                    "goal": "핵심 경험을 파고들기",
                    "question_template": "가장 도전적이었던 프로젝트와 역할을 설명해 주세요."
                  },
                  {
                    "turn_index": 10,
                    "speaker": "ai",
                    "turn_type": "WRAP_UP",
                    "goal": "회고 및 마무리",
                    "question_template": "오늘 대화에서 배운 점이나 아쉬운 점이 있나요?"
                  }
                ]
              }
            }

    - 롤플레잉 세션 시작
        - POST /roleplaying/{roleplayingId}/session/start
        - Request Spec
            - Headers
                - Authorization: Bearer <access_token>
                - Path Params: roleplayingId
        - Response Spec
            {
              "session": {
                "session_id": "rs_9001",
                "roleplay_id": "rp_501",
                "status": "IN_PROGRESS",
                "current_turn_index": 1,
                "total_turns": 10,
                "created_at": "2025-11-13T10:05:00Z"
              },
              "first_ai_turn": {
                "turn_index": 1,
                "speaker": "ai",
                "is_key_turn": true,
                "message": "간단하게 자기소개를 해 주세요."
              }
            }

    - 롤플레잉 다음 턴 생성
        - POST /roleplaying/{sessionId}/nextTurn
        - Request Spec
            - Headers
                - Authorization: Bearer <access_token>
            - Path Params: sessionId
            - Body
                {
                  "last_turn_index": 2,
                  "last_user_message": "저는 3년차 백엔드 개발자이고, 최근에는 영어 롤플레잉 서비스를 만들고 있어요."
                }
        - Response Spec
            - 아직 턴이 남아 있을 때(IN_PROGRESS)
                {
                  "next_turn": {
                    "turn_index": 3,
                    "speaker": "ai",
                    "is_key_turn": false,
                    "message": "그 서비스를 만들면서 가장 어려웠던 점은 무엇이었나요?",
                    "source": "dynamic_llm"
                  },
                  "session": {
                    "session_id": "rs_9001",
                    "current_turn_index": 3,
                    "remaining_turns": 8,
                    "status": "IN_PROGRESS"
                  }
                }
            - 마지막 턴까지 끝나서 세션이 종료될 때
                {
                  "next_turn": null,
                  "session": {
                    "session_id": "rs_9001",
                    "current_turn_index": 10,
                    "remaining_turns": 0,
                    "status": "FINISHED"
                  }
                }

    - 세션 대화 리스트 조회(오른쪽 패널용)
        - GET /roleplaying/{sessionId}/messages
        - Request Spec
            - Headers
                - Authorization: Bearer <access_token>
            - Path Params: sessionId
            - Query Params
                - page
                - size
        - Response Spec
            {
              "session_id": "rs_9001",
              "items": [
                {
                  "turn_index": 1,
                  "speaker": "ai",
                  "message": "간단하게 자기소개를 해 주세요.",
                  "created_at": "2025-11-13T11:10:00Z"
                },
                {
                  "turn_index": 2,
                  "speaker": "user",
                  "message": "저는 3년차 백엔드 개발자이고...",
                  "created_at": "2025-11-13T11:11:10Z"
                }
              ],
              "page": 1,
              "size": 50,
              "total": 12
            }
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
