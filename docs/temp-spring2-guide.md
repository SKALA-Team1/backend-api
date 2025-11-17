# ⚙️ 임시 Spring 2(Core) 서버 구성 가이드

FastAPI가 모델 서빙을 구현하는 동안, 실제 Spring 2 서버가 준비되지 않았더라도 CRUD 책임을 흉내 낼 수 있는 임시 서버가 필요합니다. 아래 체크리스트대로 구성하면 FastAPI와의 연동을 테스트하면서도 최종 아키텍처 규칙을 유지할 수 있습니다.

---

## 1. 최소 백엔드 스택
- **프레임워크**: Spring Boot 3(Java 17) 혹은 동일한 REST 프레임워크.
- **빌드**: Gradle/Maven. 의존성은 Spring Web, Spring Data JPA, PostgreSQL Driver 정도면 충분.
- **패키지 구조 예시**
  ```
  com.skala.springcore
   ├─ config        # DB, Redis, S3 등 클라이언트 설정
   ├─ controller    # 내부 API 엔드포인트
   ├─ service       # FastAPI 호출 및 비즈니스 로직
   ├─ repository    # JPA Repository
   └─ domain        # 엔티티/DTO
  ```

---

## 2. 데이터베이스 계층
임시 서버라도 실제 MySQL 스키마(`docs/db.sql`)와 동일한 테이블에 쓰기 작업을 수행해야 합니다.

- **엔티티**: `SlackMessage`, `Subject`, `Scenario`, `Reference`, `ScenarioReference`, `ScenarioSession` (MySQL 컬럼 스펙과 일치시킬 것).
- **Repository**
  - `SlackMessageRepository`: Slack 원문 저장/조회.
  - `SubjectRepository`: Slack 메시지와 사용자 컨텍스트 매핑.
  - `ScenarioRepository`: 시나리오 메타데이터 저장.
  - `ReferenceRepository`: 고정 질문/참고 문서 저장.
- **초기 데이터 스크립트**
  - `data.sql` 혹은 전용 Seeder를 만들어 FastAPI가 읽어올 mock 레코드를 INSERT.
  - 예: Slack 메시지 한 건, subject 1건, scenario draft 1건, reference 3건.

---

## 3. 내부 API 설계
FastAPI와의 통신을 위해 최소한 아래 엔드포인트를 제공합니다. 인증은 내부 네트워크에서만 호출된다 가정하고 간단한 토큰 또는 IP 필터만 구성해도 됩니다.

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/internal/scenarios/generate-request` | Slack 메시지 ID, subject 정보를 받아 FastAPI에 시나리오 생성을 요청. 요청 ID를 반환. |
| `POST` | `/internal/scenarios/{subjectId}/generate-result` | FastAPI가 생성한 시나리오/고정 질문을 전달. 서버는 DB에 INSERT. |
| `POST` | `/internal/sessions/{sessionId}/utterances` | FastAPI가 전송한 사용자 발화(오디오 base64, STT 텍스트)를 저장하도록 트리거. |
| `POST` | `/internal/sessions/{sessionId}/evaluation-result` | FastAPI 평가 결과를 저장. |
| `POST` | `/internal/sessions/{sessionId}/finish` | 세션 종료 처리(상태 업데이트, 평가 트리거). |

※ 실제 서버에서는 더 많은 API가 필요하지만, 임시 서버 목적이라면 위 4~5개면 대부분의 FastAPI 흐름을 검증할 수 있습니다.

---

## 4. FastAPI 연동 클라이언트
- **HTTP Client**: `WebClient` 또는 `RestTemplate`를 사용해 FastAPI 내부 엔드포인트(`/internal/scenarios/generate` 등)를 호출.
- **요청 데이터**: Slack 메시지 텍스트, 사용자 역할, subject topic 등 모델이 필요로 하는 필드를 그대로 전달.
- **응답 처리**: FastAPI가 반환한 시나리오 문장, 고정 질문 배열, 메타 정보 등을 DTO로 받아 DB에 저장.
- **예외 처리**: FastAPI 호출 실패 시 재시도(Backoff) 또는 DLQ(임시라면 메모리 큐)에 저장해 추후 수동 재처리.

---

## 5. Redis/세션 스텁
실제 Spring 1이 세션을 생성하지만, 임시 서버에서는 다음 두 가지 방법 중 택일합니다.
1. **Redis Mock**: 로컬 Redis 인스턴스를 띄우고 `session_id -> 세션정보`를 저장. FastAPI가 검증 시 사용할 수 있게 REST API(`/internal/sessions/{sessionId}`)도 제공.
2. **인메모리 구현**: 단순 테스트용이라면 ConcurrentHashMap으로 세션 정보를 저장하고 TTL 스케줄러로 만료시키는 방식도 가능.

---

## 6. S3/파일 업로드 스텁
- 실제 S3 대신 로컬 디렉터리에 저장하는 `FileStorageService`를 두고, 업로드 후 가짜 URL(`file://...`)을 반환하게 합니다.
- FastAPI가 `audio_blob`을 전달하면 디코딩 → 파일 저장 → URL 생성 → `scenario_message` 테이블에 `audio_url`로 기록.
- 나중에 실제 S3 연동으로 손쉽게 교체할 수 있도록 인터페이스를 분리합니다.

---

## 7. 로깅 & 모니터링
- FastAPI 요청/응답을 모두 로깅해 디버그 가능하도록 합니다. (예: `FastApiClient`에 Slf4j 로깅 추가)
- DB INSERT/업데이트 여부도 로그로 남겨 시나리오 생성→저장까지 추적 가능하게 합니다.

---

## 8. 실행 순서 요약
1. **Seed 데이터 삽입**: Slack 메시지, subject 등 최소 mock 데이터 준비.
2. **임시 Spring 2 서버 실행**.
3. **FastAPI에서 시나리오/고정 질문 생성 API 호출**.
4. **Spring 2가 결과를 DB에 저장하고 응답**.
5. **웹소켓/세션 흐름 테스트 시**: 세션 스텁 생성 → FastAPI가 `session_id`로 연결 → 발화 → `/internal/sessions/{id}/utterances` 호출.

이 가이드를 따르면 실제 Spring 2가 완성되기 전에 FastAPI 기능을 검증하고, 나중에 본 서버로 쉽게 이전할 수 있습니다.
