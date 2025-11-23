# FastAPI 롤플레잉 서버 요구사항 정의서

**문서 버전:** 1.0
**작성일:** 2025-11-20
**상태:** 현재 구현 상태 분석 및 요구사항 정의

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [현재 구현 상태](#현재-구현-상태)
3. [전체 기능 요구사항](#전체-기능-요구사항)
4. [세부 API 명세](#세부-api-명세)
5. [데이터베이스 스키마](#데이터베이스-스키마)
6. [기술 스택 및 의존성](#기술-스택-및-의존성)
7. [아키텍처 및 설계 원칙](#아키텍처-및-설계-원칙)

---

## 프로젝트 개요

### 목적
SKALA는 **AI 기반 실시간 영어 회화 연습 플랫폼**입니다. FastAPI 백엔드는 다음을 담당합니다:

- **Slack/GitHub 통합 시나리오 생성**: 대화 기록을 분석하여 영어 연습 시나리오 자동 생성
- **실시간 WebSocket 회화**: 음성 스트리밍, STT, AI 응답, TTS
- **세션 관리**: Redis 기반 세션 검증 및 상태 관리
- **Spring 2와의 협력**: 모든 DB/S3 쓰기는 Spring 2를 통해 수행 (READ-ONLY 원칙)

### 주요 사용자 흐름

```
사용자 → Spring 1 (인증) → Spring 2 (시나리오 생성)
         ↓
    FastAPI WebSocket (실시간 회화)
         ↓
    AI + STT/TTS + Spring 2 (데이터 저장)
```

---

## 현재 구현 상태

### ✅ 완료된 기능

#### 1. 기본 인프라
- [x] FastAPI 애플리케이션 기본 설정 (`app/main.py`)
- [x] 환경 설정 관리 (`app/config.py`)
- [x] 데이터베이스 연결 설정 (`app/db/`, SQLAlchemy ORM)
- [x] 로깅 시스템 (`app/core/logging.py`)
- [x] 예외 처리 (`app/core/exceptions.py`)
- [x] Redis 클라이언트 (`app/integrations/clients/redis_client.py`)

#### 2. 시나리오 생성 (Slack 기반)
- [x] Slack 메시지 분석 및 LLM 처리
- [x] 시나리오 및 고정 질문 생성
- [x] `POST /roleplaying/internal/scenarios/analyze-conversation` 엔드포인트
- [x] 스키마 및 DTO 정의 (`app/roleplaying/schemas.py`)

#### 3. WebSocket 기본 구조
- [x] WebSocket 라우터 기본 설정 (`app/roleplaying/ws_realtime.py`)
- [x] 세션 검증 로직 (Redis)
- [x] 메시지 모델 정의 (`app/roleplaying/ws_models.py`)
- [x] 세션 상태 관리자 (`app/roleplaying/session_manager.py`)

#### 4. 건강 확인 (Health Check)
- [x] `GET /health/health/ping`
- [x] `GET /roleplaying/health/ping`
- [x] `GET /` (root endpoint)

### ⚠️ 진행 중인 기능

#### 1. 세션 생성 API
- [x] 엔드포인트 정의: `POST /roleplaying/sessions`
- [x] 요청/응답 스키마 정의
- [ ] 데이터베이스 모델 완성 (subject, scenario 테이블 확인 필요)
- [ ] 세션 만료 시간 설정 및 Redis 저장 로직
- [ ] 반환되는 scenario 정보 필드 확인

#### 2. WebSocket 메시지 처리
- [ ] INIT 메시지 처리
- [ ] UTTERANCE_END 메시지 처리
- [ ] USER_TEXT 메시지 처리 (테스트용)
- [ ] END_SESSION 메시지 처리
- [ ] 메시지 유효성 검증

#### 3. STT (Speech-to-Text) 처리
- [ ] 오디오 청크 수신 및 누적
- [ ] Whisper 또는 Google Cloud Speech 통합
- [ ] 부분 결과 (STT_PARTIAL) 전송
- [ ] 최종 결과 (STT_FINAL) 전송

#### 4. AI 응답 생성
- [ ] OpenAI/Claude/Ollama 통합
- [ ] 고정 질문 사용 (3개 중 선택)
- [ ] 동적 응답 생성
- [ ] 컨텍스트 관리 (이전 대화 참고)

#### 5. Spring 2 통합
- [ ] `POST /internal/sessions` - 세션 생성
- [ ] `POST /internal/utterances` - 발화 저장
- [ ] `GET /internal/sessions/{session_id}` - 세션 조회
- [ ] 타임아웃 처리 및 재시도 로직

### ❌ 미구현 기능

#### 1. 추가 API 엔드포인트 (OpenAPI 문서 기준)
- [ ] `GET /roleplaying/userInfo` - 사용자 정보 조회
- [ ] `GET /roleplaying/userStatics` - 사용자 이용 데이터 조회
- [ ] `GET /roleplaying/roleplayList` - 롤플레잉 리스트 조회
- [ ] `POST /roleplaying/prompt_create` - 프롬프트 기반 롤플레잉 생성
- [ ] `POST /roleplaying/{roleplayingId}/session/start` - 롤플레잉 세션 시작
- [ ] `POST /roleplaying/{sessionId}/nextTurn` - 다음 턴 생성
- [ ] `GET /roleplaying/{sessionId}/messages` - 세션 메시지 조회

#### 2. Textbook (교재 기반) 모듈
- [ ] 교재 레슨 시작 API
- [ ] 질문 흐름 처리
- [ ] 답변 제출 및 평가
- [ ] 레슨 종료 및 피드백

#### 3. Feedback (피드백) 모듈
- [ ] 세션 완료 후 피드백 수집
- [ ] 점수 계산
- [ ] 피드백 요약 생성

#### 4. MyPage (사용자 페이지) 기능
- [ ] 프로필 조회/수정
- [ ] 북마크 관리
- [ ] 순위 시스템
- [ ] 설정 관리
- [ ] 데이터 복구

#### 5. Integration (통합) 모듈
- [ ] GitHub 연동
- [ ] Slack 동기화
- [ ] 메시지 매핑 및 정규화

---

## 전체 기능 요구사항

### 1. 시나리오 생성 (분석 및 생성)

**기능:**
- Spring 2가 Slack 대화 기록을 전송
- FastAPI가 LLM을 사용하여 분석
- 1개의 개요 시나리오 + 3개의 상세 시나리오 생성
- 각 시나리오마다 3개의 고정 질문 생성

**입력:**
```json
{
  "userId": 1,
  "myRole": "Software Engineer",
  "conversationDate": "2025-11-20",
  "messages": [
    {
      "timestamp": "2025-11-20T10:00:00Z",
      "senderName": "Alice",
      "text": "어제 미팅에서 뭐 얘기했어?",
      "myMessage": false
    }
  ],
  "aiRoles": ["Tech Lead", "Product Manager"]
}
```

**출력:**
```json
{
  "subject": {
    "myRole": "Software Engineer",
    "situation": "Daily standup discussion",
    "conversationDate": "2025-11-20",
    "messageCount": 5
  },
  "scenarios": [
    {
      "aiRole": "Tech Lead",
      "topicType": "overview",
      "title": "Daily Standup Discussion",
      "fixedQuestions": [
        "Can you summarize yesterday's meeting?",
        "What are the technical challenges?",
        "What's next?"
      ]
    },
    // ... 3개 더
  ]
}
```

### 2. 세션 생성 및 관리

**기능:**
- 시나리오 ID를 받아 DB에서 조회
- Redis에 세션 정보 저장 (만료 시간 설정)
- WebSocket URL 반환

**요청:**
```json
{
  "userId": 1,
  "scenarioId": 31,
  "sessionId": "550e8400-e29b-41d4-a716-446655440000"  // 선택사항
}
```

**응답:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "ws_url": "wss://api.skala.local/ws/roleplaying/550e8400-e29b-41d4-a716-446655440000",
  "scenario": {
    "scenarioId": 31,
    "subjectId": 1,
    "myRole": "Software Engineer",
    "aiRole": "Tech Lead",
    "title": "Daily Standup Discussion",
    "topicType": "overview",
    "fixedQuestions": ["Q1", "Q2", "Q3"]
  },
  "expires_at": "2025-11-20T11:00:00Z"
}
```

### 3. WebSocket 실시간 회화

#### 메시지 흐름

```
클라이언트 → 서버 → 서버 → 클라이언트
──────────────────────────────
INIT          → 초기화    → ACK
              → 첫 AI 질문 → AI_TEXT

오디오 청크   → STT      → STT_PARTIAL
              →          → STT_FINAL

UTTERANCE_END → 저장      → UTTERANCE_SAVED
              → AI 응답   → AI_TYPING
              →          → AI_TEXT

END_SESSION   → 종료      → SESSION_ENDED
```

#### 메시지 명세

##### 인바운드 메시지 (클라이언트 → 서버)

1. **INIT** - 세션 초기화
```json
{
  "type": "INIT",
  "userId": 1,
  "subjectId": 1,
  "myRole": "Software Engineer",
  "aiRole": "Tech Lead",
  "fixedQuestions": ["Q1", "Q2", "Q3"]
}
```

2. **오디오 청크** - 바이너리 프레임
- MIME: `audio/webm` 또는 `audio/wav`
- 부분 데이터

3. **UTTERANCE_END** - 발화 끝
```json
{
  "type": "UTTERANCE_END"
}
```

4. **USER_TEXT** - 텍스트 입력 (테스트용)
```json
{
  "type": "USER_TEXT",
  "text": "I have finished my current project."
}
```

5. **END_SESSION** - 세션 종료
```json
{
  "type": "END_SESSION"
}
```

##### 아웃바운드 메시지 (서버 → 클라이언트)

1. **ACK** - 메시지 수신 확인
```json
{
  "type": "ACK",
  "message": "Initialized"
}
```

2. **AI_TEXT** - AI 응답
```json
{
  "type": "AI_TEXT",
  "text": "Can you summarize your recent project?",
  "is_fixed_question": true
}
```

3. **STT_PARTIAL** - STT 부분 결과
```json
{
  "type": "STT_PARTIAL",
  "text": "I have finished..."
}
```

4. **STT_FINAL** - STT 최종 결과
```json
{
  "type": "STT_FINAL",
  "text": "I have finished my current project."
}
```

5. **UTTERANCE_SAVED** - 발화 저장 완료
```json
{
  "type": "UTTERANCE_SAVED",
  "index": 2
}
```

6. **AI_TYPING** - AI가 응답 작성 중
```json
{
  "type": "AI_TYPING"
}
```

7. **SESSION_ENDED** - 세션 종료
```json
{
  "type": "SESSION_ENDED",
  "reason": "user_end|timeout|disconnected|error|turn_limit"
}
```

8. **ERROR** - 에러 발생
```json
{
  "type": "ERROR",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

### 4. 턴 관리 및 제한

- **최대 턴 수**: 10 (AI ↔ 사용자 쌍)
- **세션 타임아웃**: 30분 (설정 가능)
- **고정 질문**: 3개 (처음, 중간, 끝)
- **동적 응답**: LLM 기반 (고정 질문 사용 후 자유로운 질문)

### 5. Spring 2 통합 API

#### 5.1 세션 생성 (FastAPI → Spring 2)

**엔드포인트:** `POST /api/v1/roleplaying/sessions`

**요청:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "scenario_id": 31
}
```

**응답:**
```json
{
  "success": true
}
```

#### 5.2 발화 저장 (FastAPI → Spring 2)

**엔드포인트:** `POST /api/v1/roleplaying/sessions/{session_id}/utterances`

**요청:**
```json
{
  "utterance_index": 2,
  "speaker": "user|ai",
  "text": "User's spoken text or AI response",
  "s3_url": "s3://bucket/path/to/audio.wav",  // 사용자 발화만
  "started_at": "2025-11-20T10:05:00Z",       // 사용자 발화만
  "ended_at": "2025-11-20T10:06:00Z"          // 사용자 발화만
}
```

**응답:**
```json
{
  "success": true,
  "utterance_id": 12345
}
```

#### 5.3 세션 종료 (FastAPI → Spring 2)

**엔드포인트:** `PUT /api/v1/roleplaying/sessions/{session_id}/finish`

**요청:**
```json
{
  "end_reason": "user_end|timeout|disconnected|error|turn_limit",
  "ended_at": "2025-11-20T10:30:00Z"
}
```

**응답:**
```json
{
  "success": true
}
```

---

## 세부 API 명세

### 1. Health Check APIs

#### GET /health/health/ping
**설명:** 서비스 건강 확인
**응답:**
```json
{
  "status": "ok"
}
```

#### GET /roleplaying/health/ping
**설명:** 롤플레잉 모듈 건강 확인
**응답:**
```json
{
  "status": "ok"
}
```

#### GET /
**설명:** 루트 엔드포인트
**응답:**
```json
{
  "message": "hello"
}
```

### 2. Scenario APIs

#### POST /roleplaying/internal/scenarios/analyze-conversation
**설명:** Slack 대화 분석 및 시나리오 생성
**요청:** AnalysisRequestDto
**응답:** AnalysisResultDto
**상태 코드:**
- 200: 성공
- 400: 유효성 검증 실패 (messages 비어있음)
- 500: LLM 오류

### 3. Session APIs

#### POST /roleplaying/sessions
**설명:** 롤플레잉 세션 생성
**인증:** 불필요 (Spring 1이 사전 검증)
**요청:** SessionCreateRequest
**응답:** SessionCreateResponse
**상태 코드:**
- 200: 성공
- 404: 시나리오를 찾을 수 없음
- 500: Redis/DB 오류

### 4. WebSocket API

#### WS /ws/roleplaying/{session_id}
**설명:** 실시간 롤플레잉 WebSocket
**프로토콜:**
- 업그레이드 완료 후 JSON + 바이너리 메시지
- 모든 제어 메시지는 JSON
- 오디오 데이터는 바이너리 프레임

**타임아웃:**
- 세션 검증 실패 → 연결 거부
- INIT 메시지 없음 (30초) → 타임아웃
- 비활성 (5분) → 연결 종료

---

## 데이터베이스 스키마

### 1. scenarios 테이블 (기존)

```sql
CREATE TABLE scenarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    subject_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'generated',
    fixed_questions JSON NOT NULL,  -- ["Q1", "Q2", "Q3"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    INDEX idx_user_id (user_id),
    INDEX idx_subject_id (subject_id),
    INDEX idx_status (status)
);
```

### 2. subjects 테이블 (기존)

```sql
CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    my_role VARCHAR(255),
    ai_role VARCHAR(255),
    situation TEXT,
    topic_type ENUM('overview', 'detail'),
    source_type VARCHAR(50),  -- 'slack', 'github', 'prompt'
    conversation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id)
);
```

### 3. sessions 테이블 (Spring 2용)

```sql
CREATE TABLE sessions (
    session_id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id BIGINT NOT NULL,
    scenario_id INT NOT NULL,
    status ENUM('ACTIVE', 'FINISHED', 'ERROR') DEFAULT 'ACTIVE',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    end_reason VARCHAR(50) NULL,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id),
    INDEX idx_user_id (user_id),
    INDEX idx_scenario_id (scenario_id),
    INDEX idx_status (status)
);
```

### 4. utterances 테이블 (Spring 2용)

```sql
CREATE TABLE utterances (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    utterance_index INT NOT NULL,
    speaker ENUM('user', 'ai') NOT NULL,
    text TEXT NOT NULL,
    s3_url VARCHAR(512),  -- 사용자 발화만
    started_at TIMESTAMP,  -- 사용자 발화만
    ended_at TIMESTAMP,    -- 사용자 발화만
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE KEY uk_session_utterance (session_id, utterance_index),
    INDEX idx_session_id (session_id),
    INDEX idx_session_speaker (session_id, speaker)
);
```

### 5. Redis 세션 저장소

**Key Format:** `session:{session_id}`
**TTL:** 30분

**값:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "scenario_id": 31,
  "status": "ACTIVE",
  "created_at": "2025-11-20T10:00:00Z",
  "last_activity": "2025-11-20T10:05:00Z"
}
```

---

## 기술 스택 및 의존성

### 핵심 프레임워크
- **FastAPI** >= 0.104.0
- **Uvicorn** >= 0.24.0 (ASGI 서버)
- **Pydantic** >= 2.0.0 (데이터 검증)

### 데이터베이스
- **SQLAlchemy** >= 2.0.0 (ORM)
- **Alembic** >= 1.12.0 (마이그레이션)
- **asyncpg** >= 0.29.0 (PostgreSQL 비동기 드라이버)
- **psycopg2-binary** >= 2.9.9 (PostgreSQL 동기 드라이버)

### 캐시 및 세션
- **Redis** >= 5.0.0 (비동기)

### 외부 통신
- **httpx** >= 0.25.0 (HTTP 클라이언트, Spring 2 통신)

### STT (Speech-to-Text)
- **openai-whisper** >= 20231117 (로컬 STT)
- *선택사항:* Google Cloud Speech, Azure Speech

### LLM (Large Language Model)
- **OpenAI** >= 1.0.0
- **Anthropic** >= 0.7.0
- **ollama** >= 0.1.0

### 파일 저장소
- **boto3** >= 1.28.0 (S3/MinIO)

### 개발 도구
- **pytest** >= 7.4.0
- **pytest-asyncio** >= 0.21.0
- **black**, **isort**, **mypy**, **flake8**

---

## 아키텍처 및 설계 원칙

### 1. 3-Tier 서버 구조

```
┌─────────────┐
│   Client    │ (React/Flutter)
└──────┬──────┘
       │ WebSocket (JWT)
       ▼
┌─────────────┐       (UUID 생성 & Redis 저장)
│  Spring 1   │ ──────────────┐
└──────┬──────┘               │
       │ HTTP                 │
       ▼                       │
┌─────────────────────────────▼──────┐
│       Spring 2 (API Gateway)       │
│   - 시나리오 CRUD                  │
│   - 발화 저장 & S3 업로드           │
│   - 비즈니스 로직                  │
└──────┬──────────────────────────────┘
       │ HTTP (RPC)
       ▼
┌─────────────────────────────────────┐
│        FastAPI (READ-ONLY)          │
│   - WebSocket 관리                  │
│   - STT/AI 처리                      │
│   - Spring 2 호출 (쓰기 위임)       │
└──────┬────────────────┬─────────────┘
       │ Redis          │ PostgreSQL
       ▼                ▼
    [Cache]        [Database]
```

### 2. FastAPI READ-ONLY 원칙

**규칙:**
- FastAPI는 DB와 S3에 **쓸 수 없음**
- 모든 쓰기는 Spring 2 API를 통해 수행
- FastAPI는 읽기 및 계산만 담당

**이점:**
- 트랜잭션 관리 중앙화 (Spring 2)
- 일관성 보장
- 감시 로그 단순화

### 3. 메시지 기반 설계

**WebSocket 메시지 특성:**
- JSON: 제어 메시지 (타입, 설정)
- 바이너리: 오디오 데이터

**상태 머신:**

```
┌─────────────┐
│    INIT     │
└──────┬──────┘
       │ INIT 메시지
       ▼
┌──────────────────┐
│ WAITING_FOR_USER │
└──────┬───────────┘
       │ 오디오/텍스트
       ▼
┌──────────────┐
│ PROCESSING   │ (STT → AI → TTS)
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ WAITING_FOR_USER │ (반복)
└──────┬───────────┘
       │ END_SESSION
       ▼
┌──────────┐
│ FINISHED │
└──────────┘
```

### 4. 에러 처리

**레벨별 에러 처리:**

1. **검증 에러** (400)
   - 요청 형식 오류
   - 필수 필드 누락

2. **인증 에러** (401/403)
   - 토큰 검증 실패
   - 권한 부족

3. **리소스 에러** (404)
   - 시나리오/세션 찾을 수 없음

4. **서버 에러** (500)
   - LLM 호출 실패
   - DB 연결 실패
   - Spring 2 통신 실패

**WebSocket 에러:**
- JSON 메시지로 ERROR 타입 전송
- 심각한 오류는 연결 종료
- 상태 코드: 1000 (정상), 1008 (정책), 1011 (서버 에러)

### 5. 동시성 처리

**비동기 처리:**
- 모든 I/O 작업은 `async/await` 사용
- WebSocket 연결 관리는 TaskGroup 사용 (동시 다중 연결)
- 세션 상태는 스레드 안전 구조 사용

**병목 관리:**
- STT: 장시간 작업 → 백그라운드 처리 고려
- LLM: 외부 API 호출 → 타임아웃 설정 (30초)
- Spring 2: 재시도 로직 (exponential backoff)

---

## 구현 로드맵

### Phase 1: Core WebSocket (우선순위 높음)
- [ ] 세션 생성 API 완성
- [ ] WebSocket 메시지 처리 완성
- [ ] STT 통합
- [ ] AI 응답 생성
- [ ] Spring 2 통합 (발화 저장)

### Phase 2: 추가 API (우선순위 중간)
- [ ] userInfo, userStatics API
- [ ] roleplayList API
- [ ] prompt_create API

### Phase 3: 교재 및 피드백 (우선순위 낮음)
- [ ] Textbook 모듈
- [ ] Feedback 모듈
- [ ] MyPage 모듈

---

## 참고 자료

- **OpenAPI 명세**: `/docs/roleplaying_openapi.yaml`
- **WebSocket 아키텍처**: `/docs/websocket_realtime_architecture.md`
- **Spring 2 통합 가이드**: `/docs/spring2_roleplaying_implementation_prompt.md`
- **API 테스트 가이드**: `/docs/api_test_guide.md`
- **개발 지침**: `/docs/development_instructions.md`

---

**문서 최종 업데이트:** 2025-11-20
**다음 검토일:** 2025-12-04