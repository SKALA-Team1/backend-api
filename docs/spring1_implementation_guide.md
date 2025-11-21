# Spring 1 (API Gateway) 구현 가이드

## 📋 개요

Spring 1은 SKALA 프로젝트의 **API Gateway 및 인증 서버**입니다.

**핵심 역할:**
- 사용자 인증/인가 (JWT)
- 세션 ID(UUID) 발급
- Spring 2에 세션 생성 요청
- 클라이언트 진입점

**핵심 원칙:**
- 클라이언트의 모든 요청은 Spring 1을 통해 진입
- 세션 ID(UUID)는 Spring 1이 발급
- 즉시 검증: Spring 2 호출로 HTTP 응답 전에 검증 완료

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```
┌──────────────┐
│   Client     │
└──────────────┘
        │
        │ HTTP + JWT
        ▼
┌──────────────┐
│  Spring 1    │  ← API Gateway + Session Issuer
│              │
│ 1. JWT 검증  │
│ 2. UUID 생성 │  session_id = UUID.randomUUID()
│ 3. Spring 2  │  → POST /internal/sessions
│    호출       │  ← {success: true}
│ 4. WS URL    │
│    반환       │
└──────────────┘
        │
        │ Spring 2 호출
        ▼
┌──────────────┐         ┌──────────────┐
│   Spring 2   │         │   FastAPI    │
│              │         │              │
│ - 세션 검증  │         │ - WebSocket  │
│ - DB INSERT  │◄────────│ - 세션 확인  │
│ - S3 Upload  │         │ - STT/LLM    │
└──────────────┘         └──────────────┘
        │                        │
        ▼                        ▼
┌──────────────┐         ┌──────────────┐
│    MySQL     │         │    Redis     │
│              │         │  (캐싱용)     │
└──────────────┘         └──────────────┘
```

---

## 🔄 세션 생성 플로우

### 전체 흐름

```
1. Client → Spring 1: POST /roleplaying/sessions
   Headers: Authorization: Bearer <JWT>
   Body: {
     "userId": 1,
     "scenarioId": 31
   }

2. Spring 1:
   ✅ JWT 검증
   ✅ userId 추출
   ✅ UUID 생성: "abc-123-def-456"
   ✅ Spring 2 호출:
      POST /internal/sessions
      {
        "session_id": "abc-123-def-456",
        "user_id": 1,
        "scenario_id": 31
      }

3. Spring 2:
   ✅ 시나리오 검증 (DB)
   ✅ sessions 테이블 INSERT
   ✅ 응답: {success: true}

4. Spring 1 → Client:
   {
     "session_id": "abc-123-def-456",
     "ws_url": "wss://fastapi.skala.com/ws/roleplaying/abc-123-def-456"
   }

5. Client → FastAPI: WebSocket 연결
   /ws/roleplaying/abc-123-def-456

6. FastAPI:
   ✅ 세션 확인 (Redis 캐시 또는 Spring 2 조회)
   ✅ WebSocket 연결 수락
   ✅ INIT 메시지 처리
```

---

## 📦 API 명세

### 세션 생성 API

**Endpoint:** `POST /roleplaying/sessions`

**역할:**
1. JWT 검증
2. UUID 세션 ID 발급
3. Spring 2 호출하여 세션 생성
4. WebSocket URL 반환

#### 요청

```http
POST /roleplaying/sessions
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "userId": 1,
  "scenarioId": 31
}
```

**Headers:**
- `Authorization`: JWT 토큰 (필수)
  - Format: `Bearer <token>`

**Body:**
- `userId` (integer, 필수): 사용자 ID
- `scenarioId` (integer, 필수): 시나리오 ID

#### 응답

**성공 (201 Created):**

```json
{
  "session_id": "abc-123-def-456",
  "ws_url": "wss://fastapi.skala.com/ws/roleplaying/abc-123-def-456"
}
```

**실패 (401 Unauthorized):**
```json
{
  "error": "Invalid or expired JWT token",
  "timestamp": "2025-11-18T10:00:00Z"
}
```

**실패 (404 Not Found):**
```json
{
  "error": "Scenario not found or not accessible by user",
  "timestamp": "2025-11-18T10:00:00Z"
}
```

**실패 (500 Internal Server Error):**
```json
{
  "error": "Failed to create session in Spring 2",
  "timestamp": "2025-11-18T10:00:00Z"
}
```

---

## 🔐 JWT 인증

### JWT 구조

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "1",
    "userId": 1,
    "role": "user",
    "iat": 1700000000,
    "exp": 1700086400
  },
  "signature": "..."
}
```

### JWT 검증 로직

```java
@Component
public class JwtService {

    @Value("${jwt.secret}")
    private String jwtSecret;

    public Claims verify(String authHeader) {
        // Bearer 접두사 제거
        if (!authHeader.startsWith("Bearer ")) {
            throw new UnauthorizedException("Invalid Authorization header format");
        }

        String token = authHeader.substring(7);

        try {
            return Jwts.parser()
                .setSigningKey(jwtSecret)
                .parseClaimsJws(token)
                .getBody();

        } catch (ExpiredJwtException e) {
            throw new UnauthorizedException("JWT token expired");
        } catch (JwtException e) {
            throw new UnauthorizedException("Invalid JWT token");
        }
    }

    public Long getUserId(Claims claims) {
        return Long.parseLong(claims.getSubject());
    }
}
```

---

## 🔗 Spring 2 연동

### Spring 2 클라이언트 구현

```java
@Service
@Slf4j
public class Spring2Client {

    @Value("${spring2.base-url}")
    private String spring2BaseUrl;

    @Value("${spring2.timeout:10}")
    private int timeoutSeconds;

    private final WebClient webClient;

    public Spring2Client(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder
            .baseUrl(spring2BaseUrl)
            .build();
    }

    /**
     * Spring 2에 세션 생성 요청
     *
     * @param sessionId UUID 세션 ID
     * @param userId 사용자 ID
     * @param scenarioId 시나리오 ID
     * @return 생성 결과
     * @throws BadRequestException 시나리오가 유효하지 않은 경우
     * @throws InternalServerException Spring 2 호출 실패
     */
    public Spring2SessionResponse createSession(
        String sessionId,
        Long userId,
        Integer scenarioId
    ) {
        try {
            log.info("Creating session in Spring 2: session={}, user={}, scenario={}",
                sessionId, userId, scenarioId);

            Spring2SessionResponse response = webClient.post()
                .uri("/internal/sessions")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of(
                    "session_id", sessionId,
                    "user_id", userId,
                    "scenario_id", scenarioId
                ))
                .retrieve()
                .bodyToMono(Spring2SessionResponse.class)
                .block(Duration.ofSeconds(timeoutSeconds));

            if (response == null) {
                throw new InternalServerException("Empty response from Spring 2");
            }

            if (!response.getSuccess()) {
                log.warn("Session creation rejected by Spring 2: {}", response.getError());
                throw new BadRequestException(
                    response.getError() != null ? response.getError() : "Invalid scenario"
                );
            }

            log.info("Session created successfully in Spring 2: {}", sessionId);
            return response;

        } catch (WebClientResponseException e) {
            log.error("Spring 2 error response: status={}, body={}",
                e.getStatusCode(), e.getResponseBodyAsString());

            if (e.getStatusCode().is4xxClientError()) {
                throw new BadRequestException("Invalid session request");
            }

            throw new InternalServerException("Spring 2 session creation failed");

        } catch (Exception e) {
            log.error("Failed to create session in Spring 2: {}", e.getMessage(), e);
            throw new InternalServerException("Failed to communicate with Spring 2");
        }
    }
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Spring2SessionResponse {
    private Boolean success;
    private String error;
}
```

---

## 💻 Controller 구현

```java
@RestController
@RequestMapping("/roleplaying")
@Slf4j
public class SessionController {

    @Autowired
    private JwtService jwtService;

    @Autowired
    private Spring2Client spring2Client;

    @Value("${fastapi.ws-url}")
    private String fastapiWsUrl;

    @PostMapping("/sessions")
    public ResponseEntity<SessionResponse> createSession(
        @RequestHeader("Authorization") String authHeader,
        @Valid @RequestBody SessionRequest request
    ) {
        log.info("Session creation request: userId={}, scenarioId={}",
            request.getUserId(), request.getScenarioId());

        // 1. JWT 검증
        Claims claims = jwtService.verify(authHeader);
        Long userId = jwtService.getUserId(claims);

        // JWT의 userId와 요청의 userId 일치 확인
        if (!userId.equals(request.getUserId())) {
            log.warn("User ID mismatch: jwt={}, request={}", userId, request.getUserId());
            throw new ForbiddenException("User ID mismatch");
        }

        // 2. UUID 생성
        String sessionId = UUID.randomUUID().toString();

        // 3. Spring 2에 세션 생성 요청
        spring2Client.createSession(sessionId, userId, request.getScenarioId());

        // 4. WebSocket URL 생성
        String wsUrl = String.format(
            "%s/ws/roleplaying/%s",
            fastapiWsUrl,
            sessionId
        );

        log.info("Session created successfully: sessionId={}, userId={}, scenarioId={}",
            sessionId, userId, request.getScenarioId());

        // 5. 응답 반환
        SessionResponse response = SessionResponse.builder()
            .sessionId(sessionId)
            .wsUrl(wsUrl)
            .build();

        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}
```

---

## 📦 DTO 정의

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionRequest {

    @NotNull(message = "userId is required")
    private Long userId;

    @NotNull(message = "scenarioId is required")
    private Integer scenarioId;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SessionResponse {

    @JsonProperty("session_id")
    private String sessionId;

    @JsonProperty("ws_url")
    private String wsUrl;
}
```

---

## 🛡️ 예외 처리

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(UnauthorizedException.class)
    public ResponseEntity<ErrorResponse> handleUnauthorized(UnauthorizedException e) {
        log.warn("Unauthorized access: {}", e.getMessage());
        return ResponseEntity
            .status(HttpStatus.UNAUTHORIZED)
            .body(ErrorResponse.builder()
                .error(e.getMessage())
                .timestamp(LocalDateTime.now())
                .build());
    }

    @ExceptionHandler(ForbiddenException.class)
    public ResponseEntity<ErrorResponse> handleForbidden(ForbiddenException e) {
        log.warn("Forbidden access: {}", e.getMessage());
        return ResponseEntity
            .status(HttpStatus.FORBIDDEN)
            .body(ErrorResponse.builder()
                .error(e.getMessage())
                .timestamp(LocalDateTime.now())
                .build());
    }

    @ExceptionHandler(BadRequestException.class)
    public ResponseEntity<ErrorResponse> handleBadRequest(BadRequestException e) {
        log.warn("Bad request: {}", e.getMessage());
        return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(ErrorResponse.builder()
                .error(e.getMessage())
                .timestamp(LocalDateTime.now())
                .build());
    }

    @ExceptionHandler(InternalServerException.class)
    public ResponseEntity<ErrorResponse> handleInternalError(InternalServerException e) {
        log.error("Internal server error: {}", e.getMessage(), e);
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorResponse.builder()
                .error(e.getMessage())
                .timestamp(LocalDateTime.now())
                .build());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericError(Exception e) {
        log.error("Unexpected error: {}", e.getMessage(), e);
        return ResponseEntity
            .status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorResponse.builder()
                .error("Internal server error")
                .timestamp(LocalDateTime.now())
                .build());
    }
}

@Data
@Builder
public class ErrorResponse {
    private String error;
    private LocalDateTime timestamp;
}
```

---

## 📂 패키지 구조

```
com.skala.spring1
├── config
│   ├── JwtConfig.java              # JWT 설정
│   ├── WebClientConfig.java        # WebClient 설정
│   └── SecurityConfig.java         # Spring Security 설정
├── controller
│   └── SessionController.java      # 세션 생성 API
├── service
│   ├── JwtService.java             # JWT 검증
│   └── Spring2Client.java          # Spring 2 HTTP 클라이언트
├── dto
│   ├── SessionRequest.java
│   ├── SessionResponse.java
│   └── Spring2SessionResponse.java
├── exception
│   ├── UnauthorizedException.java
│   ├── ForbiddenException.java
│   ├── BadRequestException.java
│   ├── InternalServerException.java
│   └── GlobalExceptionHandler.java
└── SkalaSpring1Application.java
```

---

## ⚙️ 설정 파일

### application.yml

```yaml
spring:
  application:
    name: skala-spring1

server:
  port: 8080

# JWT 설정
jwt:
  secret: ${JWT_SECRET:your-secret-key-change-in-production}
  expiration: 86400000  # 24시간 (밀리초)

# Spring 2 연동
spring2:
  base-url: ${SPRING2_BASE_URL:http://localhost:8081}
  timeout: 10  # 초

# FastAPI 연동
fastapi:
  ws-url: ${FASTAPI_WS_URL:wss://fastapi.skala.com}

# 로깅
logging:
  level:
    com.skala.spring1: INFO
    org.springframework.web: DEBUG
```

### WebClient 설정

```java
@Configuration
public class WebClientConfig {

    @Bean
    public WebClient.Builder webClientBuilder() {
        return WebClient.builder()
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE);
    }
}
```

---

## 🧪 테스트

### 단위 테스트

```java
@SpringBootTest
@AutoConfigureMockMvc
class SessionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private Spring2Client spring2Client;

    @MockBean
    private JwtService jwtService;

    @Test
    void createSession_Success() throws Exception {
        // Given
        String jwt = "valid-jwt-token";
        Long userId = 1L;
        Integer scenarioId = 31;

        Claims claims = Mockito.mock(Claims.class);
        when(jwtService.verify("Bearer " + jwt)).thenReturn(claims);
        when(jwtService.getUserId(claims)).thenReturn(userId);

        Spring2SessionResponse spring2Response = Spring2SessionResponse.builder()
            .success(true)
            .build();
        when(spring2Client.createSession(anyString(), eq(userId), eq(scenarioId)))
            .thenReturn(spring2Response);

        // When & Then
        mockMvc.perform(post("/roleplaying/sessions")
                .header("Authorization", "Bearer " + jwt)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"userId\": 1, \"scenarioId\": 31}"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.session_id").exists())
            .andExpect(jsonPath("$.ws_url").exists());
    }

    @Test
    void createSession_InvalidJwt() throws Exception {
        // Given
        when(jwtService.verify(anyString()))
            .thenThrow(new UnauthorizedException("Invalid JWT"));

        // When & Then
        mockMvc.perform(post("/roleplaying/sessions")
                .header("Authorization", "Bearer invalid-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"userId\": 1, \"scenarioId\": 31}"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void createSession_InvalidScenario() throws Exception {
        // Given
        Claims claims = Mockito.mock(Claims.class);
        when(jwtService.verify(anyString())).thenReturn(claims);
        when(jwtService.getUserId(claims)).thenReturn(1L);

        when(spring2Client.createSession(anyString(), anyLong(), anyInt()))
            .thenThrow(new BadRequestException("Scenario not found"));

        // When & Then
        mockMvc.perform(post("/roleplaying/sessions")
                .header("Authorization", "Bearer valid-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"userId\": 1, \"scenarioId\": 999}"))
            .andExpect(status().isBadRequest());
    }
}
```

### 통합 테스트

```bash
# 1. JWT 토큰 발급 (별도 인증 API 필요)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 2. 세션 생성
curl -X POST http://localhost:8080/roleplaying/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": 1,
    "scenarioId": 31
  }'

# 응답 예시
{
  "session_id": "abc-123-def-456",
  "ws_url": "wss://fastapi.skala.com/ws/roleplaying/abc-123-def-456"
}
```

---

## 🚀 배포

### 환경 변수

```bash
# JWT
JWT_SECRET=your-very-long-secret-key-at-least-256-bits

# Spring 2
SPRING2_BASE_URL=http://spring2:8081

# FastAPI
FASTAPI_WS_URL=wss://fastapi.skala.com
```

### Docker Compose

```yaml
version: '3.8'

services:
  spring1:
    image: skala/spring1:latest
    ports:
      - "8080:8080"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - SPRING2_BASE_URL=http://spring2:8081
      - FASTAPI_WS_URL=wss://fastapi:8001
    depends_on:
      - spring2
    networks:
      - skala-network

  spring2:
    image: skala/spring2:latest
    ports:
      - "8081:8081"
    networks:
      - skala-network

  fastapi:
    image: skala/fastapi:latest
    ports:
      - "8001:8001"
    networks:
      - skala-network

networks:
  skala-network:
    driver: bridge
```

---

## 📝 체크리스트

### 구현 완료 확인

- [ ] JWT 검증 구현 (JwtService)
- [ ] 세션 생성 API 구현 (SessionController)
- [ ] Spring 2 클라이언트 구현 (Spring2Client)
- [ ] 예외 처리 구현 (GlobalExceptionHandler)
- [ ] DTO 정의 (Request/Response)
- [ ] 로깅 추가
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 환경 변수 설정
- [ ] Docker 이미지 빌드

### 배포 확인

- [ ] JWT_SECRET 환경 변수 설정
- [ ] Spring 2 연결 확인
- [ ] FastAPI WebSocket URL 설정
- [ ] HTTPS 설정 (프로덕션)
- [ ] CORS 설정 (필요시)
- [ ] 모니터링 설정

---

## 📚 참고 자료

- `docs/spring2_roleplaying_implementation_prompt.md` - Spring 2 구현 가이드
- `docs/websocket_realtime_architecture.md` - FastAPI WebSocket 아키텍처

**작성자:** Claude Code
**최종 수정일:** 2025-11-18
**문서 위치:** `/docs/spring1_implementation_guide.md`