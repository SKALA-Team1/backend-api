# 음성 기반 롤플레잉 테스트 가이드

## 🎯 개요

이 가이드는 음성 기반 롤플레잉 시스템의 테스트 방법을 설명합니다.

### 테스트 방식
- **더미 오디오**: 실제 마이크 없이 테스트 (권장, 안정적)
- **실제 마이크**: 마이크를 사용한 실시간 테스트
- **텍스트**: STT 없이 텍스트로 직접 테스트
- **대화형**: 각 단계마다 엔터 키로 진행

---

## 📋 빠른 시작

### 1️⃣ 서버 시작

**터미널 1에서:**
```bash
# 서버 시작
bash scripts/start_server.sh
```

### 2️⃣ 테스트 실행

**터미널 2에서 - 가장 간단한 테스트 (더미 오디오):**
```bash
bash scripts/test_voice_modes.sh dummy
```

---

## 🧪 다양한 테스트 모드

### 1. 더미 오디오 테스트 (권장)

**특징**
- 실제 마이크 필요 없음
- 안정적이고 재현 가능
- 가장 빠른 테스트

**실행**
```bash
bash scripts/test_voice_modes.sh dummy
```

---

### 2. 실제 마이크 테스트

#### 2.1 기본 마이크 테스트 (3초 녹음)

**특징**
- 실제 마이크 음성 사용
- 3초 동안 녹음
- Deepgram STT로 변환

**실행**
```bash
bash scripts/test_voice_modes.sh mic
```

#### 2.2 장시간 마이크 테스트 (5초 녹음)

**특징**
- 5초 동안 녹음 가능
- 더 자연스러운 발화

**실행**
```bash
bash scripts/test_voice_modes.sh mic-long
```

---

### 3. 텍스트 기반 테스트

**특징**
- STT 없이 텍스트로 직접 대화
- 마이크 필요 없음
- STT 오류 검증 가능

**실행**
```bash
bash scripts/test_voice_modes.sh text
```

---

### 4. 대화형 모드

**특징**
- 각 단계마다 엔터 키로 진행
- 수동으로 각 단계 제어 가능

**실행 - 더미 오디오 모드**
```bash
bash scripts/test_voice_modes.sh interactive
```

**실행 - 마이크 모드**
```bash
bash scripts/test_voice_modes.sh interactive --mic
```

---

### 5. 다중 반복 테스트

**특징**
- 같은 테스트를 3회 반복
- 안정성 검증

**실행**
```bash
bash scripts/test_voice_modes.sh multi
```

---

### 6. 데모 시나리오

**특징**
- 3턴 전체 대화 시연
- 텍스트 기반 (마이크 없음)

**실행**
```bash
bash scripts/test_voice_modes.sh demo
```

---

## 🎮 마이크 버튼 역할 (자동화 방식)

### 전체 흐름도

```
┌─────────────────────────────────────┐
│     클라이언트 (테스트 스크립트)       │
└─────────────────────────────────────┘
              │
              ▼
    1️⃣ 대화 시작: INIT 메시지
              │
              ▼
      ┌───────────────┐
      │ 🤖 AI 첫 인사 │
      └───────────────┘
              │
              ▼
    2️⃣ 사용자 발화 [마이크 ON]
    - 오디오 청크 전송 (100ms씩)
    - 3개 청크 = ~300ms 음성
              │
              ▼
    3️⃣ 발화 종료 [마이크 OFF]
    - UTTERANCE_END 메시지
              │
              ▼
      ┌───────────────┐
      │  STT 변환     │
      │ (Deepgram)    │
      └───────────────┘
              │
              ▼
      ┌───────────────┐
      │ 🤖 AI 응답 생성│
      └───────────────┘
              │
              ▼
    4️⃣ 대화 반복 또는 종료
    - 2-3턴 반복
    - END_SESSION으로 종료
```

### 마이크 버튼 역할 대응 관계

| UI 마이크 버튼 | 자동화 시스템 | 코드 위치 |
|---|---|---|
| **버튼 누름 (녹음 시작)** | `INIT` 메시지 전송 | `ws_realtime.py:131-135` |
| **마이크 대고 말하기** | 오디오 청크 WebSocket으로 전송 | `ws_realtime.py:110-118` |
| **버튼 뗌 (녹음 종료)** | `UTTERANCE_END` 메시지 전송 | `ws_realtime.py:139-148` |
| **(자동) STT 변환** | Deepgram 호출 | `stt_service.py:492` |
| **(자동) AI 응답** | AI 튜터 서비스 호출 | `ws_realtime.py:565-567` |
| **다시 버튼 누름** | 반복 (2번째 턴) | `ws_realtime.py:105-177` |
| **세션 종료** | `END_SESSION` 메시지 | `ws_realtime.py:180-182` |

---

## 📊 WebSocket 메시지 흐름

### 클라이언트 → 서버

```
1. INIT (JSON)
   {
     "type": "INIT",
     "userId": 1,
     "subjectId": "fix-reports-endpoint",
     "myRole": "junior developer",
     "aiRole": "senior developer",
     "fixedQuestions": [...]
   }

2. 오디오 청크 (Binary)
   [PCM 16-bit, 16kHz 오디오 바이트]
   (100ms씩 3개 청크)

3. UTTERANCE_END (JSON)
   {
     "type": "UTTERANCE_END"
   }

4. END_SESSION (JSON)
   {
     "type": "END_SESSION"
   }
```

### 서버 → 클라이언트

```
1. ACK
   {
     "type": "ACK",
     "message": "Session initialized"
   }

2. AI_TEXT (첫 질문)
   {
     "type": "AI_TEXT",
     "text": "Can you summarize...",
     "is_fixed_question": true
   }

3. STT_FINAL (최종 결과)
   {
     "type": "STT_FINAL",
     "text": "The answer is in the logs"
   }

4. UTTERANCE_SAVED
   {
     "type": "UTTERANCE_SAVED",
     "index": 1
   }

5. AI_TYPING (생각 중)
   {
     "type": "AI_TYPING"
   }

6. AI_TEXT (응답)
   {
     "type": "AI_TEXT",
     "text": "Good observation...",
     "is_fixed_question": false
   }

7. SESSION_ENDED
   {
     "type": "SESSION_ENDED",
     "reason": "user_end"
   }
```

---

## 🔧 상세 옵션

### test_voice_modes.sh

다양한 테스트 모드를 제공하는 스크립트

```bash
# 사용법
bash scripts/test_voice_modes.sh [모드]

# 모드
dummy         더미 오디오 테스트 (권장)
mic           마이크 테스트 (3초)
mic-long      마이크 테스트 (5초)
text          텍스트 기반 테스트
interactive   대화형 모드
multi         3회 반복 테스트
demo          데모 시나리오 (3턴)

# 예시
bash scripts/test_voice_modes.sh demo
bash scripts/test_voice_modes.sh interactive --mic
```

### test_voice_flow.sh

원본 통합 테스트 스크립트 (향상된 버전)

```bash
bash scripts/test_voice_flow.sh [옵션]

# 옵션
--use-mic                실제 마이크 사용
--record-duration N      녹음 시간 (초, 기본값: 3)
--iterations N           테스트 반복 횟수
--server-only            서버만 시작
--test-only              테스트만 실행
--verbose                상세 로깅
--interactive            대화형 모드
```

### test_voice_client.py

저수준 테스트 클라이언트

```bash
python scripts/test_voice_client.py [옵션]

# 옵션
--fastapi-url URL        FastAPI 베이스 URL (기본값: http://localhost:8082)
--user-id N              사용자 ID (기본값: 1)
--scenario-id N          시나리오 ID (기본값: 1)
--use-mic                실제 마이크 사용
--record-duration N      녹음 시간 (초, 기본값: 3)
--verbose                상세 로깅

# 예시
python scripts/test_voice_client.py --use-mic --record-duration 5 --verbose
```

---

## 📝 로그 확인

### 서버 로그
```bash
# 실시간 감시
tail -f logs/server.log

# 특정 에러 찾기
grep -i error logs/server.log
grep "Silence detected" logs/server.log
```

### 테스트 로그
```bash
tail -f logs/test.log
```

---

## ⚠️ 일반적인 문제 해결

### 1. "Silence detected" 에러

**원인**: 마이크에서 음성이 감지되지 않음

**해결책**
```bash
# 1️⃣ 더미 오디오로 먼저 테스트
bash scripts/test_voice_modes.sh dummy

# 2️⃣ 마이크 설정 확인 (macOS)
System Settings → Sound → Input

# 3️⃣ 마이크 권한 확인 (macOS)
System Settings → Privacy & Security → Microphone

# 4️⃣ 긴 녹음 시간으로 테스트
bash scripts/test_voice_modes.sh mic-long

# 5️⃣ 텍스트 모드로 STT 없이 테스트
bash scripts/test_voice_modes.sh text
```

### 2. "WebSocket connection timeout"

**원인**: 서버가 실행 중이지 않음

**해결책**
```bash
# 터미널 1에서 서버 시작
bash scripts/start_server.sh

# 연결 확인
curl http://localhost:8082/docs

# 로그 확인
tail -f logs/server.log
```

### 3. "Session not initialized"

**원인**: INIT 메시지를 먼저 보내지 않음

**해결책**
- 테스트 스크립트는 자동으로 INIT을 처리합니다
- 수동으로 테스트하는 경우 INIT 메시지를 먼저 보내세요

---

## 📚 관련 파일

```
Backend/
├── scripts/
│   ├── start_server.sh           # 서버 시작
│   ├── test_voice_client.py      # 저수준 테스트 클라이언트
│   ├── test_voice_flow.sh        # 통합 테스트
│   └── test_voice_modes.sh       # 다양한 모드 테스트 (권장)
├── app/
│   ├── main.py                   # FastAPI 진입점
│   ├── roleplaying/
│   │   ├── ws_realtime.py        # WebSocket 핸들러
│   │   ├── services/
│   │   │   ├── stt_service.py    # Deepgram STT
│   │   │   ├── ai_tutor_service.py
│   │   │   └── ...
│   │   └── session_manager.py    # 세션 관리
│   └── ...
├── logs/
│   ├── server.log                # 서버 로그
│   └── test.log                  # 테스트 로그
└── TESTING.md                    # 이 파일
```

---

## ✨ 팁

### 성공적인 테스트를 위해

1. **더미 오디오로 시작**
   ```bash
   bash scripts/test_voice_modes.sh dummy
   ```

2. **텍스트 모드로 검증**
   ```bash
   bash scripts/test_voice_modes.sh text
   ```

3. **마이크로 단계적 진행**
   ```bash
   bash scripts/test_voice_modes.sh mic
   ```

4. **대화형 모드로 디버깅**
   ```bash
   bash scripts/test_voice_modes.sh interactive --mic
   ```

### 마이크 사용 팁

- **마이크 거리**: 10-15cm
- **음성 명확성**: 천천히, 명확하게
- **녹음 시간**: 최소 3초 이상
- **배경 소음**: 조용한 환경에서
- **예시 문장**: "The answer is in the logs"

---

**마지막 업데이트**: 2025-11-21
**버전**: 2.0.0 (test_voice_modes.sh 추가)
