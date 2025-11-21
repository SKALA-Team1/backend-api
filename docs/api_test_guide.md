# 롤플레잉 세션 API 테스트 가이드

이 문서는 롤플레잉 세션 생성 API를 curl/Postman으로 테스트하는 방법을 설명합니다.

## 📋 사전 준비

### 1. 로컬 환경 실행

```bash
# 1. Docker Compose 실행 (Redis + MinIO)
cd infra
docker-compose -f docker-compose.dev.yml up -d

# 2. Redis 연결 확인
docker exec -it redis redis-cli ping
# 응답: PONG

# 3. FastAPI 서버 실행
cd ..
uvicorn app.main:app --reload --port 8001
```

### 2. DB 테스트 데이터 준비

세션 생성 API는 DB에서 시나리오를 조회하므로, 먼저 테스트 시나리오를 DB에 생성해야 합니다.

**MySQL에 직접 삽입하는 방법:**

```sql
-- 1. subject 테이블에 주제 삽입
INSERT INTO subject (user_id, my_role, ai_role, topic_type, source_type, created_at)
VALUES (1, 'Software Engineer', 'Tech Lead', 'detail', 'slack', NOW());

-- subject_id 확인 (예: 100)
SELECT LAST_INSERT_ID();

-- 2. scenario 테이블에 시나리오 삽입
INSERT INTO scenario (
    user_id,
    subject_id,
    title,
    status,
    fixed_questions,
    created_at
)
VALUES (
    1,
    100,  -- 위에서 생성한 subject_id
    'Daily Standup Discussion with Tech Lead',
    'generated',
    JSON_ARRAY(
        'Can you introduce yourself and your current project?',
        'What technical challenges are you facing?',
        'What are your next steps?'
    ),
    NOW()
);

-- scenario_id 확인 (예: 500)
SELECT LAST_INSERT_ID();
```

**또는 Spring 2 API를 사용하는 방법:**

Spring 2에서 Slack 대화 분석 API를 통해 시나리오를 자동 생성할 수 있습니다.
(Spring 2 팀이 해당 API 구현 후 사용 가능)

---

## 🧪 API 테스트

### API 엔드포인트

```
POST http://localhost:8001/roleplaying/sessions
```

### Request 형식

```json
{
  "userId": 1,
  "scenarioId": 500
}
```

### curl 테스트

```bash
curl -X POST "http://localhost:8001/roleplaying/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 1,
    "scenarioId": 500
  }'
```

### 성공 응답 예시

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "ws_url": "ws://localhost:8001/ws/roleplaying/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "scenario": {
    "scenarioId": 500,
    "subjectId": 100,
    "myRole": "Software Engineer",
    "aiRole": "Tech Lead",
    "title": "Daily Standup Discussion with Tech Lead",
    "topicType": "detail",
    "fixedQuestions": [
      "Can you introduce yourself and your current project?",
      "What technical challenges are you facing?",
      "What are your next steps?"
    ]
  },
  "expires_at": "2025-11-17T12:00:00Z"
}
```

### 에러 응답 예시

**404 - 시나리오를 찾을 수 없음:**

```json
{
  "detail": "Scenario 500 not found for user 1"
}
```

**400 - 잘못된 요청:**

```json
{
  "detail": [
    {
      "loc": ["body", "userId"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## 🔌 WebSocket 연결 테스트

세션 생성 후, 반환된 `ws_url`을 사용하여 WebSocket 연결을 테스트할 수 있습니다.

### Python 스크립트로 테스트

```bash
# 1) REST API로 세션 생성 + 2) WebSocket 흐름 실행
python scripts/test_websocket_with_session.py <user_id> <scenario_id>
```

**scripts/test_websocket_with_session.py 요약:**

```python
payload = await create_session(user_id, scenario_id)
ws_url = payload["ws_url"]
scenario = payload["scenario"]

init_message = {
    "type": "INIT",
    "userId": user_id,
    "subjectId": scenario["subjectId"],
    "myRole": scenario["myRole"],
    "aiRole": scenario["aiRole"],
    "fixedQuestions": scenario["fixedQuestions"],  # DB에서 조회된 값 그대로 사용
}
```

---

## 📊 Postman 테스트

### Request 설정

1. **Method:** `POST`
2. **URL:** `http://localhost:8001/roleplaying/sessions`
3. **Headers:**
   - `Content-Type: application/json`
4. **Body (raw JSON):**
   ```json
   {
     "userId": 1,
     "scenarioId": 500
   }
   ```

### Environment Variables 설정 (선택)

Postman 환경 변수를 설정하면 테스트가 더 편리합니다:

- `BASE_URL`: `http://localhost:8001`
- `USER_ID`: `1`
- `SCENARIO_ID`: `500`

사용 예시:
```
POST {{BASE_URL}}/roleplaying/sessions

Body:
{
  "userId": {{USER_ID}},
  "scenarioId": {{SCENARIO_ID}}
}
```

---

## 🔍 Redis 세션 확인

세션이 Redis에 저장되었는지 확인:

```bash
# Redis CLI 접속
docker exec -it redis redis-cli

# 세션 조회
GET session:<session_id>

# 예:
# GET session:a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**저장된 데이터 예시:**

```json
{
  "userId": 1,
  "role": "user",
  "scenarioType": "ROLEPLAYING",
  "startedAt": "2025-11-17T10:00:00Z",
  "expiresAt": "2025-11-17T12:00:00Z"
}
```

---

## ⚠️ 주의사항

1. **DB 시나리오 상태**: `status = 'generated'`인 시나리오만 조회됩니다.
2. **사용자 ID 일치**: 시나리오의 `user_id`와 요청의 `userId`가 일치해야 합니다.
3. **fixed_questions**: DB의 `fixed_questions` 컬럼은 JSON 배열이어야 하며, 3개의 질문이 포함되어야 합니다.
4. **세션 TTL**: Redis에 저장된 세션은 2시간 후 자동으로 만료됩니다.
5. **WebSocket 연결**: 세션 생성 직후 WebSocket 연결을 시도해야 합니다. (만료 전)

---

## 🐛 트러블슈팅

### "Scenario not found" 에러

- DB에 해당 시나리오가 존재하는지 확인
- `user_id`가 일치하는지 확인
- `status = 'generated'`인지 확인

```sql
SELECT * FROM scenario WHERE scenario_id = 500 AND user_id = 1 AND status = 'generated';
```

### Redis 연결 실패

```bash
# Redis 컨테이너 상태 확인
docker ps | grep redis

# Redis 재시작
docker restart redis
```

### DB 연결 실패

- `.env` 파일의 DB 설정 확인
- MySQL 서버가 실행 중인지 확인

---

## 📝 다음 단계

1. 세션 생성 후 WebSocket 연결
2. 오디오 스트리밍 테스트
3. STT → AI 응답 → TTS 전체 플로우 테스트
4. 세션 종료 후 피드백 리포트 생성 (향후 구현)
