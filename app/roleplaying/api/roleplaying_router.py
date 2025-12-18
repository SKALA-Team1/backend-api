"""
Roleplaying Router
==================

목적: FastAPI 롤플레잉 기능의 모든 API 엔드포인트 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 모듈은 실시간 영어 회화 롤플레잉을 위한 모든 HTTP/WebSocket 엔드포인트를
정의합니다. FastAPI와 Spring 마이크로서비스 간의 통신을 조정하는 게이트웨이 역할.

마이크로서비스 통신 구조:

    Spring 1 (메인 게이트웨이)
    ├─ 사용자 인증/세션 관리
    ├─ ClientController → [SessionID 생성]
    └─ POST /internal/sessions/setup (FastAPI)
                    ↓
    FastAPI (이 모듈)
    ├─ 세션 정보 Redis 저장
    ├─ WebSocket URL 생성 및 반환
    └─ WebSocket 연결 대기

🔌 구현 엔드포인트:

    [헬스 체크]
    GET /health/ping
        상태: 200 OK
        목적: 서버 살아있음 확인

    [Slack 시나리오 분석] (Spring 2 → FastAPI)
    POST /internal/scenarios/analyze-conversation
        입력: AnalysisRequestDto (Slack 메시지 목록 + 사용자 정보)
        처리:
            1. 메시지들을 MessageRole로 변환
            2. SlackScenarioService에 비동기 호출
            3. LLM이 대화 분석 (주제, 상황 추출)
            4. 4개 시나리오 생성 (overview + 3개 role별)
        출력: AnalysisResultDto (주제정보 + 4개 시나리오)
        에러: 400 (빈 메시지), 500 (LLM 실패)

    [프롬프트 기반 시나리오 생성] (클라이언트 → FastAPI)
    POST /internal/scenarios/generate-from-prompt
        입력: PromptBasedScenarioRequestDto (역할/상황 자유입력)
        처리:
            1. 입력 검증 (Pydantic 자동)
            2. 사용자의 과거 시나리오 조회 (컨텍스트)
            3. LLM이 상황 강화, 제목 생성, 질문 생성
            4. 1개 시나리오 생성
        출력: PromptBasedScenarioResponseDto (1개 시나리오)
        에러: 400 (검증실패), 500 (생성실패)

    [세션 설정] (Spring 1 → FastAPI)
    POST /internal/sessions/setup
        입력: InternalSessionSetupRequest (sessionID, userID, scenarioID)
        처리:
            1. SessionService에 비동기 호출
            2. 시나리오 정보 조회 (DB)
            3. 세션 정보 Redis에 저장 (TTL 설정)
            4. WebSocket URL 생성 (WS_BASE_URL + /ws/roleplaying/{sessionID})
            5. 클라이언트에 전송할 정보 패킹
        출력: InternalSessionSetupResponse (sessionID, wsURL, scenario, expiresAt)
        에러: 404 (시나리오 없음), 500 (DB/Redis 오류)

    [실시간 롤플레잉] (WebSocket)
    WS /ws/roleplaying/{session_id}
        구현: handlers/ws_realtime_handler.py의 roleplaying_websocket() 함수

        인바운드 메시지 (Client → FastAPI):
            - INIT: 세션 초기화 (시나리오/역할 로드, 첫 질문 전송)
            - AUDIO_CHUNK: 오디오 바이너리 청크 (WAV, 16kHz, 16-bit, mono)
            - UTTERANCE_END: 발화 종료 신호 (STT 최종화, AI 응답 생성)
            - USER_TEXT: 텍스트 입력 (테스트/STT 없이 진행)
            - END_SESSION: 세션 종료 요청

        아웃바운드 메시지 (FastAPI → Client):
            - ACK: 메시지 수신 확인
            - AI_TEXT: AI 응답 텍스트 (고정 질문 또는 동적 생성)
            - AI_TEXT_STREAMING: AI 응답 스트리밍 (청크 단위 실시간 전송)
            - STT_PARTIAL: STT 부분 결과 (음성 인식 중 임시 결과)
            - STT_FINAL: STT 최종 결과 (오디오 처리 완료)
            - UTTERANCE_SAVED: 발화 저장 완료 (Spring 2 DB 저장 확인)
            - AI_TYPING: AI 응답 생성 중 (로딩 표시)
            - FEEDBACK: 피드백 점수 (발음, 문법, 맥락 적절성 점수 0-100)
            - FEEDBACK_STREAMING: 피드백 텍스트 스트리밍 (교정 제안 청크 전송)
            - RETRY_REQUIRED: 재시도 요청 (교정 필요시 같은 질문 반복)
            - SESSION_ENDED: 세션 종료 완료
            - ERROR: 오류 메시지

        상태관리:
            - 세션: Redis에 저장된 사용자/시나리오 정보 (TTL 자동 만료)
            - 턴 추적: AI 턴 카운트, 고정 질문 여부 (턴 1, 4, 7)
            - 대화: 사용자/AI 발화 히스토리 (컨텍스트용)
            - 피드백: 발음, 문법, 맥락 적절성 평가 점수
            - 재시도: 현재 질문 재시도 횟수 (최대 3회)

🏗️ 설계 원칙:

    1. Dependency Injection: services.dependencies에서 주입받음
    2. Async/Await: 모든 I/O 비동기 처리 (LLM, DB, Redis)
    3. SOLID 준수: 로직은 Service 계층, 라우터는 HTTP 계층만 담당
    4. 에러 처리: HTTPException으로 명확한 HTTP 상태 코드 반환
    5. 로깅: 주요 지점에서 request/response 로깅 (디버깅용)

⚠️ 중요한 구조:

    FastAPI 라우터 역할 분담:
    ├─ 이 파일: REST/내부 API 엔드포인트
    ├─ ws_realtime.py: WebSocket 엔드포인트 (실시간 대화)
    └─ services/: 모든 비즈니스 로직 (LLM, 세션, 피드백)

    마이크로서비스 책임:
    ├─ Spring 1: 사용자 인증, 세션 ID 생성, 호스팅
    ├─ Spring 2: DB 접근, Slack API, 데이터 관리
    └─ FastAPI: 실시간 통신, LLM 호출, 피드백 생성

의존성:
    - fastapi: 라우터 및 HTTP 처리
    - sqlalchemy: DB 접근 (시나리오, 주제 정보)
    - pydantic: 요청/응답 검증
    - services: 비즈니스 로직 (SlackScenarioService, SessionService 등)
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from app.roleplaying.api.api_schemas import (
    AnalysisRequestDto,
    AnalysisResultDto,
    MessageRole,
    InternalSessionSetupRequest,
    InternalSessionSetupResponse,
    PromptBasedScenarioRequestDto,
    PromptBasedScenarioResponseDto
)
from app.roleplaying.services.dependencies import (
    SlackScenarioServiceDep,
    PromptBasedScenarioServiceDep,
    SessionServiceDep
)
from app.config import settings
from app.core.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================
# Health Check Endpoints
# ============================================

@router.get("/health/ping")
async def ping():
    """
    서버 상태 확인 엔드포인트

    응답: {"status": "ok"} (200 OK)
    목적: 로드밸런서/모니터링에서 서버 살아있음 확인
    """
    return {"status": "ok"}




# ============================================
# Slack Scenario Analysis & Generation
# ============================================

@router.post("/internal/scenarios/analyze-conversation", response_model=AnalysisResultDto)
async def analyze_conversation(
    request: AnalysisRequestDto,
    slack_scenario_service: SlackScenarioServiceDep
):
    """
    Slack 대화를 분석하고 영어 연습 시나리오를 생성하는 엔드포인트

    Spring 2 (데이터 서버)에서 호출하는 내부 API.
    사용자의 Slack 메시지들을 받아 LLM이 분석하고 시나리오를 생성.

    처리 흐름:
        1. 입력 검증 (메시지 목록 비어있는지 확인)
        2. SlackMessageDto → MessageRole로 변환 (LLM 처리용)
        3. SlackScenarioService 호출 (비동기)
            - ConversationAnalyzer: 대화 주제/상황 추출
            - ScenarioGenerator: 4개 시나리오 생성 (overview + 3개 role)
        4. AnalysisResultDto로 응답

    Args:
        request: AnalysisRequestDto
            - userId: 사용자 ID
            - myRole: 사용자의 IT 역할
            - conversationDate: Slack 메시지 추출 날짜
            - messages: SlackMessageDto 목록 (timestamp, sender, text, myMessage)
            - aiRoles: 생성할 시나리오의 AI 역할 목록

        slack_scenario_service: SlackScenarioService 인스턴스 (의존성 주입)

    Returns:
        AnalysisResultDto:
            - subject: SubjectInfoDto (분석된 주제정보)
                - myRole, situation, conversationDate, messageCount
            - scenarios: List[ScenarioInfoDto] (4개 시나리오)
                - [0]: overview 시나리오
                - [1-3]: detail 시나리오 (역할별)

    Raises:
        HTTPException(400): 메시지 목록이 비어있을 때
        HTTPException(500): LLM 분석 실패, 서비스 오류 등

    예시:
        요청:
            {
                "userId": 123,
                "myRole": "Software Engineer",
                "conversationDate": "2024-12-02",
                "messages": [
                    {"timestamp": "2024-12-02T10:00:00Z", "senderName": "user", "text": "...", "myMessage": true},
                    {"timestamp": "2024-12-02T10:05:00Z", "senderName": "pm", "text": "...", "myMessage": false}
                ],
                "aiRoles": ["Project Manager", "Tech Lead", "QA Engineer"]
            }

        응답: 4개 시나리오 + 주제 정보

    주의:
        - 메시지 순서는 시간순으로 정렬되어 있어야 함 (보통 Spring 2에서 정렬 후 전송)
        - messageCount는 분석할 메시지 개수 (컨텍스트 크기 지표)
        - 각 시나리오는 정확히 3개의 고정 질문을 포함
    """
    # ========== 단계 1: 입력 검증 ==========
    # 메시지가 비어있으면 분석할 수 없으므로 400 에러 반환
    if not request.messages:
        logger.warning(f"Empty messages received for user {request.userId}")
        raise HTTPException(status_code=400, detail="No messages provided")

    # ========== 단계 2: 데이터 변환 ==========
    # SlackMessageDto를 LLM이 처리할 수 있는 MessageRole로 변환
    # MessageRole: LLM 메시지 히스토리 형식 (content, sender, mine)
    conversation_roles = [
        MessageRole(
            content=message.text,              # 메시지 내용
            sender=message.senderName,         # 발신자 (사람 이름)
            mine=bool(message.myMessage)       # 사용자 본인 발화 여부
        )
        for message in request.messages
    ]

    try:
        # ========== 단계 3: LLM 분석 및 생성 ==========
        # SlackScenarioService가 처리:
        # - ConversationAnalyzer: 주제/상황 추출
        # - ScenarioGenerator: 4개 시나리오 생성 (overview + 3개 role)
        # 모두 비동기로 처리되며, 병렬 처리 가능
        result = await slack_scenario_service.analyze_and_generate(
            request=request,                   # 원본 요청 (사용자 정보 포함)
            conversation_roles=conversation_roles  # 변환된 메시지들
        )

        logger.info(f"Successfully generated scenarios for user {request.userId}")
        return result

    except Exception as e:
        # LLM 호출 실패, 네트워크 오류, 기타 예상 외 오류
        logger.error(f"Failed to analyze conversation for user {request.userId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze conversation: {str(e)}"
        )


# ============================================
# Session Setup Endpoints
# ============================================

@router.post("/internal/sessions/setup", response_model=InternalSessionSetupResponse)
async def internal_setup_session(
    request: InternalSessionSetupRequest,
    session_service: SessionServiceDep,
    db: Session = Depends(get_db)
):
    """
    Spring 1 Gateway에서 호출하는 세션 설정 엔드포인트

    Spring 1이 사용자 세션을 생성하고, FastAPI에게 실시간 세션 정보를 등록하도록 요청.
    반환되는 WebSocket URL을 클라이언트에 제공하면 클라이언트가 연결.

    통신 흐름:
        1. Spring 1 ClientController: 사용자가 시나리오 선택
        2. Spring 1: sessionId 생성 (UUID)
        3. Spring 1: FastAPI POST /internal/sessions/setup 호출
        4. FastAPI: 세션을 Redis에 저장, WebSocket URL 생성, 응답
        5. Spring 1: 클라이언트에 WebSocket URL 제공
        6. 클라이언트: WebSocket 연결 수립

    Args:
        request: InternalSessionSetupRequest
            - sessionId: Spring 1이 생성한 세션 ID (UUID)
            - userId: 사용자 DB PK
            - scenarioId: 사용자가 선택한 시나리오 DB PK

        session_service: SessionService 인스턴스 (의존성 주입)

        db: SQLAlchemy 세션 (시나리오 정보 조회용, 자동 주입)

    Returns:
        InternalSessionSetupResponse
            - sessionId: 입력받은 sessionId (확인용)
            - wsUrl: 클라이언트가 연결할 WebSocket URL
            - scenario: 선택된 시나리오 상세정보
            - expiresAt: 세션 만료 시각

    Raises:
        HTTPException(404): 시나리오 ID가 DB에 없음
        HTTPException(500): Redis, DB 접근 오류

    중요:
        - sessionId는 Spring 1이 생성 (FastAPI는 그대로 사용)
        - Redis에 저장되는 정보로 세션 추적
        - TTL 설정으로 자동 만료 (expiresAt)
        - WebSocket 연결은 별도 ws_realtime_handler.py에서 처리
    """
    try:
        # SessionService가 처리하는 작업:
        # 1. scenarioId를 DB에서 조회하여 검증
        # 2. 시나리오 정보와 사용자 정보를 Redis에 저장
        # 3. TTL(Time To Live)을 설정하여 자동 만료 구성
        session_id, scenario, expires_at = await session_service.setup_session(
            session_id=request.sessionId,  # Spring 1에서 생성한 고유 ID
            user_id=request.userId,         # 사용자 DB PK
            scenario_id=request.scenarioId,  # 선택된 시나리오 DB PK
            db=db,                          # 시나리오 정보 조회용
            interaction_mode=request.interactionMode,  # Pass interaction mode
            voice_id=request.voiceId  # ElevenLabs Voice ID (선택적)
        )

        # WebSocket 연결 URL 생성
        # 예: wss://api.example.com/ws/roleplaying/session-uuid-12345
        base_ws_url = settings.WS_BASE_URL.rstrip("/")  # 마지막 슬래시 제거
        ws_url = f"{base_ws_url}/ws/roleplaying/{session_id}"

        logger.info(
            f"Session setup successfully: session_id={session_id}, "
            f"user_id={request.userId}, scenario_id={request.scenarioId}"
        )

        # 클라이언트에 반환할 응답 생성
        return InternalSessionSetupResponse(
            sessionId=session_id,        # Spring 1이 생성한 세션 ID (확인용)
            wsUrl=ws_url,                # 클라이언트가 연결할 WebSocket URL
            scenario=scenario,           # 선택된 시나리오 상세 정보
            expiresAt=expires_at        # 세션 유효 만료 시각
        )

    except ValueError as e:
        # 시나리오 ID가 DB에 없는 경우
        logger.warning(f"Scenario not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # 기타 예상 외 오류 (Redis 연결 실패, DB 오류 등)
        logger.error(f"Failed to setup session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup session: {str(e)}"
        )


# ============================================
# Prompt-Based Scenario Generation
# ============================================

@router.post("/internal/scenarios/generate-from-prompt", response_model=PromptBasedScenarioResponseDto)
async def generate_scenario_from_prompt(
    request: PromptBasedScenarioRequestDto,
    prompt_scenario_service: PromptBasedScenarioServiceDep,
    db: Session = Depends(get_db)
):
    """
    사용자가 직접 입력한 프롬프트로부터 롤플레잉 시나리오를 생성하는 엔드포인트

    Slack 분석과 달리, 사용자가 원하는 상황과 역할을 자유롭게 입력하여 시나리오 생성.
    클라이언트에서 직접 호출하는 API (Spring 1이 JWT 검증 후 FastAPI URL 반환).

    처리 흐름:
        1. 입력 검증 (Pydantic 자동)
            - userId: 양수
            - myRole: 1-100자
            - aiRole: 1-100자
            - situation: 1-500자
        2. 사용자의 과거 시나리오 조회 (DB, 컨텍스트용)
        3. LLM 처리:
            - ScenarioEnhancer: 상황 강화
            - 제목 생성
            - 3개 질문 생성
        4. PromptBasedScenarioResponseDto로 응답

    Args:
        request: PromptBasedScenarioRequestDto
            - userId: 사용자 DB PK (양수)
            - myRole: 사용자 역할 (예: "Software Engineer", "Product Manager")
            - aiRole: AI 역할 (예: "CEO", "HR Manager", "Marketing Lead")
            - situation: 롤플레이 상황 (예: "회사 성과 평가 면담")

        prompt_scenario_service: PromptBasedScenarioService 인스턴스 (의존성 주입)

        db: SQLAlchemy 세션 (과거 시나리오 조회용, 자동 주입)

    Returns:
        PromptBasedScenarioResponseDto:
            - scenario: ScenarioInfoDto (생성된 시나리오)
                - aiRole, topicType("direct"), title, fixedQuestions(3개), creationType("prompt")

    Raises:
        HTTPException(400): 입력 검증 실패 (ValueError)
            - userId가 0 이하
            - myRole/aiRole이 범위 벗어남
            - situation이 너무 짧거나 김
        HTTPException(500): LLM 생성 실패, 서비스 오류 등

    예시:
        요청:
            {
                "userId": 123,
                "myRole": "Senior Software Engineer",
                "aiRole": "CEO",
                "situation": "회사의 AI 도입 전략에 대해 경영진과 논의하는 상황"
            }

        응답:
            {
                "scenario": {
                    "aiRole": "CEO",
                    "topicType": "direct",
                    "title": "AI 전략 논의: CEO와의 기술 리더십 대화",
                    "fixedQuestions": [
                        "우리 회사에서 AI 도입을 고려하고 있는데, 기술적으로 어떤 준비가 필요할까요?",
                        "구체적인 도입 일정과 ROI 목표는 무엇인가요?",
                        "이 프로젝트를 성공하기 위해 우리 팀이 해야 할 가장 중요한 일은 무엇일까요?"
                    ],
                    "creationType": "prompt"
                }
            }

    주요 특징:
        - Slack 분석과 달리 단일 시나리오만 생성 (4개가 아님)
        - topicType은 항상 "direct" (사용자와 AI의 직접 대화)
        - creationType은 "prompt" (사용자 입력 기반)
        - 사용자의 과거 시나리오를 컨텍스트로 활용하여 중복 최소화
    """
    try:
        # ========== 단계 1: 입력 검증 ==========
        # Pydantic이 자동으로 수행:
        # - userId > 0 확인
        # - myRole, aiRole: 1-100자
        # - situation: 1-500자
        logger.info(
            f"Generating scenario from prompt for user {request.userId}: "
            f"my_role={request.myRole}, ai_role={request.aiRole}"
        )

        # ========== 단계 2: 시나리오 생성 ==========
        # PromptBasedScenarioService가 처리:
        # - 사용자의 과거 시나리오 조회 (중복 방지용)
        # - ScenarioEnhancer: 상황 강화
        # - 제목 생성 (역할 and 상황 함축)
        # - 3개 질문 생성 (Turn 1, Turn 5, Turn 10)
        scenario = await prompt_scenario_service.generate_from_prompt(
            user_id=request.userId,     # 사용자 DB PK
            my_role=request.myRole,     # 사용자의 역할
            ai_role=request.aiRole,     # AI의 역할
            situation=request.situation, # 롤플레이 상황
            db=db                       # 과거 시나리오 컨텍스트용
        )

        logger.info(f"Successfully generated scenario for user {request.userId}")

        # ========== 단계 3: 응답 ==========
        return PromptBasedScenarioResponseDto(scenario=scenario)

    except ValueError as e:
        # 입력 검증 실패 (Pydantic 또는 비즈니스 로직)
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # 예상 외 오류 (LLM 호출 실패, 네트워크 오류 등)
        logger.error(
            f"Failed to generate scenario for user {request.userId}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate scenario: {str(e)}"
        )
