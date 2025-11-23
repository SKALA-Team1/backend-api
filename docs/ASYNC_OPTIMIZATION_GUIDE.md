# 음성 롤플레이 비동기 최적화 가이드

## 개요

백엔드에서 STT(음성 인식) + AI 응답 생성을 병렬로 처리하도록 개선했습니다.
**클라이언트(Spring 1)도 오디오 전송과 응답 수신을 비동기로 처리해야 최대 성능을 발휘합니다.**

---

## 문제점: 순차 처리 (기존)

```
1. 오디오 전체 녹음
   ↓
2. 오디오 전체 전송 (완료 대기)
   ↓ (여기서 10초 이상 대기)
3. UTTERANCE_END 전송
   ↓
4. STT 시작 (서버)
   ↓
5. AI 응답 생성 (서버)
   ↓
6. 응답 수신

[총 시간] = 오디오 녹음 시간 + 오디오 전송 시간 + STT 시간 + AI 시간
```

**결과**: 사용자가 10-20초 기다림

---

## 해결책: 비동기 병렬 처리

```
1. 오디오 녹음 시작
   ↓
2. 오디오 청크 전송 시작 (비동기, 전체 완료 기다리지 않음)
   ↓ (동시에)
3. 응답 수신 대기 시작
   ↓
4. 클라이언트: 오디오 계속 전송 중...
   서버: STT 진행 중...
   ↓
5. STT 완료 → 즉시 응답 수신 시작
   ↓
6. 응답 수신 (오디오 전송은 백그라운드에서 계속)
   ↓
7. AI 응답 표시

[총 시간] = 오디오 녹음 시간 + MAX(오디오 전송 시간, STT 시간 + AI 시간)
```

**결과**: 사용자가 3-5초만 기다림 (훨씬 빠름!)

---

## 서버 구현 (이미 완료됨)

### 변경 내용

**파일**: `app/roleplaying/ws_realtime.py` → `_handle_utterance_end()` 함수

**핵심**:
```python
# UTTERANCE_END 받으면 즉시 STT를 백그라운드에서 시작
stt_task = asyncio.create_task(process_stt_and_history(audio_data))

# STT 완료 대기
stt_text = await stt_task

# STT 결과를 클라이언트에 즉시 전송
await websocket.send_json(SttFinalMessage(text=stt_text).model_dump())

# AI 응답 생성 (Spring 2 저장은 백그라운드)
ai_response = await ai_tutor_service.generate_reply(session_state, stt_text)

# AI 응답 전송
await websocket.send_json(AiTextMessage(text=ai_response).model_dump())
```

---

## 클라이언트 구현 (Spring 1에서 해야 할 작업)

### 요구사항

1. **오디오를 전체 완료 후 전송하지 말 것**
   - 청크 단위로 즉시 전송 (100ms = 1600 bytes)
   - 모든 청크 전송 완료를 기다리지 말 것

2. **응답 수신은 별도 스레드/비동기로 처리**
   - 오디오 전송과 동시에 응답 수신 대기

3. **UTTERANCE_END를 조기에 보낼 것**
   - 모든 오디오 전송 완료 후가 아니라
   - 일부 청크(예: 50%) 전송 후 즉시 전송

---

## Spring 1 구현 방법

### 패턴 1: CompletableFuture (권장)

```java
// 오디오 녹음
byte[] audioData = recordAudio(); // 16kHz, PCM 16-bit

// 청크 크기 (100ms = 1600 bytes @ 16kHz)
int chunkSize = SAMPLE_RATE / 10; // 16000 / 10 = 1600

// 1. 오디오 전송 (비동기 시작)
CompletableFuture<Void> sendTask = CompletableFuture.runAsync(() -> {
    int sent = 0;
    for (int i = 0; i < audioData.length; i += chunkSize) {
        int end = Math.min(i + chunkSize, audioData.length);
        byte[] chunk = Arrays.copyOfRange(audioData, i, end);

        // WebSocket으로 오디오 청크 전송
        websocket.sendBinary(chunk);
        sent++;

        // 네트워크 대역폭 고려 (10ms 대기)
        Thread.sleep(10);

        // 절반 정도 전송되면 UTTERANCE_END 전송 (조기)
        if (sent == audioData.length / chunkSize / 2) {
            websocket.sendText(new ObjectMapper().writeValueAsString(
                Map.of("type", "UTTERANCE_END")
            ));
        }
    }
    // 남은 청크 전송
});

// 2. 응답 수신 (메인 스레드에서 대기)
while (true) {
    String response = websocket.receiveText();
    JsonNode msg = new ObjectMapper().readTree(response);
    String type = msg.get("type").asText();

    if ("STT_FINAL".equals(type)) {
        String userText = msg.get("text").asText();
        System.out.println("You: " + userText);
    } else if ("AI_TEXT".equals(type)) {
        String aiText = msg.get("text").asText();
        System.out.println("AI: " + aiText);
        break; // 다음 턴으로
    }
}

// 3. 오디오 전송이 아직 진행 중이면 백그라운드에서 완료될 때까지 기다림
// (메인 스레드는 이미 응답을 받았으므로 사용자는 기다리지 않음)
sendTask.join();
```

### 패턴 2: Thread (더 간단함)

```java
byte[] audioData = recordAudio();
int chunkSize = 1600;

// 1. 오디오 전송 스레드 시작
Thread sendThread = new Thread(() -> {
    int sent = 0;
    for (int i = 0; i < audioData.length; i += chunkSize) {
        int end = Math.min(i + chunkSize, audioData.length);
        byte[] chunk = Arrays.copyOfRange(audioData, i, end);
        websocket.sendBinary(chunk);
        sent++;

        try {
            Thread.sleep(10);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // 절반 정도 전송되면 UTTERANCE_END
        if (sent == audioData.length / chunkSize / 2) {
            sendUtteranceEnd();
        }
    }
});
sendThread.start();

// 2. 메인 스레드에서 응답 수신 (블로킹)
String sttResult = null;
String aiResponse = null;

while (true) {
    String response = websocket.receiveText();
    JsonNode msg = new ObjectMapper().readTree(response);
    String type = msg.get("type").asText();

    if ("STT_FINAL".equals(type)) {
        sttResult = msg.get("text").asText();
        System.out.println("You: " + sttResult);
    } else if ("AI_TEXT".equals(type)) {
        aiResponse = msg.get("text").asText();
        System.out.println("AI: " + aiResponse);
        break;
    }
}

// 3. 오디오 전송 스레드 완료 대기 (사용자는 이미 응답을 봤으므로 괜찮음)
sendThread.join();
```

### 패턴 3: Reactive/RxJava (Spring WebClient)

```java
// 응답 수신 (Flux)
Flux<String> responses = websocket.receive()
    .asString()
    .share();

Mono<String> sttResult = responses
    .filter(msg -> msg.contains("\"type\":\"STT_FINAL\""))
    .map(msg -> JsonUtil.extract(msg, "text"))
    .next();

Mono<String> aiResponse = responses
    .filter(msg -> msg.contains("\"type\":\"AI_TEXT\""))
    .map(msg -> JsonUtil.extract(msg, "text"))
    .next();

// 오디오 전송 (비동기)
Mono<Void> sendAudio = Mono.fromRunnable(() -> {
    int sent = 0;
    for (int i = 0; i < audioData.length; i += chunkSize) {
        // 청크 전송
        int end = Math.min(i + chunkSize, audioData.length);
        byte[] chunk = Arrays.copyOfRange(audioData, i, end);
        websocket.sendBinary(Mono.just(chunk)).subscribe();
        sent++;

        // 절반 정도 전송 후 UTTERANCE_END
        if (sent == audioData.length / chunkSize / 2) {
            websocket.sendText(Mono.just(utteranceEndMsg)).subscribe();
        }
    }
});

// 병렬 실행: 오디오 전송 + 응답 수신
Mono.zip(sendAudio, sttResult, aiResponse)
    .subscribe(tuple -> {
        String stt = tuple.getT2();
        String ai = tuple.getT3();
        System.out.println("You: " + stt);
        System.out.println("AI: " + ai);
    });
```

---

## 타이밍 다이어그램

### 기존 (순차 처리)

```
클라이언트                           서버
|                                  |
| 오디오 녹음 (5초)                   |
|------- 5초 경과 --------|
|                                  |
| 오디오 전송 (10초)                  |
|------- 15초 경과 --------|
|                          UTTERANCE_END 수신
|                                  |
|                          STT 시작 (3초)
|------- 18초 경과 --------|
|                          AI 생성 (2초)
|------- 20초 경과 --------|
| ←── AI_TEXT 수신
|
[사용자가 20초 기다림]
```

### 개선 (비동기 병렬)

```
클라이언트                           서버
|                                  |
| 오디오 녹음 (5초)                   |
|------- 5초 경과 --------|
|                                  |
| 청크1 전송 (0.1초)                 |
| 청크2 전송 (0.1초)                 |
| ...                              |
| 청크5 전송 후 → UTTERANCE_END 전송 (0.5초)
|------- 5.5초 경과 --------|       UTTERANCE_END 수신
|                          STT 시작 (3초)
| 청크6 전송...                     |
| (백그라운드)                       |
|------- 8.5초 경과 --------|       AI 생성 시작
|                          AI 생성 (2초)
|------- 10.5초 경과 --------|
| ←── AI_TEXT 수신
|
[사용자가 10초만 기다림 (절반 이상 단축!)]
```

---

## 체크리스트

Spring 1 개발자가 구현할 때 확인할 사항:

- [ ] 오디오를 **청크 단위** (100ms)로 분할
- [ ] 각 청크를 **즉시 전송** (완료 기다리지 않음)
- [ ] 오디오 전송을 **별도 스레드/비동기**에서 실행
- [ ] 응답 수신을 **메인 스레드/별도 흐름**에서 대기
- [ ] UTTERANCE_END를 **절반 정도 전송 후** 보냄
- [ ] STT_FINAL 메시지를 받으면 사용자 텍스트 표시
- [ ] AI_TEXT 메시지를 받으면 AI 응답 표시
- [ ] 오디오 전송 완료 전에 다음 턴으로 진행 가능

---

## 메시지 포맷 참고

### UTTERANCE_END
```json
{
  "type": "UTTERANCE_END"
}
```

### STT_FINAL (서버 → 클라이언트)
```json
{
  "type": "STT_FINAL",
  "text": "사용자가 말한 내용"
}
```

### AI_TEXT (서버 → 클라이언트)
```json
{
  "type": "AI_TEXT",
  "text": "AI가 생성한 응답",
  "is_fixed_question": false
}
```

### AI_TYPING (선택사항, UI 로딩 표시)
```json
{
  "type": "AI_TYPING"
}
```

---