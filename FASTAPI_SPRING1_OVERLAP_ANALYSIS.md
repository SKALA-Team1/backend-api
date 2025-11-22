# FastAPI vs Spring 1: Responsibility Overlap Analysis

**Status:** 🚨 **CRITICAL ISSUE FOUND**

---

## Summary

**FastAPI is currently implementing work that should belong to Spring 1.** The `POST /sessions` endpoint in FastAPI is performing responsibilities that should be handled by Spring 1 Gateway:

1. **UUID Generation** - Creating session IDs (should come from Spring 1)
2. **Direct Client Handling** - Accepting HTTP requests directly from clients (should go through Spring 1)

**Note:** Redis storage and TTL management are correctly handled by FastAPI.

---

## Current (Incorrect) Flow

```
Client
  ↓
FastAPI POST /sessions (직접 호출) ❌ SHOULD GO THROUGH Spring 1
  ├─ SessionService.create_session()
  │   ├─ UUID 생성: uuid.uuid4()  ❌ SHOULD BE Spring 1
  │   ├─ DB 시나리오 조회 (OK)
  │   └─ Redis 저장 (TTL 2h)     ✅ CORRECT (FastAPI handles)
  ↓
Client receives: {session_id, ws_url, scenario}
  ↓
Client → FastAPI WebSocket (정상)
```

---

## Correct (Architecture) Flow

```
Client
  ↓
Spring 1 POST /roleplaying/sessions (API Gateway)
  ├─ JWT 검증                      ✅ Spring 1 책임
  ├─ UUID 생성                     ✅ Spring 1 책임
  └─ FastAPI 내부 호출 (session_id 전달)
  ↓
FastAPI 내부 처리
  ├─ session_id 받기               ✅ Spring 1에서 전달
  ├─ Spring 2 호출 (시나리오 조회) ✅ Spring 1 또는 FastAPI
  ├─ Redis 저장 (TTL 2h)          ✅ FastAPI 책임
  ├─ WS URL 생성                  ✅ FastAPI 책임
  ↓
Spring 1 → Client: {session_id, ws_url}
  ↓
Client → FastAPI WebSocket /ws/roleplaying/{session_id}
  ├─ 기존 세션 검증 (Redis에서)    ✅ FastAPI 책임
  ├─ STT 처리                      ✅ FastAPI 책임
  ├─ AI 응답 생성                  ✅ FastAPI 책임
  └─ 세션 데이터 관리             ✅ FastAPI 책임
```

---

## Issue Details

### File 1: `app/roleplaying/router.py` (Lines 114-157)

**Problem:** Endpoint directly accepting session creation from clients

```python
@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    ❌ PROBLEM: FastAPI is creating sessions directly
    This endpoint should NOT exist here.
    It should be in Spring 1 only.
    """
    session_id, scenario, expires_at = await session_service.create_session(
        user_id=request.userId,
        scenario_id=request.scenarioId,
        db=db,
        provided_session_id=request.sessionId
    )
    # ... returns session_id, ws_url, scenario
```

**Impact:**
- Clients call FastAPI directly (bypasses Spring 1 Gateway)
- JWT validation never happens (security issue)
- Spring 1 cannot track session lifecycle
- Distributed session management becomes impossible

---

### File 2: `app/roleplaying/services/session_service.py` (Lines 53-95)

**Problem:** Generating UUIDs (should receive from Spring 1)

```python
async def create_session(self, user_id, scenario_id, db, provided_session_id=None):
    # Step 1: DB 조회 (시나리오)
    scenario_detail = await self._get_scenario_from_db(scenario_id, user_id, db)

    # Step 2: UUID 생성 ❌ SHOULD BE Spring 1
    if provided_session_id is not None:
        session_id = str(provided_session_id)  # ✅ OK (from Spring 1)
    else:
        session_id = str(uuid.uuid4())  # ❌ SHOULD NOT GENERATE HERE

    # Step 3: Redis 저장 ✅ CORRECT
    expires_at = datetime.utcnow() + timedelta(hours=2)
    await self._save_session_to_redis(session_id, user_id, expires_at)
```

**Detail Breakdown:**

| Responsibility | Line | Status | Should Be |
|---|---|---|---|
| UUID 생성 | 84 | ❌ 잘못됨 | Spring 1에서 전달 |
| Redis 저장 | 88 | ✅ 정상 | FastAPI (내부 처리) |
| DB 조회 | 75 | ✅ 정상 | FastAPI (Spring 2 대신) |
| TTL 설정 | 87 | ✅ 정상 | FastAPI (내부 처리) |

---

### File 3: `app/roleplaying/services/session_service.py` (Lines 182-218)

**Status:** ✅ CORRECT - Redis storage is FastAPI's responsibility

```python
async def _save_session_to_redis(self, session_id, user_id, expires_at):
    redis_client = await self._get_redis_client()
    redis_key = f"session:{session_id}"

    session_data = {
        "userId": user_id,
        "role": "user",
        "scenarioType": "ROLEPLAYING",
        "startedAt": datetime.utcnow().isoformat() + "Z",
        "expiresAt": expires_at.isoformat() + "Z"
    }

    # TTL 2시간 ✅ CORRECT
    await redis_client.setex(redis_key, 7200, json.dumps(session_data))
```

**Note:** This method is correct and should be kept. FastAPI must manage Redis storage for session validation during WebSocket connections.

---

## What FastAPI SHOULD Do

FastAPI should:

1. ✅ **Receive session_id** from Spring 1 (already provided)
2. ✅ **Store to Redis** session data with TTL (internal processing)
3. ✅ **Validate** existing sessions during WebSocket (check Redis exists)
4. ✅ **Handle WebSocket** real-time audio streaming
5. ✅ **Process STT** with Deepgram
6. ✅ **Generate AI responses** with LLM
7. ✅ **Manage session state** during conversation

FastAPI should NOT:

- ❌ Generate UUIDs (accept from Spring 1)
- ❌ Accept direct client HTTP requests for session creation (should go through Spring 1)
- ❌ Validate JWT tokens (Spring 1's responsibility)

---

## Required Changes

### 1. Remove from FastAPI

**Delete endpoint:** `app/roleplaying/router.py` (Lines 114-157)

```python
# ❌ DELETE THIS ENDPOINT
@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(...):
    ...
```

**Refactor SessionService:** `app/roleplaying/services/session_service.py`

현재 코드는 `provided_session_id`가 있으면 사용하는 로직이 있는데, 이를 의존하도록 변경:

```python
# ❌ REMOVE: self-generating UUID when provided_session_id is None
# ✅ KEEP: _save_session_to_redis() - FastAPI 내부 처리에 필요
# ✅ KEEP: _get_scenario_from_db() - WebSocket 연결 시 검증에 필요

# 변경: create_session()은 내부 호출용으로 (항상 provided_session_id 필수)
# 삭제: 공개 HTTP 엔드포인트 (POST /sessions)
```

### 2. Create in Spring 1

**New endpoint:** `POST /roleplaying/sessions`

```kotlin
@PostMapping("/roleplaying/sessions")
@PreAuthorize("hasRole('USER')")
suspend fun createSession(
    @RequestBody request: SessionCreateRequest,
    @AuthenticationPrincipal user: UserPrincipal
): ResponseEntity<SessionCreateResponse> {
    // 1. JWT 검증 (자동, @PreAuthorize)
    val userId = user.id

    // 2. UUID 생성
    val sessionId = UUID.randomUUID().toString()

    // 3. Spring 2 호출 (시나리오 조회)
    val scenario = spring2Client.getScenario(request.scenarioId, userId)

    // 4. Redis 저장 (TTL 2시간)
    redisTemplate.opsForValue().set(
        "session:$sessionId",
        """{"userId": $userId, "scenario": ...}""",
        Duration.ofHours(2)
    )

    // 5. FastAPI WebSocket URL 생성
    val wsUrl = "ws://fastapi:8000/ws/roleplaying/$sessionId"

    return ResponseEntity.ok(
        SessionCreateResponse(sessionId, wsUrl, scenario)
    )
}
```

---

## Security Implications

### Current Risk (❌ HIGH)

```
Client → FastAPI /sessions (no JWT validation)
   ↓
SessionService.create_session() accepts ANY request
   ↓
User can create unlimited sessions without authentication
```

### After Fix (✅ SAFE)

```
Client → Spring 1 /roleplaying/sessions
   ↓
@PreAuthorize("hasRole('USER')") validates JWT
   ↓
UUID generated server-side
   ↓
Session stored only if user is authenticated
```

---

## Removed Files (Cleanup)

✅ **Already deleted 5 unused stub services:**
- `start_scenario_service.py`
- `finish_scenario_service.py`
- `get_status_service.py`
- `list_scenario_service.py`
- `message_flow_service.py`

---

## Summary Table

| Component | Current | Target | Status |
|---|---|---|---|
| HTTP endpoint for session creation | FastAPI | Spring 1 | ❌ WRONG |
| JWT validation | None | Spring 1 | ❌ MISSING |
| UUID generation | FastAPI | Spring 1 | ❌ WRONG |
| Redis storage (internal) | FastAPI | FastAPI | ✅ CORRECT |
| Redis TTL management | FastAPI | FastAPI | ✅ CORRECT |
| WebSocket handling | FastAPI | FastAPI | ✅ CORRECT |
| STT processing | FastAPI | FastAPI | ✅ CORRECT |
| AI response | FastAPI | FastAPI | ✅ CORRECT |
| Session validation | FastAPI | FastAPI | ✅ CORRECT |

---

## Next Steps

1. **Implement** `POST /roleplaying/sessions` in Spring 1
   - JWT 검증
   - UUID 생성
   - Spring 2 시나리오 조회
   - Redis 저장 (TTL 2시간)
   - FastAPI 내부 호출

2. **Delete** `POST /sessions` endpoint from FastAPI router (Lines 114-157 in `router.py`)

3. **Refactor** `SessionService.create_session()` in FastAPI
   - ❌ Remove UUID generation when `provided_session_id` is None
   - ✅ Keep `_save_session_to_redis()` - internal use only
   - ✅ Keep `_get_scenario_from_db()` - WebSocket validation
   - Make `provided_session_id` parameter required (not optional)

4. **Update** client code to call Spring 1 instead of FastAPI
   - Client: `POST /roleplaying/sessions` → Spring 1
   - Client: `WS /ws/roleplaying/{session_id}` → FastAPI (correct)

5. **Add tests** to verify responsibility boundaries
   - Spring 1: Can create sessions with authentication
   - FastAPI: Can only use provided session_ids
   - WebSocket: Validates session exists in Redis

---

## Reference

See `SYSTEM_ARCHITECTURE.md` for complete architecture overview.