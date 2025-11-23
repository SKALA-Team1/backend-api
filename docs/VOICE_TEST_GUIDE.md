# 🎙️ 음성 기반 롤플레잉 테스트 가이드

> 마이크 없이 더미 오디오로 음성 기반 롤플레잉을 테스트하는 완전한 자동화 가이드

---

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [자동화 스크립트 설명](#자동화-스크립트-설명)
3. [마이크 대체 방식](#마이크-대체-방식)
4. [테스트 플로우](#테스트-플로우)
5. [환경 설정](#환경-설정)
6. [문제 해결](#문제-해결)

---

## 🚀 빠른 시작

### 1️⃣ 한 줄 명령어 (전체 자동화)

```bash
bash scripts/test_voice_automated.sh
```

**자동으로 수행되는 작업:**
- ✅ Redis Docker 컨테이너 시작
- ✅ Ollama Docker 컨테이너 시작
- ✅ FastAPI 서버 시작
- ✅ 음성 기반 롤플레잉 테스트 실행

### 2️⃣ 테스트만 실행 (서버 이미 실행 중인 경우)

```bash
bash scripts/test_voice_automated.sh --only-test
```

### 3️⃣ Docker 건너뛰기 (이미 실행 중인 경우)

```bash
bash scripts/test_voice_automated.sh --skip-docker
```

---

## 📊 자동화 스크립트 설명

### 파일: `scripts/test_voice_automated.sh`

#### 역할

완전한 자동화 테스트 환경을 구축하고 실행합니다.

#### 수행 단계

```
Step 1: 전제 조건 확인
  ├─ Docker 설치 확인
  ├─ Python 3 설치 확인
  └─ curl 설치 확인

Step 2: Docker 서비스 시작
  ├─ Redis 컨테이너 시작
  │  └─ redis://localhost:6379
  └─ Ollama 컨테이너 시작
     ├─ Ollama API: http://localhost:11434
     └─ 모델 다운로드: mistral

Step 3: FastAPI 서버 시작
  └─ http://localhost:8082
     ├─ .env의 환경변수 자동 로드
     ├─ 데이터베이스 연결
     └─ Redis 세션 캐시 연결

Step 4: 테스트 실행
  └─ scripts/test_voice_client.py 실행

Step 5: 정리
  └─ FastAPI 서버 종료
  └─ Docker 컨테이너 정지 (선택사항)
```

#### 사용법

```bash
# 기본 사용
bash scripts/test_voice_automated.sh

# 옵션 추가
bash scripts/test_voice_automated.sh [옵션]

# 옵션:
#   --skip-docker       Docker 시작 건너뛰기
#   --skip-server       FastAPI 서버 시작 건너뛰기
#   --only-test         테스트만 실행
#   --keep-docker       테스트 후 Docker 유지
#   --help              도움말
```

#### 예시

```bash
# 전체 자동화
bash scripts/test_voice_automated.sh

# Docker는 이미 실행 중, FastAPI만 시작
bash scripts/test_voice_automated.sh --skip-docker

# 서비스는 이미 실행 중, 테스트만 실행
bash scripts/test_voice_automated.sh --skip-docker --skip-server

# 테스트 후 Docker 컨테이너 유지
bash scripts/test_voice_automated.sh --keep-docker
```

---

## 🎤 마이크 대체 방식

### 파일: `scripts/test_voice_client.py`

#### 음성 데이터 생성 방식

실제 마이크 없이 더미 오디오를 생성합니다:

#### 1️⃣ 무음 (Silence)

```python
# 방식: 모든 샘플이 0인 PCM 데이터
DummyAudioGenerator.generate_silence_chunk()

# 결과: 조용한 배경 노이즈
# 용도: 오디오 버퍼링 테스트
```

#### 2️⃣ 정현파 톤 (Sine Wave)

```python
# 방식: 특정 주파수의 정현파 생성
DummyAudioGenerator.generate_tone_chunk(
    frequency=440,  # A4 노트
    duration_ms=100,
    amplitude=1000
)

# 결과: 순수한 톤 (비프음)
# 용도: STT 엔진 테스트
```

#### 3️⃣ 음성 같은 오디오 (Speech-like)

```python
# 방식: 다양한 주파수 조합
DummyAudioGenerator.generate_speech_like_audio(
    duration_ms=500
)

# 구성:
#   - 저음역대 (150 Hz): 자음/자모음
#   - 중음역대 (500 Hz): 모음
#   - 고음역대 (2000 Hz): 자음
#
# 결과: 음성과 유사한 특성
# 용도: 실제 음성과 유사한 STT 테스트
```

### 오디오 포맷

```
PCM (Pulse Code Modulation)
├─ 비트 깊이: 16-bit (16,384 ~ -16,384 범위)
├─ 샘플링 레이트: 16,000 Hz (16 kHz)
├─ 채널: 모노 (1 channel)
└─ 바이너리 형식: Little-endian
```

### 생성 과정

```
수학 공식:
  sample = amplitude × sin(2π × frequency × n / sample_rate)

예시 (frequency=440 Hz, duration=100ms, sample_rate=16000):
  - 생성 샘플 수: 16000 × 0.1 = 1,600 샘플
  - 바이너리 크기: 1,600 × 2 bytes = 3,200 bytes
```

---

## 🔄 테스트 플로우

### 전체 시나리오

```
┌────────────────────────────────────────────────────────┐
│ Step 1: 세션 생성 (REST API)                            │
│                                                         │
│ POST /roleplaying/sessions                             │
│ {                                                       │
│   "userId": 1,                                          │
│   "scenarioId": 1                                       │
│ }                                                       │
│                                                         │
│ Response:                                               │
│ {                                                       │
│   "session_id": "abc-123-def",                          │
│   "ws_url": "ws://localhost:8082/ws/roleplaying/...",  │
│   "scenario": { ... }                                   │
│ }                                                       │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ Step 2: WebSocket 연결                                  │
│                                                         │
│ WS ws://localhost:8082/ws/roleplaying/abc-123-def      │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ Step 3: INIT 메시지 전송                                 │
│                                                         │
│ {                                                       │
│   "type": "INIT",                                       │
│   "userId": 1,                                          │
│   "subjectId": 123,                                     │
│   "myRole": "Software Engineer",                        │
│   "aiRole": "Tech Lead",                                │
│   "fixedQuestions": [                                   │
│     "Can you introduce yourself?",                      │
│     "What challenges?",                                 │
│     "Next steps?"                                       │
│   ]                                                     │
│ }                                                       │
│                                                         │
│ ← ACK 수신                                              │
│ ← AI 첫 질문 수신                                        │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ Step 4: 오디오 청크 전송 (더미 데이터)                   │
│                                                         │
│ 3개의 청크 반복 전송:                                     │
│ [음성 오디오 바이너리] (500ms × 3)                        │
│                                                         │
│ ← STT 부분 결과 (선택사항)                               │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ Step 5: UTTERANCE_END 메시지                            │
│                                                         │
│ {                                                       │
│   "type": "UTTERANCE_END"                               │
│ }                                                       │
│                                                         │
│ ← STT 최종 결과                                         │
│ ← AI 응답 생성 중 (AI_TYPING)                            │
│ ← AI 응답 (AI_TEXT)                                     │
└────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────┐
│ Step 6: END_SESSION 메시지                              │
│                                                         │
│ {                                                       │
│   "type": "END_SESSION"                                 │
│ }                                                       │
│                                                         │
│ ← SESSION_ENDED                                         │
└────────────────────────────────────────────────────────┘
```

### 메시지 상세

#### 클라이언트 → 서버

```javascript
// 1. INIT
{
  "type": "INIT",
  "userId": 1,
  "subjectId": 123,
  "myRole": "Software Engineer",
  "aiRole": "Tech Lead",
  "fixedQuestions": ["Q1", "Q2", "Q3"]
}

// 2. AUDIO_CHUNK (반복)
[바이너리 오디오 데이터]

// 3. UTTERANCE_END
{
  "type": "UTTERANCE_END"
}

// 4. END_SESSION
{
  "type": "END_SESSION"
}
```

#### 서버 → 클라이언트

```javascript
// 1. ACK
{
  "type": "ACK",
  "message": "Session initialized"
}

// 2. AI_TEXT (첫 질문)
{
  "type": "AI_TEXT",
  "text": "Can you introduce yourself?",
  "is_fixed_question": true
}

// 3. STT_PARTIAL (선택사항)
{
  "type": "STT_PARTIAL",
  "text": "I'm a backend"
}

// 4. STT_FINAL
{
  "type": "STT_FINAL",
  "text": "I'm a backend developer"
}

// 5. AI_TYPING
{
  "type": "AI_TYPING"
}

// 6. AI_TEXT (응답)
{
  "type": "AI_TEXT",
  "text": "What specific technologies are you using?",
  "is_fixed_question": false
}

// 7. SESSION_ENDED
{
  "type": "SESSION_ENDED",
  "reason": "user_end"
}
```

---

## ⚙️ 환경 설정

### .env 파일 (자동 로드)

```bash
# 데이터베이스
DATABASE_URL=mysql+pymysql://root:denny1302!@localhost:3306/skuseme_db

# Redis
REDIS_URL=redis://localhost:6379/0

# FastAPI
FASTAPI_PORT=8082

# 웹소켓
WS_BASE_URL=ws://localhost:8082

# STT
DEEPGRAM_API_KEY=a2641a52fcec8a44e58792130734a71fac631285

# Spring 서버
SPRING1_BASE_URL=http://localhost:8080
SPRING2_BASE_URL=http://localhost:8081
```

### Docker 컨테이너 포트 매핑

```
Redis:   localhost:6379   (내부 6379)
Ollama:  localhost:11434  (내부 11434)
FastAPI: localhost:8082   (내부 8082)
```

---

## 🔧 문제 해결

### 문제 1: "Docker이 설치되지 않았습니다"

```bash
# Docker 설치
# macOS
brew install docker

# Ubuntu
sudo apt-get install docker.io

# Windows
# https://www.docker.com/products/docker-desktop
```

### 문제 2: "Permission denied while trying to connect to Docker daemon"

```bash
# Linux에서:
sudo usermod -aG docker $USER
newgrp docker
# 또는
sudo chmod 666 /var/run/docker.sock
```

### 문제 3: "Redis 시작 실패"

```bash
# 기존 Redis 컨테이너 정리
docker stop redis-voice-test 2>/dev/null || true
docker rm redis-voice-test 2>/dev/null || true

# 다시 시도
bash scripts/test_voice_automated.sh --skip-docker
```

### 문제 4: "FastAPI 시작 실패"

```bash
# 로그 확인
tail -f /tmp/fastapi.log

# 포트 점유 확인
lsof -i :8082

# 기존 프로세스 종료
kill -9 $(lsof -t -i:8082)
```

### 문제 5: "Deepgram API Key 오류"

```bash
# .env 파일 확인
cat .env | grep DEEPGRAM_API_KEY

# API Key 설정
export DEEPGRAM_API_KEY=your_actual_key_here

# 다시 시도
bash scripts/test_voice_automated.sh
```

### 문제 6: "WebSocket 연결 거부"

```bash
# FastAPI 서버 상태 확인
curl http://localhost:8082/health/ping

# 서버 로그 확인
tail -f /tmp/fastapi.log

# 포트 확인
netstat -tuln | grep 8082
```

---

## 📊 테스트 결과 해석

### 성공 사례

```
✅ 세션 생성됨: abc-123-def
✅ WebSocket 연결됨
📤 INIT 메시지 전송
📥 ACK 수신: Session initialized
🤖 AI (Turn 1): Can you introduce yourself?
📤 오디오 청크 전송 (3개)
   청크 1/3 전송 (3200 bytes)
   청크 2/3 전송 (3200 bytes)
   청크 3/3 전송 (3200 bytes)
✅ 오디오 청크 전송 완료
📤 UTTERANCE_END 메시지 전송
   STT (부분): I'm
   STT (부분): I'm a backend
✅ STT (최종): I'm a backend developer
   💭 AI 생각 중...
🤖 AI 응답 (동적): What specific technologies are you using?
📤 END_SESSION 메시지 전송
✅ 세션 종료됨 (reason: user_end)

==================================================
✅ 모든 테스트 통과!
==================================================
```

### 실패 원인 분석

| 에러 메시지 | 원인 | 해결책 |
|-----------|------|--------|
| "세션 생성 실패" | FastAPI 미응답 | FastAPI 서버 확인 |
| "WebSocket 연결 실패" | 포트 점유 | `lsof -i :8082` 확인 |
| "STT 타임아웃" | Deepgram API 오류 | API Key 확인 |
| "AI 응답 타임아웃" | LLM 서버 미응답 | Ollama 상태 확인 |

---

## 🎯 다음 단계

### 1️⃣ 실제 마이크 연결

```python
# 마이크 입력 대신 파일에서 오디오 읽기
with open("sample_audio.wav", "rb") as f:
    audio_data = f.read()
    # 위의 더미 오디오 대신 사용
```

### 2️⃣ 다중 턴 테스트

```bash
# 여러 UTTERANCE_END 반복 (최대 10턴)
for i in {1..5}; do
  send_audio_chunks
  send_utterance_end
done
```

### 3️⃣ 성능 측정

```python
import time

start = time.time()
await client.send_utterance_end()
elapsed = time.time() - start

print(f"AI 응답 시간: {elapsed:.2f}초")
```

---

## 📚 참고 자료

- [WebSocket 메시지 스키마](../docs/WS_MESSAGES.md)
- [STT 구현](../app/roleplaying/services/stt_service.py)
- [AI 튜터 서비스](../app/roleplaying/services/ai_tutor_service.py)
- [세션 관리](../app/roleplaying/session_manager.py)

---

**마지막 업데이트**: 2025-11-21
**테스트 환경**: FastAPI 8082, Redis, Ollama, Deepgram