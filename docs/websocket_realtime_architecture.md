# WebSocket 실시간 롤플레잉 아키텍처

## 📋 개요

SKALA 프로젝트의 FastAPI WebSocket 기반 실시간 롤플레잉 서버 아키텍처 문서입니다.

**목적:**
- 실시간 음성 기반 영어 회화 연습
- 오디오 스트리밍 → STT → AI 응답 → TTS 흐름
- Spring 2와의 통합 (음성 데이터 저장, 세션 관리)

**핵심 원칙:**
- FastAPI는 READ-ONLY (DB/S3 쓰기 금지)
- 모든 쓰기 작업은 Spring 2를 통해 수행
- 세션 검증은 연결 시 1회만 (성능 최적화)

---

## 🏗️ 시스템 아키텍처

### 3-Tier 서버 구조

```
┌──────────────┐
│   Client     │ (React/Flutter)
│              │
│ - 음성 녹음   │
│ - TTS/Avatar │
│ - WebSocket  │
└──────────────┘
        │
        │ HTTP (JWT)
        ▼
┌──────────────┐
│  Spring 1    │ (API Gateway + Auth)
│              │
│ - JWT 발급   │
│ - 세션 생성   │
│ - Redis 저장 │
└──────────────┘
        │
        │ WebSocket Info
        ▼
┌──────────────┐         ┌──────────────┐
│   FastAPI    │────────▶│   Spring 2   │
│              │  HTTP   │              │
│ - WebSocket  │         │ - DB Write   │
│ - STT        │         │ - S3 Upload  │
│ - AI Tutor   │         │ - 비즈니스    │
│ - READ-ONLY  │         │   로직       │
└──────────────┘         └──────────────┘
        │                        │
        │                        │
        ▼                        ▼
┌──────────────┐         ┌──────────────┐
│    Redis     │         │ PostgreSQL   │
│ (Session)    │         │ + Qdrant     │
└──────────────┘         │ + S3         │
                         └──────────────┘
```

---

## 📂 파일 구조 (기존 구조에 맵핑)

### 현재 디렉토리 구조
```
app/
├── main.py                     # FastAPI 앱 (WebSocket 라우터 등록)
├── config.py                   # 설정 (Redis, Spring 2 URL)
├── core/                       # 공통 기능
│   ├── logging.py
│   ├── deps.py
│   └── security.py
├── integrations/               # 외부 시스템 통합
│   ├── clients/
│   │   ├── spring2_client.py   ⭐ NEW
│   │   └── redis_client.py     ⭐ NEW
│   ├── mappers/
│   └── services/
└── roleplaying/                # 롤플레잉 모듈
    ├── router.py              # HTTP API (기존)
    ├── schemas.py             # HTTP DTO (기존)
    ├── models.py              # DB 모델 (기존)
    ├── ws_audio.py            # WebSocket (기존 - Slack 용)
    ├── ws_realtime.py         ⭐ NEW - 실시간 WebSocket
    ├── session_manager.py     ⭐ NEW - 세션 상태 관리
    ├── ws_models.py           ⭐ NEW - WebSocket 메시지 모델
    └── services/
        ├── llm_service.py     # LLM (기존 - Slack 시나리오)
        ├── ai_tutor_service.py ⭐ NEW - 실시간 AI 응답
        └── stt_service.py      ⭐ NEW - STT 엔진
```

### 추가할 파일

| 파일 | 역할 | 의존성 |
|------|------|--------|
| `ws_realtime.py` | WebSocket 엔드포인트 | SessionManager, Redis, Spring2, STT, AI |
| `session_manager.py` | 인메모리 세션 관리 | - |
| `ws_models.py` | WebSocket 메시지 모델 | Pydantic |
| `services/ai_tutor_service.py` | AI 응답 생성 | LLM API |
| `services/stt_service.py` | STT 처리 | Whisper 등 |
| `integrations/clients/redis_client.py` | Redis 세션 검증 | redis-py |
| `integrations/clients/spring2_client.py` | Spring 2 HTTP 클라이언트 | httpx |

---

## 🔄 전체 실행 흐름

### Phase 1: 세션 시작 (Spring 1 → Redis)

```
Client → Spring 1: POST /roleplaying/sessions
                   (JWT 포함)

Spring 1:
  1. JWT 검증
  2. session_id 생성 (UUID)
  3. Redis 저장:
     SET session:{session_id}
     {
       "userId": 1,
       "role": "user",
       "scenarioType": "ROLEPLAYING",
       "startedAt": "2025-11-17T10:00:00Z",
       "expiresAt": "2025-11-17T12:00:00Z"
     }
     TTL: 2 hours

Spring 1 → Client:
  {
    "session_id": "abc-123-def",
    "ws_url": "wss://fastapi.skala.com/ws/roleplaying/abc-123-def"
  }
```

**파일:** Spring 1 (별도 서버)

---

### Phase 2: WebSocket 연결 (Client ↔ FastAPI)

```
Client → FastAPI: WebSocket /ws/roleplaying/{session_id}

FastAPI:
  1. Redis 검증 (1회만):
     GET session:{session_id}

  2. 검증 성공 시:
     - WebSocket 연결 수락
     - SessionManager에 세션 생성 (메모리)

  3. 검증 실패 시:
     - WebSocket 연결 거부 (1008: Invalid Session)
```

**파일:**
- `ws_realtime.py` - WebSocket 엔드포인트
- `integrations/clients/redis_client.py` - Redis 검증

**코드 예시:**
```python
@app.websocket("/ws/roleplaying/{session_id}")
async def roleplaying_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # ✅ Redis 검증 (연결 시 1회만)
    session_data = await redis_validator.validate_session(session_id)
    if not session_data:
        await websocket.close(code=1008, reason="Invalid session")
        return

    # SessionManager에 세션 생성
    session_manager.create_session(
        session_id=session_id,
        user_id=session_data["userId"],
        expires_at=datetime.fromisoformat(session_data["expiresAt"])
    )
```

---

### Phase 3: 세션 초기화 (INIT 메시지)

```
Client → FastAPI:
  {
    "type": "INIT",
    "userId": 1,
    "subjectId": 123,
    "myRole": "Software Engineer",
    "aiRole": "Tech Lead",
    "fixedQuestions": [
      "Can you introduce yourself?",
      "What are your main responsibilities?",
      "How do you handle conflicts?"
    ]
  }

FastAPI:
  1. SessionManager에 컨텍스트 저장
  2. ACK 전송
  3. 첫 AI 질문 생성 및 전송

FastAPI → Client:
  { "type": "ACK", "message": "received" }

  { "type": "AI_TEXT", "text": "Can you introduce yourself?" }
```

**파일:**
- `ws_models.py` - InitMessage 모델
- `session_manager.py` - 세션 생성
- `services/ai_tutor_service.py` - 첫 질문 생성

---

### Phase 4: 사용자 발화 (오디오 스트리밍 → STT)

```
Client → FastAPI: (오디오 청크 스트리밍)
  - Binary: AUDIO_CHUNK (1024 bytes)
  - Binary: AUDIO_CHUNK (1024 bytes)
  - Binary: AUDIO_CHUNK (1024 bytes)
  - ...

FastAPI:
  1. 오디오 청크 버퍼에 추가
  2. STT 스트리밍 처리
  3. 부분 결과 즉시 반환

FastAPI → Client:
  { "type": "STT_PARTIAL", "text": "I am a" }
  { "type": "STT_PARTIAL", "text": "I am a software" }

Client → FastAPI:
  { "type": "UTTERANCE_END" }

FastAPI:
  1. 전체 오디오 최종 STT
  2. 최종 텍스트 전송
  3. Spring 2에 비동기 전송 (발화 저장)

FastAPI → Client:
  { "type": "STT_FINAL", "text": "I am a software engineer" }

FastAPI → Spring 2: (비동기)
  POST /internal/sessions/{session_id}/utterances
  Content-Type: multipart/form-data

  - audio: (binary .wav file)
  - stt_text: "I am a software engineer"
  - utterance_index: 1
  - started_at: "2025-11-17T10:01:00Z"
  - ended_at: "2025-11-17T10:01:05Z"

Spring 2:
  1. S3 업로드: s3://skala/sessions/{session_id}/utterance_1.wav
  2. PostgreSQL 저장:
     INSERT INTO utterances (session_id, s3_url, stt_text, ...)

FastAPI → Client:
  { "type": "UTTERANCE_SAVED", "index": 1 }
```

**파일:**
- `services/stt_service.py` - STT 처리
- `integrations/clients/spring2_client.py` - Spring 2 호출

**핵심 포인트:**
- ✅ FastAPI는 S3/DB에 직접 쓰기 금지
- ✅ Spring 2가 S3 업로드 + PostgreSQL 저장
- ✅ 비동기 전송으로 WebSocket 응답성 유지

---

### Phase 5: AI 응답 생성

```
FastAPI:
  1. AI_TYPING 전송
  2. AI 서비스 호출:
     - 세션 컨텍스트 (시나리오, 대화 히스토리)
     - 사용자 발화
     → LLM API (GPT-4, Claude 등)
  3. AI 응답 생성
  4. 세션 히스토리에 추가
  5. 클라이언트 전송

FastAPI → Client:
  { "type": "AI_TYPING" }

  (2-3초 후)

  {
    "type": "AI_TEXT",
    "text": "That's great! What technologies do you work with?"
  }
```

**파일:**
- `services/ai_tutor_service.py` - AI 응답 생성

**AI 응답 생성 로직:**
```python
async def generate_reply(session_state: SessionState, user_text: str) -> str:
    # 1. 시나리오 컨텍스트
    scenario = f"Role: {session_state.ai_role}, Topic: {session_state.my_role}"

    # 2. 대화 히스토리
    history = [
        f"{turn.speaker}: {turn.text}"
        for turn in session_state.history[-5:]  # 최근 5턴
    ]

    # 3. 고정 질문 진행도
    fixed_q_index = len([t for t in session_state.history if t.speaker == "ai"])
    if fixed_q_index < len(session_state.fixed_questions):
        return session_state.fixed_questions[fixed_q_index]

    # 4. LLM 호출
    prompt = f"""
    Scenario: {scenario}
    History: {history}
    User: {user_text}

    Generate next question as a {session_state.ai_role}.
    """

    return await llm_api.generate(prompt)
```

---

### Phase 6: 세션 종료

```
Client → FastAPI:
  { "type": "END_SESSION" }

FastAPI:
  1. SessionManager.end_session()
  2. Spring 2에 세션 완료 알림

FastAPI → Spring 2:
  POST /internal/sessions/{session_id}/complete
  {
    "status": "FINISHED",
    "reason": "user_end"
  }

Spring 2:
  UPDATE sessions
  SET status = 'FINISHED', ended_at = NOW()
  WHERE id = {session_id}

FastAPI → Client:
  { "type": "SESSION_ENDED", "reason": "user_end" }

  [WebSocket 연결 종료]

FastAPI:
  session_manager.cleanup(session_id)  # 메모리 정리
```

**종료 시나리오:**
- `user_end`: 사용자가 정상 종료
- `timeout`: 세션 만료 시간 초과
- `disconnected`: 네트워크 끊김
- `error`: 오류 발생

---

## 🔐 세션 검증 전략

### 문제: 매 메시지마다 Redis 검증?

**❌ 비효율적:**
- 오디오 스트리밍은 초당 수십~수백 개의 청크
- 각 청크마다 Redis 조회 시:
  - 레이턴시: 1-5ms × 수백 = 수백 ms
  - Redis 부하 급증
  - 실시간 응답성 저하

**✅ 권장 전략: 연결 시 1회 검증 + TTL 로컬 체크**

| 검증 시점 | Redis 조회 | SessionManager 조회 | 성능 |
|----------|-----------|-------------------|------|
| WebSocket 연결 | ✅ 1회 | - | 높음 |
| INIT 메시지 | ❌ | ✅ | 높음 |
| 오디오 청크 | ❌ | ✅ | 높음 |
| 사용자 메시지 | ❌ | ✅ (+ TTL 체크) | 높음 |
| 세션 종료 | ✅ (선택) | ✅ | 중간 |

### 구현 방법

```python
@dataclass
class SessionState:
    session_id: str
    user_id: int
    created_at: datetime
    expires_at: datetime  # ⭐ Redis에서 가져온 만료 시간

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

# 메시지 처리 전
session_state = session_manager.get_session(session_id)
if not session_state or session_state.is_expired():
    await websocket.close(code=1008, reason="Session expired")
    return
```

### 추가 보안 옵션 (선택 사항)

**Option 1: 주기적 Heartbeat (5분마다)**
```python
async def periodic_session_check(session_id: str):
    while True:
        await asyncio.sleep(300)  # 5분

        session_data = await redis_validator.validate_session(session_id)
        if not session_data:
            await websocket.close(code=1008, reason="Session expired")
            break
```

**Option 2: 중요 작업 시에만 재검증**
```python
# 세션 종료 등 중요한 작업 시에만
async def handle_session_end(session_id):
    # ✅ 한 번 더 검증
    session_data = await redis_validator.validate_session(session_id)
    if not session_data:
        logger.warning(f"Session {session_id} already invalid")
```

---

## 📦 WebSocket 메시지 프로토콜

### 인바운드 메시지 (Client → FastAPI)

#### 1. INIT - 세션 초기화
```json
{
  "type": "INIT",
  "userId": 1,
  "subjectId": 123,
  "myRole": "Software Engineer",
  "aiRole": "Tech Lead",
  "fixedQuestions": ["Q1", "Q2", "Q3"]
}
```

#### 2. AUDIO_CHUNK - 오디오 청크
```
Binary data (1024 bytes)
```

#### 3. UTTERANCE_END - 발화 종료
```json
{
  "type": "UTTERANCE_END"
}
```

#### 4. USER_TEXT - 텍스트 메시지 (오디오 없이)
```json
{
  "type": "USER_TEXT",
  "text": "I am a software engineer"
}
```

#### 5. END_SESSION - 세션 종료
```json
{
  "type": "END_SESSION"
}
```

### 아웃바운드 메시지 (FastAPI → Client)

#### 1. ACK - 수신 확인
```json
{
  "type": "ACK",
  "message": "received"
}
```

#### 2. AI_TEXT - AI 응답
```json
{
  "type": "AI_TEXT",
  "text": "Can you introduce yourself?"
}
```

#### 3. STT_PARTIAL - STT 부분 결과
```json
{
  "type": "STT_PARTIAL",
  "text": "I am a softw"
}
```

#### 4. STT_FINAL - STT 최종 결과
```json
{
  "type": "STT_FINAL",
  "text": "I am a software engineer"
}
```

#### 5. UTTERANCE_SAVED - 발화 저장 완료
```json
{
  "type": "UTTERANCE_SAVED",
  "index": 1
}
```

#### 6. AI_TYPING - AI 응답 생성 중
```json
{
  "type": "AI_TYPING"
}
```

#### 7. SESSION_ENDED - 세션 종료
```json
{
  "type": "SESSION_ENDED",
  "reason": "user_end"
}
```

#### 8. ERROR - 오류
```json
{
  "type": "ERROR",
  "message": "STT service unavailable"
}
```

---

## 🗄️ 데이터 모델

### SessionState (SessionManager)

```python
@dataclass
class SessionState:
    session_id: str
    user_id: int
    subject_id: int
    my_role: str              # 사용자 직무 (예: "Software Engineer")
    ai_role: str              # AI 역할 (예: "Tech Lead")
    fixed_questions: List[str] # 고정 질문 목록
    history: List[Turn]       # 대화 히스토리
    status: SessionStatus     # ACTIVE / FINISHED / ERROR
    created_at: datetime
    expires_at: datetime      # Redis에서 가져온 만료 시간
    current_utterance_audio: bytes  # 현재 발화 오디오 버퍼
    utterance_index: int      # 발화 인덱스 (0부터 시작)
```

### Turn (대화 턴)

```python
@dataclass
class Turn:
    speaker: str              # "user" | "ai"
    text: str                 # 발화 내용
    timestamp: datetime
    audio_s3_url: Optional[str]  # S3 URL (사용자 발화만)
```

---

## 🚀 Spring 2 API 사양

### 1. 발화 저장

**Endpoint:** `POST /internal/sessions/{session_id}/utterances`

**Request:**
```
Content-Type: multipart/form-data

Fields:
  - audio: (binary file, .wav)
  - stt_text: "I am a software engineer"
  - utterance_index: 1
  - started_at: "2025-11-17T10:01:00Z"
  - ended_at: "2025-11-17T10:01:05Z"
```

**Response:**
```json
{
  "success": true,
  "s3_url": "s3://skala/sessions/abc-123/utterance_1.wav",
  "utterance_id": 456
}
```

**Spring 2 처리:**
1. S3 업로드: `audio` → `s3://skala/sessions/{session_id}/utterance_{index}.wav`
2. PostgreSQL 저장:
   ```sql
   INSERT INTO utterances (
     session_id, utterance_index, s3_url, stt_text,
     started_at, ended_at
   ) VALUES (?, ?, ?, ?, ?, ?)
   ```

---

### 2. 세션 완료

**Endpoint:** `POST /internal/sessions/{session_id}/complete`

**Request:**
```json
{
  "status": "FINISHED",
  "reason": "user_end"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "abc-123",
  "ended_at": "2025-11-17T10:30:00Z"
}
```

**Spring 2 처리:**
```sql
UPDATE sessions
SET status = 'FINISHED', ended_at = NOW(), end_reason = 'user_end'
WHERE id = ?
```

---

## 🛠️ 에러 핸들링

### 1. WebSocket 연결 실패

| 에러 | 원인 | 처리 |
|------|------|------|
| 1008: Invalid Session | Redis에 session_id 없음 | 연결 거부, 클라이언트에 재로그인 안내 |
| 1008: Session Expired | 세션 만료 시간 초과 | 연결 거부 |
| 1011: Internal Error | FastAPI 내부 오류 | 에러 로그, 연결 종료 |

### 2. 메시지 처리 오류

| 에러 | 처리 | 응답 |
|------|------|------|
| STT 실패 | 로그 + 재시도 (1회) | ERROR 메시지 전송 |
| AI 응답 생성 실패 | 기본 응답 반환 | AI_TEXT (fallback) |
| Spring 2 호출 실패 | 로그만 (WebSocket 유지) | UTTERANCE_SAVED (skip) |
| SessionManager 없음 | 세션 종료 | SESSION_ENDED |

### 3. 연결 끊김

```python
try:
    # WebSocket 메시지 루프
    ...
except WebSocketDisconnect:
    logger.info(f"Client disconnected: {session_id}")

    # 세션 종료 처리
    await handle_session_end(session_id, "disconnected")

    # Spring 2 알림
    await spring_client.complete_session(
        session_id, "FINISHED", "disconnected"
    )

    # 메모리 정리
    session_manager.cleanup(session_id)
```

---

## 📊 성능 고려사항

### 1. 오디오 스트리밍

- **청크 크기:** 1024 bytes (약 64ms @ 16kHz)
- **전송 빈도:** 초당 15-20 청크
- **버퍼링:** SessionManager에 메모리 버퍼 유지

### 2. STT 최적화

- **스트리밍 STT:** 부분 결과 즉시 반환
- **최종 STT:** 발화 종료 시 전체 오디오 재처리
- **엔진 옵션:**
  - Whisper (로컬)
  - Google STT API
  - Azure Speech SDK

### 3. Spring 2 호출 최적화

- **비동기 전송:** `asyncio.create_task()` 사용
- **타임아웃:** 30초
- **재시도 정책:** 실패 시 로그만, WebSocket 유지

### 4. SessionManager 메모리 관리

- **세션 크기:** ~1MB (오디오 버퍼 포함)
- **동시 접속:** 1000명 = ~1GB
- **정리 전략:**
  - 세션 종료 시 즉시 cleanup
  - 만료 세션 주기적 정리 (백그라운드 태스크)

---

## 🔍 로깅 전략

### 주요 이벤트 로깅

```python
# 연결
logger.info(f"WebSocket connected: session_id={session_id}, user_id={user_id}")

# 메시지 수신
logger.debug(f"Received {msg_type} from session {session_id}")

# STT 결과
logger.info(f"STT final: session={session_id}, text='{stt_text}'")

# AI 응답
logger.info(f"AI reply: session={session_id}, text='{ai_text[:50]}...'")

# Spring 2 호출
logger.info(f"Saved utterance {index} to Spring 2: session={session_id}")

# 오류
logger.error(f"STT failed: session={session_id}, error={e}", exc_info=True)

# 연결 종료
logger.info(f"Session ended: {session_id}, reason={reason}")
```

### 로그 레벨

- **DEBUG:** 메시지 상세 (개발 환경)
- **INFO:** 주요 이벤트 (운영 환경)
- **WARNING:** 재시도, 대체 로직
- **ERROR:** 실패, 예외

---

## 🧪 테스트 전략

### 1. 단위 테스트

- SessionManager (세션 생성, 조회, 정리)
- STT Service (더미 오디오 처리)
- AI Service (응답 생성 로직)

### 2. 통합 테스트

- Redis 연결 및 세션 검증
- Spring 2 API 호출 (모킹)
- WebSocket 메시지 프로토콜

### 3. 부하 테스트

- 동시 접속 1000명
- 오디오 스트리밍 처리량
- Spring 2 호출 병목 확인

---

## 📚 참고 자료

### 관련 문서

- `docs/roleplaying_script.md` - 전체 아키텍처 설계
- `docs/architecture_script.md` - 서버 책임 분리
- `docs/db.sql` - PostgreSQL 스키마

### 기술 스택

- **FastAPI:** https://fastapi.tiangolo.com/
- **WebSockets:** https://fastapi.tiangolo.com/advanced/websockets/
- **Redis:** https://redis.io/docs/
- **httpx:** https://www.python-httpx.org/
- **Whisper:** https://github.com/openai/whisper

---

## 📝 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2025-11-17 | 1.0 | 초안 작성 |

---

**작성자:** Claude Code
**검토자:** SKALA Team
**문서 위치:** `/docs/websocket_realtime_architecture.md`