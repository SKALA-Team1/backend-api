# 🎬 음성 기반 롤플레잉 시스템 - 실행 가이드

## 📂 사용 가능한 스크립트

### 1. 서버 시작
```bash
bash scripts/start_server.sh
```
- FastAPI 서버를 포트 8082에서 시작합니다
- 자동 리로드 활성화
- Ctrl+C로 종료

---

## 🎯 롤플레잉 테스트 방법

### 방법 1️⃣: 텍스트 기반 (권장 - 가장 안정적)

**마이크 필요 없음, STT 없음, 100% 안정적**

```bash
# 기본 실행 (1회)
bash scripts/roleplay_text.sh

# 3회 반복 테스트
bash scripts/roleplay_text.sh --iterations 3

# 상세 로깅 활성화
bash scripts/roleplay_text.sh --verbose

# 서버만 시작 (다른 터미널에서 테스트)
bash scripts/roleplay_text.sh --server-only
```

**테스트 흐름:**
1. 세션 생성 (REST API)
2. WebSocket 연결
3. INIT 메시지 → AI 첫 질문
4. 텍스트 메시지 전송 (3턴)
5. AI 응답 수신
6. 세션 종료

---

### 방법 2️⃣: 음성 기반 (마이크 필요)

**실제 마이크 음성으로 테스트, STT 포함**

```bash
# 기본 실행 (10초 녹음)
bash scripts/roleplay_voice.sh

# 더 짧은 녹음 (5초)
bash scripts/roleplay_voice.sh --record-duration 5

# 더 긴 녹음 (15초)
bash scripts/roleplay_voice.sh --record-duration 15

# 3회 반복 테스트
bash scripts/roleplay_voice.sh --iterations 3 --record-duration 10

# 상세 로깅
bash scripts/roleplay_voice.sh --verbose

# 서버만 시작
bash scripts/roleplay_voice.sh --server-only
```

**테스트 흐름:**
1. 서버 시작
2. 세션 생성 (REST API)
3. WebSocket 연결
4. INIT 메시지 → AI 첫 질문
5. 마이크 녹음 (지정된 시간)
6. 오디오 청크 전송
7. UTTERANCE_END 메시지
8. Deepgram STT 변환
9. AI 응답 생성 및 수신
10. 세션 종료

---

## 🚀 빠른 시작 (터미널 2개 필요)

### 터미널 1: 서버 시작
```bash
bash scripts/start_server.sh
```

### 터미널 2: 테스트 선택

#### 옵션 1️⃣: 자동 텍스트 테스트 (권장, 가장 빠름)
```bash
bash scripts/roleplay_text.sh
```
- 자동 3턴 대화
- 완료까지 ~10초

#### 옵션 2️⃣: 실시간 대화형 입력 (권장, 가장 유연함)
```bash
bash scripts/roleplay_interactive.sh
```
- 터미널에서 직접 텍스트 입력
- 'quit' 또는 'exit'로 종료
- 무제한 턴 수

#### 옵션 3️⃣: 음성 기반 테스트 (마이크 필요)
```bash
bash scripts/roleplay_voice.sh
```
- 실제 마이크 녹음 (10초)
- Deepgram STT 포함

---

## 📊 마이크 버튼 역할 (자동화)

음성 테스트에서 실제 UI의 마이크 버튼 동작이 자동화됩니다:

| UI 동작 | 자동화 구현 |
|--------|-----------|
| 마이크 버튼 누름 | `INIT` 메시지 전송 |
| 마이크 대고 말하기 | 오디오 청크 전송 (100ms씩) |
| 마이크 버튼 떼기 | `UTTERANCE_END` 메시지 |
| (자동) STT 변환 | Deepgram 호출 |
| (자동) AI 응답 | AI 튜터 호출 |

---

## ⚠️ 음성 테스트 문제 해결

### 문제: "Silence detected" 에러

**해결책:**

1. **먼저 텍스트 모드로 테스트**
   ```bash
   bash scripts/roleplay_text.sh
   ```
   이 명령이 성공하면 시스템은 정상입니다.

2. **마이크 설정 확인 (macOS)**
   - System Settings → Sound → Input
   - 올바른 마이크가 선택되어 있는지 확인

3. **마이크 권한 확인 (macOS)**
   - System Settings → Privacy & Security → Microphone
   - Terminal이 마이크 접근 권한을 가지고 있는지 확인

4. **더 긴 녹음 시간 사용**
   ```bash
   bash scripts/roleplay_voice.sh --record-duration 15
   ```

5. **마이크 테스트**
   ```bash
   # 간단한 음성 확인
   ffmpeg -f avfoundation -i ":0" -t 3 test.wav
   ```

---

## 📋 옵션 설명

### roleplay_text.sh (자동 3턴 대화)
```bash
--iterations N       # 반복 횟수 (기본값: 1)
--verbose           # 상세 로깅 활성화
--server-only       # 서버만 시작
```

### roleplay_interactive.sh (실시간 사용자 입력)
```bash
--verbose           # 상세 로깅 활성화
--server-only       # 서버만 시작
```
**사용법:**
- 터미널에서 메시지 입력
- 'quit' 또는 'exit' 입력하면 종료
- 무제한 턴 수 가능

### roleplay_voice.sh (음성 기반)
```bash
--record-duration N # 녹음 시간 (초, 기본값: 10)
--iterations N      # 반복 횟수 (기본값: 1)
--verbose          # 상세 로깅 활성화
--server-only      # 서버만 시작
```

---

## 📝 로그 확인

### 서버 로그 (실시간)
```bash
tail -f logs/server.log
```

### 최근 로그
```bash
cat logs/server.log | tail -50
```

---

## 🔄 전체 테스트 프로세스

### 1단계: 서버 준비
```bash
# 터미널 1
bash scripts/start_server.sh
# "서버가 준비되었습니다" 메시지 확인
```

### 2단계: 텍스트 테스트 (권장)
```bash
# 터미널 2
bash scripts/roleplay_text.sh
# 3턴 대화 완료 후 "모든 테스트를 통과했습니다!" 메시지 확인
```

### 3단계: 음성 테스트 (선택사항)
```bash
# 터미널 2 (새 터미널 또는 Step 2 후)
bash scripts/roleplay_voice.sh
# 마이크 준비 → 녹음 → 테스트 완료
```

---

## 💡 팁

### 개발 중 자동 리로드 활성화
```bash
# 터미널 1: 자동으로 리로드됨
bash scripts/start_server.sh
```

### 포트 8082 사용 확인
```bash
lsof -i :8082
```

### 기존 프로세스 종료
```bash
lsof -i :8082 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

---

## 📚 추가 정보

자세한 테스트 가이드는 `TESTING.md` 파일을 참고하세요.

---

**최종 업데이트**: 2025-11-21
**버전**: 1.0.0