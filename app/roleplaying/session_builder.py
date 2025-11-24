"""
세션 생성 빌더 패턴
===============================================

역할:
- 세션 생성 요청 객체화
- Builder 패턴으로 파라미터 축소
- 유효성 검증
# Spring 2 Backend Modification Guide
## scenario_session 테이블 턴 정보 업데이트

---

## 📋 개요

FastAPI에서 `scenario_session` 테이블의 턴 정보를 업데이트할 수 있도록 **두 가지 API 엔드포인트**를 수정해야 합니다:
1. **POST /internal/sessions/{sessionId}/utterances** - 발화 저장 시 턴 정보 업데이트
2. **POST /internal/sessions/{sessionId}/complete** - 세션 완료 시 최종 턴 정보 업데이트

---

## 🔧 수정 사항

### 1️⃣ SaveUtteranceRequest DTO 확장

**파일:** `src/main/java/com/skala/api/dto/request/SaveUtteranceRequest.java`

**현재 상태:**
```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SaveUtteranceRequest {
    private String speaker;              // "user" 또는 "ai"
    private String text;                 // 발화 텍스트
    private Integer utteranceIndex;      // 발화 인덱스
    private String audio;                // Base64 인코딩된 오디오
    private LocalDateTime startedAt;     // 발화 시작 시각
    private LocalDateTime endedAt;       // 발화 종료 시각
}
```

**수정 후:**
```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SaveUtteranceRequest {
    private String speaker;              // "user" 또는 "ai"
    private String text;                 // 발화 텍스트
    private Integer utteranceIndex;      // 발화 인덱스
    private String audio;                // Base64 인코딩된 오디오
    private LocalDateTime startedAt;     // 발화 시작 시각
    private LocalDateTime endedAt;       // 발화 종료 시각

    // ✅ 새로운 필드들 (scenario_session 업데이트용)
    @JsonProperty("played_turns")
    private Integer playedTurns;         // AI가 한 질문의 총 개수

    @JsonProperty("completed_all_turns")
    private Boolean completedAllTurns;   // 모든 턴(10개)을 완료했는지 여부

    @JsonProperty("finish_reason")
    private String finishReason;         // 세션 종료 사유 (turn_limit, user_end, timeout, error 등)

    private String status;               // 세션 상태 (IN_PROGRESS, FINISHED, ERROR)
}
```

**참고:**
- `@JsonProperty`를 사용하여 snake_case JSON 필드를 camelCase Java 필드로 매핑
- 모든 필드는 `Optional`이므로 기존 호출과의 호환성 유지

---

### 2️⃣ SaveUtteranceController 수정

**파일:** `src/main/java/com/skala/api/controller/SaveUtteranceController.java` (또는 유사 이름)

**현재 상태:**
```java
@PostMapping("/internal/sessions/{sessionId}/utterances")
public ResponseEntity<?> saveUtterance(
    @PathVariable String sessionId,
    @RequestBody SaveUtteranceRequest request
) {
    // 1. 오디오 S3 업로드
    // 2. Conversation_log 테이블에 저장
    // ❌ scenario_session 업데이트 없음

    return ResponseEntity.ok(response);
}
```

**수정 후:**
```java
@PostMapping("/internal/sessions/{sessionId}/utterances")
public ResponseEntity<?> saveUtterance(
    @PathVariable String sessionId,
    @RequestBody SaveUtteranceRequest request
) {
    try {
        // 1. 오디오 S3 업로드 (기존 로직)
        // ...

        // 2. Conversation_log 테이블에 저장 (기존 로직)
        // ...

        // ✅ 3. scenario_session 테이블 업데이트 (새로운 로직)
        if (request.getPlayedTurns() != null ||
            request.getCompletedAllTurns() != null ||
            request.getFinishReason() != null ||
            request.getStatus() != null) {

            ScenarioSession scenarioSession = scenarioSessionRepository
                .findById(sessionId)
                .orElse(null);

            if (scenarioSession != null) {
                // played_turns 업데이트
                if (request.getPlayedTurns() != null) {
                    scenarioSession.setPlayedTurns(request.getPlayedTurns());
                }

                // completed_all_turns 업데이트
                if (request.getCompletedAllTurns() != null) {
                    scenarioSession.setCompletedAllTurns(request.getCompletedAllTurns());
                }

                // finish_reason 업데이트
                if (request.getFinishReason() != null) {
                    scenarioSession.setFinishReason(request.getFinishReason());
                }

                // status 업데이트
                if (request.getStatus() != null) {
                    scenarioSession.setStatus(request.getStatus());
                }

                // 변경사항 저장
                scenarioSessionRepository.save(scenarioSession);

                logger.info("ScenarioSession updated: sessionId={}, playedTurns={}, completedAllTurns={}",
                    sessionId, request.getPlayedTurns(), request.getCompletedAllTurns());
            }
        }

        return ResponseEntity.ok(response);
    } catch (Exception e) {
        logger.error("Error saving utterance: {}", e.getMessage(), e);
        throw new RuntimeException("Failed to save utterance", e);
    }
}
```

---

### 3️⃣ CompleteSessionRequest DTO 확장

**파일:** `src/main/java/com/skala/api/dto/request/CompleteSessionRequest.java` (또는 유사 이름)

**현재 상태:**
```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompleteSessionRequest {
    private String status;     // "FINISHED", "ERROR" 등
    private String reason;     // "user_end", "timeout", "disconnected", "error" 등
}
```

**수정 후:**
```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompleteSessionRequest {
    private String status;     // "FINISHED", "ERROR" 등
    private String reason;     // "user_end", "timeout", "disconnected", "error" 등

    // ✅ 새로운 필드들 (scenario_session 최종 업데이트용)
    @JsonProperty("played_turns")
    private Integer playedTurns;         // AI가 한 질문의 총 개수

    @JsonProperty("completed_all_turns")
    private Boolean completedAllTurns;   // 모든 턴(10개)을 완료했는지 여부

    @JsonProperty("finish_reason")
    private String finishReason;         // 세션 종료 사유

    private LocalDateTime finishedAt;    // 세션 종료 시각
}
```

---

### 4️⃣ CompleteSessionController 수정

**파일:** `src/main/java/com/skala/api/controller/CompleteSessionController.java` (또는 유사 이름)

**현재 상태:**
```java
@PostMapping("/internal/sessions/{sessionId}/complete")
public ResponseEntity<?> completeSession(
    @PathVariable String sessionId,
    @RequestBody CompleteSessionRequest request
) {
    // 1. 세션 상태 업데이트
    // ❌ scenario_session 턴 정보 업데이트 없음

    return ResponseEntity.ok(response);
}
```

**수정 후:**
```java
@PostMapping("/internal/sessions/{sessionId}/complete")
public ResponseEntity<?> completeSession(
    @PathVariable String sessionId,
    @RequestBody CompleteSessionRequest request
) {
    try {
        // 1. 세션 상태 업데이트 (기존 로직)
        // ...

        // ✅ 2. scenario_session 테이블 최종 업데이트 (새로운 로직)
        ScenarioSession scenarioSession = scenarioSessionRepository
            .findById(sessionId)
            .orElse(null);

        if (scenarioSession != null) {
            // played_turns 업데이트
            if (request.getPlayedTurns() != null) {
                scenarioSession.setPlayedTurns(request.getPlayedTurns());
            }

            // completed_all_turns 업데이트
            if (request.getCompletedAllTurns() != null) {
                scenarioSession.setCompletedAllTurns(request.getCompletedAllTurns());
            }

            // finish_reason 업데이트
            if (request.getFinishReason() != null) {
                scenarioSession.setFinishReason(request.getFinishReason());
            }

            // status 업데이트 (request.getStatus() 또는 기존 로직)
            scenarioSession.setStatus(request.getStatus());

            // finished_at 업데이트
            if (request.getFinishedAt() != null) {
                scenarioSession.setFinishedAt(request.getFinishedAt());
            } else {
                scenarioSession.setFinishedAt(LocalDateTime.now());
            }

            // 변경사항 저장
            scenarioSessionRepository.save(scenarioSession);

            logger.info("ScenarioSession completed: sessionId={}, status={}, reason={}, playedTurns={}",
                sessionId, request.getStatus(), request.getReason(), request.getPlayedTurns());
        }

        return ResponseEntity.ok(response);
    } catch (Exception e) {
        logger.error("Error completing session: {}", e.getMessage(), e);
        throw new RuntimeException("Failed to complete session", e);
    }
}
```

---

### 5️⃣ ScenarioSession Entity 확인

**파일:** `src/main/java/com/skala/entity/ScenarioSession.java`

**필수 필드 확인:**

```java
@Entity
@Table(name = "scenario_session")
public class ScenarioSession {
    @Id
    private String id;

    // 기존 필드
    private Integer userId;
    private Integer scenarioId;
    private String status;         // 필요
    private LocalDateTime createdAt;

    // ✅ 다음 필드들이 존재하는지 확인
    private Integer playedTurns;         // ❓ 확인 필요
    private Boolean completedAllTurns;   // ❓ 확인 필요
    private String finishReason;         // ❓ 확인 필요
    private LocalDateTime finishedAt;    // ❓ 확인 필요
}
```

**만약 필드가 없다면 추가:**

```java
@Column(name = "played_turns", nullable = true)
private Integer playedTurns;

@Column(name = "completed_all_turns", nullable = true)
private Boolean completedAllTurns;

@Column(name = "finish_reason", length = 50, nullable = true)
private String finishReason;

@Column(name = "finished_at", nullable = true)
private LocalDateTime finishedAt;
```

---

### 6️⃣ 데이터베이스 마이그레이션 (필요시)

**파일:** `src/main/resources/db/migration/V*.sql` 또는 `schema.sql`

**필드가 없다면 추가:**

```sql
-- scenario_session 테이블에 컬럼 추가 (필요시)
ALTER TABLE scenario_session
ADD COLUMN played_turns INT NULL COMMENT 'AI가 한 질문의 총 개수',
ADD COLUMN completed_all_turns BOOLEAN DEFAULT FALSE COMMENT '모든 턴(10개)을 완료했는지 여부',
ADD COLUMN finish_reason VARCHAR(50) NULL COMMENT '세션 종료 사유',
ADD COLUMN finished_at DATETIME NULL COMMENT '세션 종료 시각';
```

---

## 🧪 테스트 케이스

### Test Case 1: 발화 저장 시 턴 정보 업데이트

```java
@Test
public void testSaveUtteranceWithTurnInfo() {
    // Given
    SaveUtteranceRequest request = new SaveUtteranceRequest();
    request.setSessionId("session-123");
    request.setSpeaker("user");
    request.setText("Hello");
    request.setUtteranceIndex(0);
    request.setPlayedTurns(1);                    // ✅ 새로운 필드
    request.setCompletedAllTurns(false);          // ✅ 새로운 필드
    request.setFinishReason(null);                // ✅ 새로운 필드
    request.setStatus("IN_PROGRESS");             // ✅ 새로운 필드

    // When
    ResponseEntity<?> response = controller.saveUtterance("session-123", request);

    // Then
    ScenarioSession session = scenarioSessionRepository.findById("session-123").get();
    assert session.getPlayedTurns() == 1;
    assert session.getStatus().equals("IN_PROGRESS");
}
```

### Test Case 2: 세션 완료 시 최종 턴 정보 업데이트

```java
@Test
public void testCompleteSessionWithTurnInfo() {
    // Given
    CompleteSessionRequest request = new CompleteSessionRequest();
    request.setStatus("FINISHED");
    request.setReason("turn_limit");
    request.setPlayedTurns(10);                   // ✅ 새로운 필드
    request.setCompletedAllTurns(true);           // ✅ 새로운 필드
    request.setFinishReason("turn_limit");        // ✅ 새로운 필드
    request.setFinishedAt(LocalDateTime.now());   // ✅ 새로운 필드

    // When
    ResponseEntity<?> response = controller.completeSession("session-123", request);

    // Then
    ScenarioSession session = scenarioSessionRepository.findById("session-123").get();
    assert session.getStatus().equals("FINISHED");
    assert session.getPlayedTurns() == 10;
    assert session.getCompletedAllTurns() == true;
    assert session.getFinishReason().equals("turn_limit");
    assert session.getFinishedAt() != null;
}
```

---

## 📊 API 요청/응답 예시

### 요청: POST /internal/sessions/session-123/utterances

```json
{
  "speaker": "ai",
  "text": "How was your day?",
  "utterance_index": 1,
  "audio": "SUQz...",  // Base64 인코딩된 오디오
  "started_at": "2025-11-24T10:30:00Z",
  "ended_at": "2025-11-24T10:32:00Z",
  "played_turns": 1,
  "completed_all_turns": false,
  "finish_reason": null,
  "status": "IN_PROGRESS"
}
```

### 요청: POST /internal/sessions/session-123/complete

```json
{
  "status": "FINISHED",
  "reason": "turn_limit",
  "played_turns": 10,
  "completed_all_turns": true,
  "finish_reason": "turn_limit",
  "finished_at": "2025-11-24T10:45:00Z"
}
```

---

## ✅ 체크리스트

Spring 2 수정을 완료하기 위해 다음을 확인하세요:

- [ ] `SaveUtteranceRequest` DTO에 4개 필드 추가
- [ ] `CompleteSessionRequest` DTO에 4개 필드 추가
- [ ] `SaveUtteranceController`에서 scenario_session 업데이트 로직 추가
- [ ] `CompleteSessionController`에서 scenario_session 최종 업데이트 로직 추가
- [ ] `ScenarioSession` Entity에 필드 존재 확인 (없으면 추가)
- [ ] 데이터베이스 마이그레이션 실행 (필드 추가)
- [ ] 단위 테스트 작성 및 실행
- [ ] 통합 테스트로 FastAPI ↔ Spring 2 통신 확인

---

## 🔗 관련 FastAPI 코드

**FastAPI에서 전송하는 시점:**

1. **사용자 발화 저장** (`ws_realtime.py:542-555`)
   - STT 결과를 Spring 2에 저장할 때
   - `played_turns`, `completed_all_turns`, `status` 전송

2. **AI 응답 저장** (`ws_realtime.py:583-592`)
   - AI 응답을 Spring 2에 저장할 때
   - `played_turns`, `completed_all_turns`, `status` 전송

3. **세션 종료** (`ws_realtime.py:658-666`)
   - 세션을 종료할 때
   - `played_turns`, `completed_all_turns`, `finish_reason`, `finished_at` 전송

---

## 📝 참고사항

- 모든 새로운 필드는 **Optional**이므로 기존 호출과의 호환성을 유지합니다
- `@JsonProperty`를 사용하여 snake_case JSON을 camelCase Java로 자동 변환합니다
- 필드 값이 `null`이면 기존 값을 유지하도록 구현했습니다
- `finished_at`은 명시적으로 제공되지 않으면 현재 시각으로 설정됩니다

---

**수정 완료 후 FastAPI와 함께 테스트하면 완벽한 턴 추적 시스템이 완성됩니다!** ✅
"""
logger = logging.getLogger(__name__)


class SessionCreationRequest:
    """세션 생성 요청"""

    def __init__(self):
        self.session_id: Optional[str] = None
        self.user_id: Optional[int] = None
        self.subject_id: Optional[int] = None
        self.my_role: Optional[str] = None
        self.ai_role: Optional[str] = None
        self.fixed_questions: List[str] = []
        self.expires_at: Optional[datetime] = None

    def with_session_id(self, session_id: str) -> "SessionCreationRequest":
        """세션 ID 설정"""
        self.session_id = session_id
        return self

    def with_user_id(self, user_id: int) -> "SessionCreationRequest":
        """사용자 ID 설정"""
        self.user_id = user_id
        return self

    def with_subject_id(self, subject_id: int) -> "SessionCreationRequest":
        """주제 ID 설정"""
        self.subject_id = subject_id
        return self

    def with_roles(self, my_role: str, ai_role: str) -> "SessionCreationRequest":
        """역할 설정"""
        self.my_role = my_role
        self.ai_role = ai_role
        return self

    def with_fixed_questions(self, questions: List[str]) -> "SessionCreationRequest":
        """고정 질문 설정 (반드시 3개)"""
        if len(questions) != 3:
            raise ValueError(f"Fixed questions must contain exactly 3 questions, got {len(questions)}")
        self.fixed_questions = questions
        return self

    def with_expiration(self, expires_at: Optional[datetime]) -> "SessionCreationRequest":
        """만료 시각 설정"""
        self.expires_at = expires_at
        return self

    def validate(self) -> None:
        """유효성 검증"""
        if not self.session_id:
            raise ValueError("session_id is required")
        if self.user_id is None:
            raise ValueError("user_id is required")
        if self.subject_id is None:
            raise ValueError("subject_id is required")
        if not self.my_role:
            raise ValueError("my_role is required")
        if not self.ai_role:
            raise ValueError("ai_role is required")
        if len(self.fixed_questions) != 3:
            raise ValueError("fixed_questions must contain exactly 3 questions")

    def build(self):
        """세션 생성"""
        self.validate()
        return session_manager.create_session(
            session_id=self.session_id,
            user_id=self.user_id,
            subject_id=self.subject_id,
            my_role=self.my_role,
            ai_role=self.ai_role,
            fixed_questions=self.fixed_questions,
            expires_at=self.expires_at,
        )


def create_session_builder() -> SessionCreationRequest:
    """빌더 팩토리"""
    return SessionCreationRequest()