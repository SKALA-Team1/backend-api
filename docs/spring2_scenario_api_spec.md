# Spring 2 - 시나리오 조회 API 구현 가이드

## 📌 개요

사용자가 생성된 시나리오 목록을 조회하고, 특정 시나리오의 상세 정보를 가져올 수 있는 API를 Spring 2에서 구현해야 합니다.

이 API는 클라이언트(프론트엔드, 모바일 앱)에서 호출되어, 사용자에게 롤플레잉 시나리오 선택 화면을 제공하는 데 사용됩니다.

---

## 🎯 사용 시나리오

1. **사용자가 앱을 열고 시나리오 목록 페이지로 이동**
   - Spring 2: `GET /api/v1/scenarios?userId=1&status=ready&page=0&size=10`
   - 응답: 사용자의 준비된 시나리오 목록 반환

2. **사용자가 특정 시나리오를 선택**
   - Spring 2: `GET /api/v1/scenarios/{scenarioId}?userId=1`
   - 응답: 시나리오 상세 정보 반환

3. **사용자가 "세션 시작" 버튼 클릭**
   - 클라이언트: FastAPI `POST /roleplaying/sessions` 호출
   - FastAPI: DB에서 시나리오 조회 + Redis 세션 생성
   - 응답: WebSocket URL 반환

---

## 📋 API 명세

### 1. 시나리오 목록 조회

**Endpoint:**
```
GET /api/v1/scenarios
```

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| `userId` | `int` | ✅ | 사용자 ID | - |
| `status` | `string` | ❌ | 시나리오 상태 필터 (`ready`, `in_progress`, `finished`, `creating`) | 전체 |
| `sourceType` | `string` | ❌ | 시나리오 소스 필터 (`slack`, `github`, `prompt`) | 전체 |
| `page` | `int` | ❌ | 페이지 번호 (0부터 시작) | 0 |
| `size` | `int` | ❌ | 페이지당 항목 수 | 10 |
| `sort` | `string` | ❌ | 정렬 기준 (`createdAt,desc` 또는 `updatedAt,desc`) | `createdAt,desc` |

**Response (200 OK):**

```json
{
  "content": [
    {
      "scenarioId": 500,
      "subjectId": 100,
      "title": "Daily Standup Discussion with Tech Lead",
      "status": "ready",
      "sourceType": "slack",
      "myRole": "Software Engineer",
      "aiRole": "Tech Lead",
      "topicType": "detail",
      "createdAt": "2025-11-16T10:00:00Z",
      "updatedAt": "2025-11-16T10:05:00Z"
    },
    {
      "scenarioId": 501,
      "subjectId": 101,
      "title": "Code Review with Senior Developer",
      "status": "ready",
      "sourceType": "github",
      "myRole": "Junior Developer",
      "aiRole": "Senior Developer",
      "topicType": "overview",
      "createdAt": "2025-11-15T14:30:00Z",
      "updatedAt": "2025-11-15T14:30:00Z"
    }
  ],
  "pageable": {
    "pageNumber": 0,
    "pageSize": 10,
    "sort": {
      "sorted": true,
      "unsorted": false,
      "empty": false
    },
    "offset": 0,
    "paged": true,
    "unpaged": false
  },
  "totalElements": 25,
  "totalPages": 3,
  "last": false,
  "size": 10,
  "number": 0,
  "sort": {
    "sorted": true,
    "unsorted": false,
    "empty": false
  },
  "numberOfElements": 10,
  "first": true,
  "empty": false
}
```

**Error Responses:**

- `400 Bad Request`: 유효하지 않은 파라미터
- `401 Unauthorized`: 인증 실패 (필요 시)
- `500 Internal Server Error`: 서버 오류

---

### 2. 시나리오 상세 조회

**Endpoint:**
```
GET /api/v1/scenarios/{scenarioId}
```

**Path Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `scenarioId` | `int` | ✅ | 시나리오 ID |

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `userId` | `int` | ✅ | 사용자 ID (권한 검증용) |

**Response (200 OK):**

```json
{
  "scenarioId": 500,
  "subjectId": 100,
  "title": "Daily Standup Discussion with Tech Lead",
  "status": "ready",
  "sourceType": "slack",
  "myRole": "Software Engineer",
  "aiRole": "Tech Lead",
  "topicType": "detail",
  "fixedQuestions": [
    "Can you introduce yourself and your current project?",
    "What technical challenges are you facing?",
    "What are your next steps?"
  ],
  "conversationDate": "2025-11-15",
  "messageCount": 42,
  "createdAt": "2025-11-16T10:00:00Z",
  "updatedAt": "2025-11-16T10:05:00Z"
}
```

**Error Responses:**

- `404 Not Found`: 시나리오를 찾을 수 없음 또는 권한 없음
- `400 Bad Request`: 유효하지 않은 요청
- `500 Internal Server Error`: 서버 오류

---

## 🗄️ 데이터베이스 스키마

### scenario 테이블

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
| `scenario_id` | `BIGINT` | PK, AUTO_INCREMENT | 시나리오 고유 ID |
| `user_id` | `BIGINT` | NOT NULL | 사용자 ID |
| `subject_id` | `BIGINT` | FK | 주제 ID (`subject` 테이블) |
| `title` | `VARCHAR(200)` | NOT NULL | 시나리오 제목 |
| `status` | `VARCHAR(50)` | NOT NULL | 상태 (`ready`, `in_progress`, `finished`, `creating`, `generated`) |
| `ai_role` | `VARCHAR(100)` | NOT NULL | 이 시나리오의 AI 역할 (PM, Tech Lead 등) |
| `topic_type` | `ENUM('overview','detail')` | NOT NULL | 시나리오 깊이 |
| `fixed_questions` | `JSON` | - | 고정 질문 3개 (JSON 배열) |
| `created_at` | `TIMESTAMP` | NOT NULL | 생성 시각 |
| `updated_at` | `TIMESTAMP` | NOT NULL | 수정 시각 |

### subject 테이블

| 컬럼명 | 타입 | 제약 | 설명 |
|--------|------|------|------|
| `subject_id` | `BIGINT` | PK, AUTO_INCREMENT | 주제 고유 ID |
| `user_id` | `BIGINT` | NOT NULL | 사용자 ID |
| `my_role` | `VARCHAR(100)` | NOT NULL | 사용자 역할 |
| `source_type` | `VARCHAR(50)` | NOT NULL | 소스 타입 (`slack`, `github`, `prompt`) |
| `conversation_date` | `DATE` | - | 대화 날짜 (Slack/GitHub 소스인 경우) |
| `message_count` | `INT` | - | 메시지 개수 (Slack/GitHub 소스인 경우) |
| `created_at` | `TIMESTAMP` | NOT NULL | 생성 시각 |
| `updated_at` | `TIMESTAMP` | NOT NULL | 수정 시각 |

---

## 💡 구현 가이드

### JPA Entity 예시

**Scenario.java:**

```java
@Entity
@Table(name = "scenario")
@Getter
@Setter
@NoArgsConstructor
public class Scenario {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "scenario_id")
    private Long scenarioId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "subject_id")
    private Subject subject;

    @Column(name = "title", nullable = false, length = 200)
    private String title;

    @Column(name = "status", nullable = false, length = 50)
    private String status;

    @Column(name = "fixed_questions", columnDefinition = "JSON")
    @Convert(converter = JsonConverter.class)  // Custom converter for JSON type
    private List<String> fixedQuestions;

    @Column(name = "created_at", nullable = false, updatable = false)
    @CreatedDate
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    @LastModifiedDate
    private LocalDateTime updatedAt;
}
```

**Subject.java:**

```java
@Entity
@Table(name = "subject")
@Getter
@Setter
@NoArgsConstructor
public class Subject {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "subject_id")
    private Long subjectId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "my_role", nullable = false, length = 100)
    private String myRole;

    @Column(name = "ai_role", nullable = false, length = 100)
    private String aiRole;

    @Column(name = "topic_type", nullable = false, length = 50)
    private String topicType;

    @Column(name = "source_type", nullable = false, length = 50)
    private String sourceType;

    @Column(name = "conversation_date")
    private LocalDate conversationDate;

    @Column(name = "message_count")
    private Integer messageCount;

    @Column(name = "created_at", nullable = false, updatable = false)
    @CreatedDate
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    @LastModifiedDate
    private LocalDateTime updatedAt;

    @OneToMany(mappedBy = "subject", cascade = CascadeType.ALL)
    private List<Scenario> scenarios;
}
```

### Repository 예시

**ScenarioRepository.java:**

```java
public interface ScenarioRepository extends JpaRepository<Scenario, Long> {

    // 사용자별 시나리오 목록 조회 (페이징, 정렬)
    Page<Scenario> findByUserId(Long userId, Pageable pageable);

    // 사용자별 + 상태 필터
    Page<Scenario> findByUserIdAndStatus(Long userId, String status, Pageable pageable);

    // 사용자별 + 시나리오 상세 조회 (JOIN FETCH로 Subject 함께 조회)
    @Query("SELECT s FROM Scenario s JOIN FETCH s.subject WHERE s.scenarioId = :scenarioId AND s.userId = :userId")
    Optional<Scenario> findByScenarioIdAndUserId(@Param("scenarioId") Long scenarioId, @Param("userId") Long userId);

    // 사용자별 + 상태 + 소스타입 필터
    @Query("SELECT s FROM Scenario s JOIN s.subject sub WHERE s.userId = :userId " +
           "AND (:status IS NULL OR s.status = :status) " +
           "AND (:sourceType IS NULL OR sub.sourceType = :sourceType)")
    Page<Scenario> findByUserIdWithFilters(
        @Param("userId") Long userId,
        @Param("status") String status,
        @Param("sourceType") String sourceType,
        Pageable pageable
    );
}
```

### Service 예시

**ScenarioService.java:**

```java
@Service
@RequiredArgsConstructor
public class ScenarioService {

    private final ScenarioRepository scenarioRepository;

    public Page<ScenarioListDto> getScenarios(
        Long userId,
        String status,
        String sourceType,
        int page,
        int size,
        String sort
    ) {
        // Pageable 생성
        Sort sortOrder = Sort.by(Sort.Direction.DESC, "createdAt");
        if ("updatedAt,desc".equals(sort)) {
            sortOrder = Sort.by(Sort.Direction.DESC, "updatedAt");
        }
        Pageable pageable = PageRequest.of(page, size, sortOrder);

        // Repository 조회
        Page<Scenario> scenarios = scenarioRepository.findByUserIdWithFilters(
            userId, status, sourceType, pageable
        );

        // DTO 변환
        return scenarios.map(this::toListDto);
    }

    public ScenarioDetailDto getScenarioDetail(Long scenarioId, Long userId) {
        Scenario scenario = scenarioRepository.findByScenarioIdAndUserId(scenarioId, userId)
            .orElseThrow(() -> new NotFoundException("Scenario not found"));

        return toDetailDto(scenario);
    }

    private ScenarioListDto toListDto(Scenario scenario) {
        return ScenarioListDto.builder()
            .scenarioId(scenario.getScenarioId())
            .subjectId(scenario.getSubject().getSubjectId())
            .title(scenario.getTitle())
            .status(scenario.getStatus())
            .sourceType(scenario.getSubject().getSourceType())
            .myRole(scenario.getSubject().getMyRole())
            .aiRole(scenario.getSubject().getAiRole())
            .topicType(scenario.getSubject().getTopicType())
            .createdAt(scenario.getCreatedAt())
            .updatedAt(scenario.getUpdatedAt())
            .build();
    }

    private ScenarioDetailDto toDetailDto(Scenario scenario) {
        Subject subject = scenario.getSubject();
        return ScenarioDetailDto.builder()
            .scenarioId(scenario.getScenarioId())
            .subjectId(subject.getSubjectId())
            .title(scenario.getTitle())
            .status(scenario.getStatus())
            .sourceType(subject.getSourceType())
            .myRole(subject.getMyRole())
            .aiRole(subject.getAiRole())
            .topicType(subject.getTopicType())
            .fixedQuestions(scenario.getFixedQuestions())
            .conversationDate(subject.getConversationDate())
            .messageCount(subject.getMessageCount())
            .createdAt(scenario.getCreatedAt())
            .updatedAt(scenario.getUpdatedAt())
            .build();
    }
}
```

### Controller 예시

**ScenarioController.java:**

```java
@RestController
@RequestMapping("/api/v1/scenarios")
@RequiredArgsConstructor
public class ScenarioController {

    private final ScenarioService scenarioService;

    @GetMapping
    public ResponseEntity<Page<ScenarioListDto>> getScenarios(
        @RequestParam Long userId,
        @RequestParam(required = false) String status,
        @RequestParam(required = false) String sourceType,
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "10") int size,
        @RequestParam(defaultValue = "createdAt,desc") String sort
    ) {
        Page<ScenarioListDto> scenarios = scenarioService.getScenarios(
            userId, status, sourceType, page, size, sort
        );
        return ResponseEntity.ok(scenarios);
    }

    @GetMapping("/{scenarioId}")
    public ResponseEntity<ScenarioDetailDto> getScenarioDetail(
        @PathVariable Long scenarioId,
        @RequestParam Long userId
    ) {
        ScenarioDetailDto scenario = scenarioService.getScenarioDetail(scenarioId, userId);
        return ResponseEntity.ok(scenario);
    }
}
```

---

## ⚠️ 주의사항

1. **권한 검증**: 반드시 `userId`로 권한을 검증하여 다른 사용자의 시나리오에 접근할 수 없도록 해야 합니다.
2. **JOIN 최적화**: 상세 조회 시 `JOIN FETCH`를 사용하여 N+1 문제를 방지합니다.
3. **JSON 컬럼 처리**: `fixed_questions` 컬럼은 JSON 타입이므로, JPA Converter를 구현하여 `List<String>`으로 자동 변환되도록 합니다.
4. **페이징 성능**: 대량의 시나리오가 있을 경우 페이징 쿼리 성능에 주의합니다.
5. **예외 처리**: `NotFoundException`, `UnauthorizedException` 등 적절한 예외를 정의하고 처리합니다.

---

## 📝 추가 구현 사항 (선택)

### 1. 시나리오 삭제 API

```
DELETE /api/v1/scenarios/{scenarioId}?userId={userId}
```

### 2. 시나리오 상태 업데이트 API

```
PATCH /api/v1/scenarios/{scenarioId}/status
Body: { "status": "in_progress" }
```

### 3. 최근 시나리오 조회

```
GET /api/v1/scenarios/recent?userId={userId}&limit=5
```

---

## 🧪 테스트 가이드

### curl 예시

**시나리오 목록 조회:**

```bash
curl -X GET "http://localhost:8080/api/v1/scenarios?userId=1&status=ready&page=0&size=10"
```

**시나리오 상세 조회:**

```bash
curl -X GET "http://localhost:8080/api/v1/scenarios/500?userId=1"
```

### 통합 테스트 예시

```java
@SpringBootTest
@AutoConfigureMockMvc
class ScenarioControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void testGetScenarios() throws Exception {
        mockMvc.perform(get("/api/v1/scenarios")
                .param("userId", "1")
                .param("status", "ready"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content").isArray())
            .andExpect(jsonPath("$.totalElements").isNumber());
    }

    @Test
    void testGetScenarioDetail() throws Exception {
        mockMvc.perform(get("/api/v1/scenarios/500")
                .param("userId", "1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.scenarioId").value(500))
            .andExpect(jsonPath("$.fixedQuestions").isArray());
    }
}
```

---

## 📚 참고 자료

- FastAPI SessionService 구현: `app/roleplaying/services/session_service.py`
- DB 스키마: `database/schema.sql` (있다면)
- 세션 생성 API: `POST /roleplaying/sessions` (FastAPI)
- WebSocket 아키텍처: `docs/websocket_realtime_architecture.md`

---

## 문의사항

구현 중 질문이나 불명확한 부분이 있으면 백엔드 팀에 문의해주세요.
