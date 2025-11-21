# Spring 2 Phase 1 - 필수 API 구현

> FastAPI와 Spring 2 간 필수 API 3개 구현 가이드

---

## 📋 Phase 1 구현 항목

Spring 2에서 구현해야 할 필수 API 3개:

### 1. 세션 조회 API

**엔드포인트**:
```
GET /internal/sessions/{session_id}
```

**설명**: FastAPI에서 Redis 캐시 미스 시 세션 정보를 조회합니다.

**응답**:
```json
{
  "success": true,
  "user_id": 1,
  "scenario_id": 31,
  "status": "ACTIVE",
  "created_at": "2025-11-21T10:00:00Z",
  "expires_at": "2025-11-21T12:00:00Z"
}
```

**에러 응답** (404):
```json
{
  "success": false,
  "error": "Session not found"
}
```

---

### 2. 발화 저장 API

**엔드포인트**:
```
POST /internal/sessions/{session_id}/utterances
```

**설명**: 사용자/AI 발화 데이터를 저장합니다.

**요청 1 (텍스트만)**:
```json
{
  "utterance_index": 2,
  "speaker": "user",
  "text": "안녕하세요, 백엔드 개발자입니다."
}
```

**요청 2 (오디오 + 텍스트)**:
```
multipart/form-data:
  - utterance_index: 2
  - speaker: "user"
  - text: "[STT Result] Hello, I'm a backend developer"
  - audio_file: <바이너리 WAV/MP3>
```

**응답** (200 OK):
```json
{
  "success": true,
  "utterance_id": "ut_9001",
  "session_id": "session_abc123",
  "saved_at": "2025-11-21T10:02:30Z"
}
```

**데이터베이스 스키마**:
```sql
CREATE TABLE utterances (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id VARCHAR(36) NOT NULL,
  utterance_index INT NOT NULL,
  speaker ENUM('user', 'ai') NOT NULL,
  text TEXT NOT NULL,
  audio_s3_url VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_session_index (session_id, utterance_index),
  INDEX idx_session_id (session_id)
);
```

---

### 3. 세션 완료 API

**엔드포인트**:
```
POST /internal/sessions/{session_id}/complete
```

**설명**: 롤플레잉 세션 종료 시 상태를 업데이트합니다.

**요청**:
```json
{
  "status": "FINISHED",
  "reason": "turn_limit"
}
```

**응답** (200 OK):
```json
{
  "success": true,
  "session_id": "session_abc123",
  "completed_at": "2025-11-21T10:10:00Z"
}
```

**reason 값**:
- `turn_limit`: 최대 10턴 도달
- `timeout`: 세션 만료 시간 초과
- `user_end`: 사용자 직접 종료
- `error`: 서버 에러

---

## ✅ 체크리스트

### API 1: 세션 조회
- [ ] 엔드포인트 구현
- [ ] 데이터베이스 쿼리
- [ ] 만료 시간 확인 로직
- [ ] 테스트 (정상, 404, 만료)

### API 2: 발화 저장
- [ ] multipart/form-data 파싱
- [ ] 텍스트 저장 (DB)
- [ ] 오디오 저장 (S3/MinIO)
- [ ] 트랜잭션 처리
- [ ] 테스트 (텍스트만, 오디오+텍스트)

### API 3: 세션 완료
- [ ] 엔드포인트 구현
- [ ] 세션 상태 업데이트
- [ ] 멱등성 보장
- [ ] 테스트

---

## 🧪 테스트 명령어

```bash
# 1. 세션 조회
curl -X GET http://localhost:8081/internal/sessions/{session_id}

# 2. 발화 저장 (텍스트만)
curl -X POST http://localhost:8081/internal/sessions/{session_id}/utterances \
  -H "Content-Type: application/json" \
  -d '{
    "utterance_index": 1,
    "speaker": "user",
    "text": "Hello, I am a backend developer"
  }'

# 3. 발화 저장 (오디오 + 텍스트)
curl -X POST http://localhost:8081/internal/sessions/{session_id}/utterances \
  -F "utterance_index=1" \
  -F "speaker=user" \
  -F "text=Hello" \
  -F "audio_file=@audio.wav"

# 4. 세션 완료
curl -X POST http://localhost:8081/internal/sessions/{session_id}/complete \
  -H "Content-Type: application/json" \
  -d '{
    "status": "FINISHED",
    "reason": "turn_limit"
  }'
```

---

## 📍 FastAPI 호출 위치

이 3개 API는 FastAPI에서 다음 위치에서 호출됩니다:

**파일**: `app/roleplaying/spring2_client.py`

```python
# API 1 호출
await spring2_client.get_session(session_id)

# API 2 호출
await spring2_client.save_utterance(
    session_id=session_id,
    stt_text=stt_text,
    utterance_index=utterance_index,
    speaker="user",
    audio_data=audio_bytes
)

# API 3 호출
await spring2_client.complete_session(
    session_id=session_id,
    status="FINISHED",
    reason="turn_limit"
)
```

---

**작성일**: 2025-11-21