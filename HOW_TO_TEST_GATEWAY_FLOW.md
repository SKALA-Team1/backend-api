# Gateway → FastAPI → Spring2 → MySQL 전체 흐름 테스트 가이드

## 🎯 목표
Gateway가 직접 FastAPI에 요청하여 시나리오를 생성하고 DB에 저장하는 전체 흐름 테스트

## 📋 사전 준비

### 1. 모든 서버 실행 확인
```bash
# Spring2 (포트 8081)
# FastAPI (포트 8082)
# Gateway (포트 8080) ← 새로운 코드가 반영되도록 재시작 필요!
```

### 2. Gateway 재시작
새로 추가된 `/scenarios/textbook/generate` 엔드포인트를 사용하려면 Gateway를 재시작해야 합니다.

```bash
cd /Users/younashin/backend-gateway
# 기존 실행 중인 Gateway 중지 후
./gradlew bootRun  # 또는 IDE에서 재실행
```

## 🔑 Step 1: JWT 토큰 획득

### Option A: 로그인 API 사용
```bash
curl -X POST "http://localhost:8080/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'
```

응답에서 `access_token`을 복사합니다:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "..."
}
```

### Option B: 기존 토큰 사용
이미 가지고 있는 JWT 토큰이 있다면 그것을 사용하세요.

## 🚀 Step 2: Gateway에 시나리오 생성 요청

복사한 JWT 토큰을 `YOUR_JWT_TOKEN` 자리에 붙여넣으세요:

```bash
curl -X POST "http://localhost:8080/scenarios/textbook/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "회의 진행",
    "scenarioType": "meeting",
    "difficulty": "intermediate",
    "numTurns": 20,
    "chapterFilter": "Chapter 02: Conducting Weekly Meetings (주간미팅 진행하기)",
    "includeKoreanHints": true,
    "saveToDb": true
  }' | python3 -m json.tool
```

## 📊 이 명령이 실행하는 전체 흐름

1. **Client (curl)** → Gateway에 HTTP POST 요청 전송
   - JWT 토큰을 Authorization 헤더에 포함

2. **Gateway (8080)** → JWT 검증 및 userId 추출
   - ScenarioController.generateTextbookScenario() 호출
   - SecurityContext에서 사용자 ID 추출

3. **Gateway → FastAPI (8082)** 직접 HTTP 요청
   - FastApiClient.generateTextbookScenario() 실행
   - WebClient로 `/scenario/generate` 엔드포인트 호출

4. **FastAPI (8082)** → RAG로 교재 내용 검색
   - Qdrant DB에서 관련 챕터 내용 검색
   - AI로 시나리오 생성

5. **FastAPI → Spring2 (8081)** DB 저장 요청
   - `/api/v1/scenarios` 엔드포인트 호출

6. **Spring2 (8081)** → MySQL에 시나리오 저장
   - DB에 영구 저장

7. **응답 역순으로 반환**
   - Spring2 → FastAPI → Gateway → Client

## ✅ 성공 응답 예시

```json
{
  "scenario_id": "abc-123",
  "title": "주간 미팅 진행하기",
  "dialogues": [
    {
      "turn": 1,
      "speaker": "user",
      "text": "Good morning everyone...",
      "korean_hint": "좋은 아침입니다 여러분"
    },
    ...
  ],
  "db_scenario_id": 45,
  "saved_to_db": true
}
```

## 🔍 확인 방법

### Gateway 로그 확인
```
INFO  [ScenarioController] Generate textbook scenario endpoint called: topic=회의 진행
INFO  [ScenarioService] Generating textbook scenario for userId: 123
INFO  [FastApiClient] Calling FastAPI for textbook scenario: user=123, topic=회의 진행
INFO  [FastApiClient] FastAPI scenario generation succeeded for user=123
```

### FastAPI 로그 확인
```
INFO: Received textbook scenario generation request for user_id=123
INFO: Found 5 relevant chunks for chapter filter
INFO: Generated scenario with 20 turns
INFO: Saved scenario to Spring2, db_scenario_id=45
```

### Spring2 로그 확인
```
INFO: Received scenario save request for userId=123
INFO: Saved scenario with id=45
```

### MySQL에서 직접 확인
```sql
SELECT * FROM scenarios WHERE user_id = 123 ORDER BY created_at DESC LIMIT 1;
```

## ⚠️ 주의사항

1. **JWT 토큰**: 반드시 유효한 JWT 토큰을 사용하세요
2. **Gateway 재시작**: 새 코드를 반영하려면 Gateway를 재시작해야 합니다
3. **포트 확인**: Gateway(8080), Spring2(8081), FastAPI(8082) 포트가 맞는지 확인
4. **타임아웃**: 시나리오 생성은 30초 정도 걸릴 수 있습니다 (AI 생성 시간)

## 🎬 빠른 실행

```bash
# 1. JWT 토큰 변수에 저장
export JWT_TOKEN="여기에_실제_토큰_붙여넣기"

# 2. 요청 전송
curl -X POST "http://localhost:8080/scenarios/textbook/generate" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "회의 진행",
    "scenarioType": "meeting",
    "difficulty": "intermediate",
    "numTurns": 20,
    "chapterFilter": "Chapter 02: Conducting Weekly Meetings (주간미팅 진행하기)",
    "includeKoreanHints": true,
    "saveToDb": true
  }' | python3 -m json.tool
```

이 방식이 **Gateway가 직접 FastAPI에 요청하는** 올바른 방법입니다!
