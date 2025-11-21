# Spring 2 UUID 세션 ID 마이그레이션 가이드

## 📋 개요

Spring 1에서 발급한 UUID 세션 ID를 받아 저장하도록 Spring 2를 수정합니다.

**변경 이유:**
- Spring 1이 세션 생성 주도권 보유
- UUID를 단일 식별자로 사용 (숫자 ID 매핑 불필요)
- 시스템 간 일관성 확보

---

## 🎯 핵심 변경사항

### 기존 설계 (제거)
```
Spring 2: AUTO_INCREMENT session_id (BIGINT) 생성
```

### 새 설계 (적용)
```
Spring 1: UUID session_id 생성
    ↓
Spring 2: UUID 그대로 저장 (VARCHAR(36))
```

---

## 🔧 구현 가이드

### 1. Entity 수정

#### Session Entity
```java
@Entity
@Table(name = "sessions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Session {

    @Id
    @Column(name = "session_id", length = 36)
    private String sessionId;  // ⭐ Long → String (UUID)

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "scenario_id", nullable = false)
    private Integer scenarioId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status")
    private Status status;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @Column(name = "end_reason", length = 50)
    private String endReason;

    public enum Status {
        ACTIVE, FINISHED, ERROR
    }
}
```

**변경 포인트:**
- `@Id`: `@GeneratedValue` 제거 (외부에서 UUID 받음)
- 타입: `Long` → `String`
- 길이: `length = 36` 지정

---

#### Utterance Entity
```java
@Entity
@Table(name = "utterances")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Utterance {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", nullable = false, length = 36)
    private String sessionId;  // ⭐ Long → String (UUID 참조)

    @Column(name = "utterance_index", nullable = false)
    private Integer utteranceIndex;

    @Enumerated(EnumType.STRING)
    @Column(name = "speaker", nullable = false)
    private Speaker speaker;

    @Column(name = "text", nullable = false, columnDefinition = "TEXT")
    private String text;

    @Column(name = "s3_url", length = 512)
    private String s3Url;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "ended_at")
    private LocalDateTime endedAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public enum Speaker {
        USER, AI
    }
}
```

---

### 2. Repository 수정

```java
@Repository
public interface SessionRepository extends JpaRepository<Session, String> {  // ⭐ Long → String
    // 기본 CRUD는 JpaRepository가 제공
}

@Repository
public interface UtteranceRepository extends JpaRepository<Utterance, Long> {

    // ⭐ 모든 sessionId 파라미터를 String으로 변경
    List<Utterance> findBySessionIdOrderByUtteranceIndexAsc(String sessionId);

    Integer countBySessionId(String sessionId);

    Optional<Utterance> findBySessionIdAndUtteranceIndex(
        String sessionId,
        Integer utteranceIndex
    );
}
```

---

### 3. DTO 수정

#### SessionCreateRequest (수정)
```java
@Data
public class SessionCreateRequest {

    @NotBlank
    private String sessionId;  // ⭐ 추가: Spring 1에서 받은 UUID

    @NotNull
    private Long userId;

    @NotNull
    private Integer scenarioId;
}
```

#### SessionCreateResponse (단순화)
```java
@Data
@Builder
public class SessionCreateResponse {
    private Boolean success;
    private String error;  // 실패 시만 사용

    // ⭐ session_id 반환 불필요 (Spring 1이 이미 알고 있음)
}
```

#### SessionGetResponse (신규 추가)
```java
@Data
@Builder
public class SessionGetResponse {
    private Boolean success;
    private Long userId;
    private Integer scenarioId;
    private String status;  // "ACTIVE", "FINISHED", "ERROR"
}
```

---

### 4. Controller 수정

#### 세션 생성 API (수정)
```java
@PostMapping
public ResponseEntity<SessionCreateResponse> createSession(
        @Valid @RequestBody SessionCreateRequest request
) {
    log.info("Create session: session_id={}, user={}, scenario={}",
        request.getSessionId(), request.getUserId(), request.getScenarioId());

    // 시나리오 검증
    Scenario scenario = scenarioRepository.findByIdAndUserId(
        request.getScenarioId(),
        request.getUserId()
    );

    if (scenario == null) {
        return ResponseEntity.badRequest()
            .body(SessionCreateResponse.builder()
                .success(false)
                .error("Invalid user_id or scenario_id")
                .build());
    }

    // ⭐ 세션 저장 (UUID 그대로)
    Session session = Session.builder()
        .sessionId(request.getSessionId())  // UUID
        .userId(request.getUserId())
        .scenarioId(request.getScenarioId())
        .status(Session.Status.ACTIVE)
        .startedAt(LocalDateTime.now())
        .build();

    sessionRepository.save(session);

    return ResponseEntity.status(HttpStatus.CREATED)
        .body(SessionCreateResponse.builder()
            .success(true)
            .build());
}
```

---

#### 세션 조회 API (신규 추가)
```java
@GetMapping("/{sessionId}")
public ResponseEntity<SessionGetResponse> getSession(
        @PathVariable String sessionId  // ⭐ UUID
) {
    log.info("Get session: session_id={}", sessionId);

    Session session = sessionRepository.findById(sessionId)
        .orElseThrow(() -> new SessionNotFoundException(sessionId));

    return ResponseEntity.ok(
        SessionGetResponse.builder()
            .success(true)
            .userId(session.getUserId())
            .scenarioId(session.getScenarioId())
            .status(session.getStatus().name())
            .build()
    );
}
```

**용도:** FastAPI가 세션 확인 시 호출 (Redis 캐시 미스)

---

#### 발화 저장 API (파라미터 타입 변경)
```java
@PostMapping("/{sessionId}/utterances")
public ResponseEntity<UtteranceCreateResponse> saveUtterance(
        @PathVariable String sessionId,  // ⭐ Long → String
        @RequestPart(required = false) MultipartFile audio,
        @Valid @ModelAttribute UtteranceCreateRequest request
) {
    log.info("Save utterance: session={}, speaker={}, index={}, hasAudio={}",
        sessionId, request.getSpeaker(), request.getUtteranceIndex(), audio != null);

    UtteranceCreateResponse response = utteranceService.saveUtterance(
        sessionId,
        audio,
        request
    );

    return ResponseEntity.ok(response);
}
```

---

#### 세션 완료 API (파라미터 타입 변경)
```java
@PostMapping("/{sessionId}/complete")
public ResponseEntity<SessionCompleteResponse> completeSession(
        @PathVariable String sessionId,  // ⭐ Long → String
        @Valid @RequestBody SessionCompleteRequest request
) {
    log.info("Complete session: session={}, status={}, reason={}",
        sessionId, request.getStatus(), request.getReason());

    SessionCompleteResponse response = sessionService.completeSession(
        sessionId,
        request
    );

    return ResponseEntity.ok(response);
}
```

---

#### 대화 내용 조회 API (파라미터 타입 변경)
```java
@GetMapping("/{sessionId}/utterances")
public ResponseEntity<SessionUtterancesResponse> getUtterances(
        @PathVariable String sessionId  // ⭐ Long → String
) {
    log.info("Get utterances: session={}", sessionId);

    SessionUtterancesResponse response = utteranceService.getUtterances(sessionId);

    return ResponseEntity.ok(response);
}
```

---

### 5. Service 수정

#### SessionService
```java
@Service
@Slf4j
public class SessionService {

    @Autowired
    private SessionRepository sessionRepository;

    @Autowired
    private UtteranceRepository utteranceRepository;

    @Transactional
    public SessionCompleteResponse completeSession(
            String sessionId,  // ⭐ Long → String
            SessionCompleteRequest request
    ) {
        // 세션 조회
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new SessionNotFoundException(sessionId));

        // 세션 상태 업데이트
        LocalDateTime endedAt = LocalDateTime.now();
        session.setStatus(Session.Status.valueOf(request.getStatus()));
        session.setEndedAt(endedAt);
        session.setEndReason(request.getReason());

        sessionRepository.save(session);

        // 발화 수 조회
        Integer totalUtterances = utteranceRepository.countBySessionId(sessionId);

        log.info("Session completed: session={}, status={}, reason={}, utterances={}",
            sessionId, request.getStatus(), request.getReason(), totalUtterances);

        return SessionCompleteResponse.builder()
            .success(true)
            .sessionId(sessionId)  // ⭐ 이미 String이므로 변환 불필요
            .endedAt(endedAt)
            .totalUtterances(totalUtterances)
            .build();
    }
}
```

---

#### UtteranceService
```java
@Service
@Slf4j
public class UtteranceService {

    @Autowired
    private UtteranceRepository utteranceRepository;

    @Autowired
    private S3Service s3Service;

    @Autowired
    private SessionRepository sessionRepository;

    @Transactional
    public UtteranceCreateResponse saveUtterance(
            String sessionId,  // ⭐ Long → String
            MultipartFile audio,
            UtteranceCreateRequest request
    ) {
        // 1. 세션 존재 확인
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new SessionNotFoundException(sessionId));

        // 2. S3 업로드 (사용자 오디오가 있을 경우만)
        String s3Url = null;
        if (audio != null && !audio.isEmpty()) {
            if (!"user".equalsIgnoreCase(request.getSpeaker())) {
                throw new IllegalArgumentException("Audio is only allowed for user speaker");
            }

            String s3Key = String.format(
                "sessions/%s/utterance_%d.wav",
                sessionId,
                request.getUtteranceIndex()
            );

            try {
                s3Url = s3Service.uploadFile(s3Key, audio);
                log.info("Audio uploaded: s3Url={}, size={}", s3Url, audio.getSize());
            } catch (Exception e) {
                log.error("S3 upload failed: {}", e.getMessage(), e);
                throw new S3UploadException("Failed to upload audio", e);
            }
        }

        // 3. DB 저장
        Utterance utterance = Utterance.builder()
            .sessionId(sessionId)
            .utteranceIndex(request.getUtteranceIndex())
            .speaker(request.getSpeakerEnum())
            .text(request.getText())
            .s3Url(s3Url)
            .startedAt(request.getStartedAt())
            .endedAt(request.getEndedAt())
            .createdAt(LocalDateTime.now())
            .build();

        utterance = utteranceRepository.save(utterance);

        log.info("Utterance saved: id={}, speaker={}, index={}",
            utterance.getId(), utterance.getSpeaker(), utterance.getUtteranceIndex());

        // 4. 응답 반환
        return UtteranceCreateResponse.builder()
            .success(true)
            .utteranceId(utterance.getId())
            .s3Url(s3Url)
            .build();
    }

    @Transactional(readOnly = true)
    public SessionUtterancesResponse getUtterances(String sessionId) {  // ⭐ Long → String
        // 세션 확인
        Session session = sessionRepository.findById(sessionId)
            .orElseThrow(() -> new SessionNotFoundException(sessionId));

        // 발화 목록 조회 (utterance_index 순서대로)
        List<Utterance> utterances = utteranceRepository
            .findBySessionIdOrderByUtteranceIndexAsc(sessionId);

        List<UtteranceDto> utteranceDtos = utterances.stream()
            .map(this::toDto)
            .collect(Collectors.toList());

        return SessionUtterancesResponse.builder()
            .sessionId(sessionId)  // ⭐ 이미 String이므로 변환 불필요
            .status(session.getStatus().name())
            .utterances(utteranceDtos)
            .build();
    }

    private UtteranceDto toDto(Utterance utterance) {
        return UtteranceDto.builder()
            .id(utterance.getId())
            .utteranceIndex(utterance.getUtteranceIndex())
            .speaker(utterance.getSpeaker().name().toLowerCase())
            .text(utterance.getText())
            .s3Url(utterance.getS3Url())
            .startedAt(utterance.getStartedAt())
            .endedAt(utterance.getEndedAt())
            .createdAt(utterance.getCreatedAt())
            .build();
    }
}
```

---

## 🗄️ 데이터베이스 마이그레이션

### 새 테이블 생성 (처음 구현 시)
```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id BIGINT NOT NULL,
    scenario_id INT NOT NULL,
    status ENUM('ACTIVE', 'FINISHED', 'ERROR') DEFAULT 'ACTIVE',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    end_reason VARCHAR(50) NULL,

    INDEX idx_user_id (user_id),
    INDEX idx_scenario_id (scenario_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
);

CREATE TABLE utterances (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    utterance_index INT NOT NULL,
    speaker ENUM('user', 'ai') NOT NULL,
    text TEXT NOT NULL,
    s3_url VARCHAR(512),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_session_speaker (session_id, speaker),
    INDEX idx_created_at (created_at),
    UNIQUE KEY uk_session_utterance (session_id, utterance_index)
);
```

### 기존 테이블 수정 (마이그레이션 필요 시)
```sql
-- ⚠️ 주의: 기존 데이터가 있다면 백업 필수

-- sessions 테이블 수정
ALTER TABLE sessions MODIFY COLUMN session_id VARCHAR(36);

-- utterances 테이블 수정
ALTER TABLE utterances MODIFY COLUMN session_id VARCHAR(36);
```

---

## 📝 API 명세 요약

### 변경된 API

| API | Path | 변경 사항 |
|-----|------|----------|
| 세션 생성 | `POST /internal/sessions` | Request에 `session_id` 필드 추가 |
| 세션 조회 | `GET /internal/sessions/{sessionId}` | ⭐ **신규 추가** |
| 발화 저장 | `POST /internal/sessions/{sessionId}/utterances` | PathVariable 타입 변경 |
| 세션 완료 | `POST /internal/sessions/{sessionId}/complete` | PathVariable 타입 변경 |
| 대화 조회 | `GET /internal/sessions/{sessionId}/utterances` | PathVariable 타입 변경 |

---

### 세션 생성 API 변경

**요청 (Before):**
```json
{
  "user_id": 1,
  "scenario_id": 31
}
```

**요청 (After):**
```json
{
  "session_id": "abc-123-def-456",  // ⭐ 추가
  "user_id": 1,
  "scenario_id": 31
}
```

**응답 (Before):**
```json
{
  "success": true,
  "session_id": 123
}
```

**응답 (After):**
```json
{
  "success": true
}
```

---

### 세션 조회 API (신규)

**요청:**
```http
GET /internal/sessions/abc-123-def-456
```

**응답:**
```json
{
  "success": true,
  "user_id": 1,
  "scenario_id": 31,
  "status": "ACTIVE"
}
```

**실패 (404):**
```json
{
  "success": false,
  "error": "Session not found"
}
```

---

## ✅ 구현 체크리스트

### Entity
- [ ] `Session.sessionId`: `String` (VARCHAR(36))로 변경
- [ ] `Session.@Id`: `@GeneratedValue` 제거
- [ ] `Utterance.sessionId`: `String` (VARCHAR(36))로 변경

### Repository
- [ ] `SessionRepository`: `JpaRepository<Session, String>` 타입 파라미터 변경
- [ ] `UtteranceRepository` 메서드: 모든 `sessionId` 파라미터를 `String`으로 변경

### DTO
- [ ] `SessionCreateRequest`: `String sessionId` 필드 추가
- [ ] `SessionCreateResponse`: `session_id` 반환 필드 제거
- [ ] `SessionGetResponse`: 새 DTO 클래스 추가

### Controller
- [ ] `createSession()`: Request DTO 변경 적용
- [ ] `getSession()`: 새 메서드 추가 (`GET /{sessionId}`)
- [ ] `saveUtterance()`: `@PathVariable String sessionId`
- [ ] `completeSession()`: `@PathVariable String sessionId`
- [ ] `getUtterances()`: `@PathVariable String sessionId`

### Service
- [ ] `SessionService.completeSession()`: `String sessionId` 파라미터
- [ ] `UtteranceService.saveUtterance()`: `String sessionId` 파라미터
- [ ] `UtteranceService.getUtterances()`: `String sessionId` 파라미터
- [ ] 응답 생성 시 `String.valueOf()` 제거 (이미 String)

### 데이터베이스
- [ ] `sessions` 테이블: `session_id VARCHAR(36)` 생성 또는 수정
- [ ] `utterances` 테이블: `session_id VARCHAR(36)` 생성 또는 수정

### 테스트
- [ ] 세션 생성 API 테스트 (UUID 전달)
- [ ] 세션 조회 API 테스트 (신규)
- [ ] 발화 저장 API 테스트 (UUID 사용)
- [ ] 세션 완료 API 테스트 (UUID 사용)

---

## 🚀 마이그레이션 순서

1. **데이터베이스 백업** (기존 데이터가 있을 경우)
2. **Entity 변경**: `Session`, `Utterance`
3. **Repository 변경**: 타입 파라미터 및 메서드 시그니처
4. **DTO 변경**: Request/Response 수정
5. **Service 변경**: 메서드 시그니처 및 로직
6. **Controller 변경**: PathVariable 타입 및 새 메서드 추가
7. **데이터베이스 스키마 적용**
8. **통합 테스트 실행**

---

**작성자:** Claude Code
**최종 수정일:** 2025-11-18
**문서 위치:** `/docs/spring2_uuid_migration_guide.md`