"""
Roleplaying Schemas
===================

📋 목적: API 요청/응답 데이터 검증 및 직렬화
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 모듈은 FastAPI 애플리케이션의 모든 입출력 데이터를 Pydantic을 통해
타입 검증하고 직렬화/역직렬화하는 스키마(DTO)를 정의합니다.

주요 역할:
    1. 사용자 요청 데이터 검증 (클라이언트 → 서버)
    2. API 응답 데이터 구조화 (서버 → 클라이언트)
    3. 내부 마이크로서비스 간 데이터 전송 (Spring 1 ↔ FastAPI)

주요 스키마 그룹:

    [Slack 기반 시나리오 생성 흐름]
    - SlackMessageDto: Slack에서 추출한 메시지 정보
    - AnalysisRequestDto: Spring 2에서 전달받는 Slack 대화 분석 요청
    - AnalysisResultDto: FastAPI가 생성한 시나리오들을 Spring 2로 반환

    [사용자 프롬프트 기반 시나리오 생성]
    - PromptBasedScenarioRequestDto: 사용자의 직접 입력 요청
    - PromptBasedScenarioResponseDto: 생성된 시나리오 응답

    [세션 관리]
    - SessionCreateResponse: 웹소켓 연결용 세션 생성 응답
    - InternalSessionSetupRequest/Response: Spring 1과의 내부 통신용

    [공통 데이터 구조]
    - ScenarioInfoDto: 시나리오의 핵심 정보
    - ScenarioDetail: 세션 관련 상세 시나리오 정보

설계 원칙:
    - Type hints를 통한 자동 문서화
    - Field(..., description=...) 으로 각 필드에 명확한 설명 제공
    - min_length, max_length 등으로 유효성 검증
    - 마이크로서비스 간 API 계약(Contract) 명시

의존성:
    - pydantic (데이터 검증 및 직렬화)
    - datetime (시간 정보 처리)
"""

from datetime import date, datetime
from typing import List
from pydantic import BaseModel, Field


# =====================================================
# Slack 시나리오 생성 관련 스키마
# =====================================================
#
# Slack 대화 분석 흐름:
#   1. Spring 2가 Slack API에서 메시지 추출
#   2. AnalysisRequestDto에 담아 FastAPI로 전송
#   3. FastAPI가 대화를 분석하고 시나리오 생성
#   4. AnalysisResultDto로 생성된 시나리오 4개를 Spring 2로 반환
#
# 각 DTO의 역할:
#   - SlackMessageDto: 원본 메시지 정보 (사람 → 사람 대화)
#   - MessageRole: LLM 처리용 정규화된 메시지 (분석 중간 형태)
#   - AnalysisRequestDto: 분석 요청 패킷 (Spring 2 → FastAPI)
#   - SubjectInfoDto: 분석된 주제/상황 정보
#   - ScenarioInfoDto: 생성된 시나리오 (1개)
#   - AnalysisResultDto: 최종 응답 (4개 시나리오)

class SlackMessageDto(BaseModel):
    """
    Slack 메시지 정보 DTO

    Spring 2에서 Slack API를 통해 추출한 원본 메시지 데이터.
    타임스탐프, 발신자, 내용을 포함하고, 사용자 본인 발화 여부를 표시함.
    """
    timestamp: datetime = Field(..., description="메시지 전송 시각 (ISO 8601)")
    senderName: str = Field(..., description="메시지 발신자 이름")
    text: str = Field(..., description="메시지 내용")
    myMessage: bool | None = Field(
        default=False,
        description="해당 메시지가 사용자 본인의 발화인지 여부"
    )


class MessageRole(BaseModel):
    """
    LLM 처리용 정규화된 메시지 정보

    SlackMessageDto를 LLM이 분석할 수 있도록 변환한 중간 형태.
    원본 메시지의 발신자/내용 정보와 해당 발화가 사용자인지 여부를 명시.
    """
    # LLM의 메시지 히스토리에 포함될 메시지 내용 (정규화/정제된 텍스트)
    content: str = Field(..., description="메시지 텍스트")
    # 메시지 발신자 식별용 이름 또는 ID (Slack username 등)
    sender: str = Field(..., description="발화자 이름")
    # 사용자 본인이 발화한 메시지인지 여부 (맥락 파악용)
    mine: bool = Field(default=False, description="사용자 본인 발화 여부")


class AnalysisRequestDto(BaseModel):
    """
    Slack 대화 분석 요청 DTO

    Spring 2에서 FastAPI로 전송하는 요청 패킷.
    특정 날짜의 Slack 메시지 목록과 사용자 정보를 포함하여,
    LLM이 이를 기반으로 시나리오를 분석/생성하도록 요청함.

    처리 흐름:
        1. Spring 2에서 사용자의 Slack 메시지 추출
        2. 해당 날짜의 모든 메시지를 SlackMessageDto 목록으로 변환
        3. 사용자의 DB 정보 (userId, myRole) 포함
        4. 생성할 시나리오의 AI 역할 목록 지정
        5. FastAPI의 /analyze 엔드포인트로 POST
    """
    # 데이터베이스에 등록된 사용자 ID (PK)
    userId: int = Field(..., description="사용자 ID")
    # 사용자의 IT 직무 역할 (예: Software Engineer, Tech Lead, QA Engineer)
    # 이미 DB에서 제공되므로 LLM이 분석할 필요 없음
    myRole: str = Field(..., description="사용자의 직무 역할 (DB에서 제공, LLM 분석 불필요)")
    # Slack 메시지를 추출한 날짜 (예: 2024-12-02)
    conversationDate: date = Field(..., description="대화 날짜 (LocalDate)")
    # 해당 날짜에 Slack에서 추출한 모든 메시지 목록
    messages: List[SlackMessageDto] = Field(..., description="해당 날짜의 Slack 메시지 목록")
    # 생성할 시나리오의 대상 역할들 (예: ["Project Manager", "Tech Lead", "QA Engineer"])
    aiRoles: List[str] = Field(..., description="시나리오 생성할 AI 역할 목록")


class SubjectInfoDto(BaseModel):
    """
    Slack 대화에서 분석/추출한 주제 정보 DTO

    LLM이 Slack 메시지들을 분석하여 도출한 주제/상황 정보.
    사용자의 역할, 대화의 핵심 주제, 그리고 메시지 통계를 포함함.
    """
    # LLM이 대화 내용으로부터 추론한 사용자의 역할 (AnalysisRequestDto의 myRole과 비교용)
    myRole: str = Field(..., description="대화에서 유추한 사용자 역할")
    # 대화의 핵심 주제 및 상황을 1-2문장으로 요약한 텍스트
    situation: str = Field(..., description="대화 주제 및 상황 (1-2문장)")
    # 원본 메시지 추출 날짜
    conversationDate: date = Field(..., description="대화 날짜")
    # 분석 대상이 된 Slack 메시지의 총 개수 (대화의 규모 표시)
    messageCount: int = Field(..., description="메시지 개수")


class ScenarioInfoDto(BaseModel):
    """
    생성된 시나리오의 핵심 정보 DTO

    LLM이 생성한 하나의 시나리오를 나타냄. 이 정보는:
    - 세션 생성 시 클라이언트에 반환됨
    - DB에 저장됨
    - 클라이언트가 시나리오를 선택할 때 참조됨

    시나리오의 완전한 정보는 이 DTO + 세션 중에 필요한 컨텍스트로 구성됨.
    """
    # AI가 담당할 직무 역할 (예: "Project Manager", "Tech Lead", "QA Engineer")
    # IT 업무 맥락의 역할 이름으로 구성
    aiRole: str = Field(..., description="AI 역할 (Project Manager, Tech Lead, QA Engineer)")
    # 시나리오의 깊이 또는 범위 (overview = 전체 상황 개요, detail = 특정 역할별 상세 시나리오)
    topicType: str = Field(..., description="토픽 타입 (overview, detail)")
    # 사용자가 시나리오 선택 시 보게 될 제목 (최대 80자, 역할과 상황을 함축적으로 표현)
    title: str = Field(..., max_length=80, description="시나리오 제목")
    # 롤플레이 중에 고정으로 나올 3개의 질문
    # - 질문 1 (Turn 1): 대화 시작 (Conversation Starter)
    # - 질문 2 (Turn 4): 심화 및 전환 (Deepening & Transition)
    # - 질문 3 (Turn 7): 마무리 (Wrap-up & Closure)
    fixedQuestions: List[str] = Field(..., min_items=3, max_items=3, description="고정 질문 목록 (3개)")
    # 시나리오 생성 출처 (prompt = 사용자 직접 입력, slack = Slack 대화 분석)
    creationType: str = Field(..., description="시나리오 생성 방식 (prompt, slack)")


class AnalysisResultDto(BaseModel):
    """
    Slack 대화 분석 결과 최종 응답 DTO

    FastAPI가 Spring 2로 반환하는 최종 응답 패킷.
    분석된 주제 정보와 생성된 4개의 시나리오를 포함함.

    시나리오 구성:
        1. Overview 시나리오: 전체 상황 개요 (1개)
        2. Detail 시나리오: 특정 역할별 상세 (3개, 예: PM, Tech Lead, QA)
    """
    # LLM이 Slack 대화를 분석하여 도출한 주제/상황 정보
    subject: SubjectInfoDto = Field(..., description="대화 주제 정보")
    # 생성된 시나리오 목록 (반드시 정확히 4개)
    # - scenarios[0]: overview 타입 시나리오 (1개)
    # - scenarios[1-3]: detail 타입 시나리오 (역할별로 3개)
    scenarios: List[ScenarioInfoDto] = Field(..., min_items=4, max_items=4, description="생성된 시나리오 목록 (4개 - overview, project manager detail, tech lead detail, qa engineer detail)")


class ScenarioDetail(BaseModel):
    """
    세션 생성 응답에 포함되는 시나리오 상세 정보

    SessionCreateResponse에 포함되어 클라이언트에 반환되는 시나리오 정보.
    ScenarioInfoDto와 유사하지만, 추가로 DB ID와 사용자 역할을 포함함.
    """
    # DB에 저장된 시나리오의 고유 ID
    scenarioId: int = Field(..., description="시나리오 ID")
    # 대화 주제의 DB ID (subject 테이블의 PK)
    subjectId: int = Field(..., description="주제 ID")
    # 사용자의 IT 직무 역할
    myRole: str = Field(..., description="사용자 역할")
    # AI가 담당할 대상 역할
    aiRole: str = Field(..., description="AI 역할")
    # 시나리오 제목 (사용자가 선택한 시나리오의 이름, 최대 80자)
    title: str = Field(..., max_length=80, description="시나리오 제목")
    # 시나리오 범위 (overview 또는 detail)
    topicType: str = Field(..., description="토픽 타입 (overview, detail)")
    # 롤플레이 중 나올 고정 질문들 (정확히 3개)
    fixedQuestions: List[str] = Field(..., description="고정 질문 3개", min_length=3, max_length=3)


class SessionCreateResponse(BaseModel):
    """
    세션 생성 응답 DTO

    클라이언트가 세션을 생성할 때 서버가 반환하는 응답.
    웹소켓 연결 정보, 시나리오 정보, 세션 만료 시각을 포함함.

    클라이언트의 다음 단계:
        1. 이 응답을 받으면 ws_url로 WebSocket 연결 수립
        2. 연결 후 롤플레이 시작 (scenario 정보를 UI에 표시)
        3. 질문들과 피드백을 실시간으로 수신
        4. expires_at 시간이 되면 세션 자동 종료
    """
    # FastAPI가 생성한 세션 고유 ID (Redis에 저장되는 키)
    # 형식: UUID 문자열
    session_id: str = Field(..., description="생성된 세션 ID")
    # WebSocket 연결을 위한 URL (예: ws://api.example.com/ws/session/{session_id})
    ws_url: str = Field(..., description="WebSocket 연결 URL")
    # 사용자가 선택한 시나리오의 상세 정보 (제목, 역할, 질문 등)
    scenario: ScenarioDetail = Field(..., description="선택된 시나리오 정보")
    # 해당 세션이 유효한 시간의 만료 시각 (ISO 8601 형식)
    # 이 시간이 지나면 세션은 자동으로 Redis에서 삭제됨
    expires_at: datetime = Field(..., description="세션 만료 시각")


# =====================================================
# 사용자 프롬프트 기반 시나리오 생성 스키마
# =====================================================
#
# Slack 분석과는 달리, 사용자가 직접 입력하는 형태의 시나리오 생성.
# 사용자가 원하는 상황, 역할, 대상을 직접 지정하면 시나리오 생성.
#
# 처리 흐름:
#   1. 클라이언트가 PromptBasedScenarioRequestDto 작성
#   2. FastAPI의 /scenarios/generate 엔드포인트로 POST
#   3. LLM이 상황을 분석하고 강화
#   4. 제목, 질문 생성
#   5. PromptBasedScenarioResponseDto로 응답

class PromptBasedScenarioRequestDto(BaseModel):
    """
    사용자 프롬프트 기반 시나리오 생성 요청 DTO

    사용자가 직접 상황, 역할을 입력하여 시나리오를 생성하도록 요청.
    Slack 분석과는 달리, 사용자의 자유로운 입력을 기반으로 함.
    """
    # 데이터베이스의 사용자 ID (PK) - 반드시 양수여야 함
    userId: int = Field(..., description="사용자 ID", gt=0)
    # 사용자가 롤플레이에서 담당할 자신의 역할 (예: "Software Engineer", "Product Manager")
    # 1-100자 범위
    myRole: str = Field(..., description="사용자의 역할", min_length=1, max_length=100)
    # 대화 상대방(AI)의 역할 (예: "HR Manager", "CEO", "Marketing Lead")
    # 1-100자 범위
    aiRole: str = Field(..., description="AI의 역할", min_length=1, max_length=100)
    # 롤플레이의 상황과 주제를 자유롭게 입력
    # 1-500자 범위
    situation: str = Field(..., description="롤플레잉 상황 및 주제", min_length=1, max_length=500)


class PromptBasedScenarioResponseDto(BaseModel):
    """
    사용자 프롬프트 기반 시나리오 생성 응답 DTO

    FastAPI가 생성한 시나리오를 클라이언트에 반환.
    요청에 대해 하나의 시나리오(ScenarioInfoDto)를 포함하여 응답함.
    """
    # LLM이 생성한 시나리오 정보 (제목, AI 역할, 질문, 생성 방식 등)
    scenario: ScenarioInfoDto = Field(..., description="생성된 시나리오 정보")


# =====================================================
# Spring 1 Gateway 전용 내부 API 스키마
# =====================================================
#
# Spring 1 (메인 게이트웨이)과 FastAPI 간의 내부 통신 프로토콜.
# 공개 API와는 달리, 내부 마이크로서비스 간 통신이므로:
# - 보안 검증 단순화 (같은 조직 내 통신)
# - 데이터 형식이 Spring 1과 호환
# - 에러 처리가 서로 약속된 형식
#
# 주요 차이점:
#   - sessionId: Spring 1에서 먼저 생성한 세션 ID (FastAPI가 Redis에 등록)
#   - scenarioId: DB에서 미리 조회된 시나리오 ID
#   - 응답: FastAPI가 WebSocket URL과 함께 반환

class InternalSessionSetupRequest(BaseModel):
    """
    Spring 1에서 FastAPI로 전달하는 내부 세션 설정 요청

    Spring 1이 사용자 세션을 생성하고, FastAPI에게 실시간 세션 정보를 등록하도록 요청.
    Spring 1은 세션 ID를 먼저 생성하고, FastAPI에게 WebSocket URL을 받아 클라이언트에 제공.
    """
    # Spring 1 세션 관리자가 생성한 고유 세션 ID (UUID 형식)
    # 이 ID를 FastAPI의 Redis에도 등록하여 실시간 통신 추적
    sessionId: str = Field(..., description="Spring 1이 생성한 세션 ID (UUID 문자열)")
    # 세션에 해당하는 사용자 ID (양수만 유효)
    userId: int = Field(..., description="사용자 ID", gt=0)
    # 사용자가 선택한 시나리오의 DB ID (양수만 유효)
    # Spring 1에서 미리 조회하여 전달
    scenarioId: int = Field(..., description="시나리오 ID", gt=0)
    # 상호작용 모드 (예: "default", "handsfree")
    # Spring 1에서 전달
    interactionMode: str | None = Field("default", description="상호작용 모드 (default, handsfree)")


class InternalSessionSetupResponse(BaseModel):
    """
    FastAPI에서 Spring 1로 반환하는 내부 세션 설정 응답

    Spring 1이 InternalSessionSetupRequest를 보낸 후 받는 응답.
    FastAPI가 세션을 설정하고 WebSocket 연결 정보를 제공함.

    Spring 1의 다음 처리:
        1. 이 응답을 받으면 wsUrl과 시나리오 정보를 클라이언트에 제공
        2. 클라이언트가 wsUrl로 WebSocket 연결 수립
        3. 실시간 롤플레이 시작 (FastAPI가 질문/피드백 전송)
        4. expiresAt 시간까지 세션 유지
    """
    # 요청에서 받은 세션 ID를 그대로 반환 (확인용)
    sessionId: str = Field(..., description="세션 ID")
    # 클라이언트가 연결할 WebSocket URL (예: ws://fastapi.example.com/ws/{sessionId})
    wsUrl: str = Field(..., description="WebSocket 연결 URL")
    # 시나리오의 상세 정보 (사용자에게 보여줄 내용)
    scenario: ScenarioDetail = Field(..., description="시나리오 정보")
    # 해당 세션의 유효 만료 시각 (ISO 8601 형식)
    expiresAt: datetime = Field(..., description="세션 만료 시각")
