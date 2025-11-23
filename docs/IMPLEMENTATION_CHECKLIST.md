# FastAPI 구현 체크리스트

**목표:** 모든 필요한 기능을 체계적으로 구현하기 위한 실행 가능한 체크리스트

---

## 🎯 Phase 1: Core WebSocket 통합 (핵심)

### 1.1 세션 생성 및 관리

- [ ] **`POST /roleplaying/sessions` 완성**
  - [ ] 요청 검증 (userId, scenarioId 필수)
  - [ ] DB에서 시나리오 조회
    - [ ] subjects 테이블 조회 (subject_id 확인)
    - [ ] scenarios 테이블 조회 (고정 질문 포함)
  - [ ] Redis에 세션 저장 (30분 TTL)
  - [ ] SessionCreateResponse 반환
  - [ ] 테스트: curl/Postman으로 검증

- [ ] **Redis 세션 저장소 구현**
  - [ ] Key format: `session:{session_id}`
  - [ ] Value: session 메타데이터 JSON
  - [ ] TTL 설정 (30분)
  - [ ] 만료 처리

### 1.2 WebSocket 연결 관리

- [ ] **`WS /ws/roleplaying/{session_id}` 완성**
  - [ ] 연결 수락
  - [ ] Redis 세션 검증 (1회)
  - [ ] 타임아웃 처리
  - [ ] 연결 종료 시 정리

- [ ] **INIT 메시지 처리**
  - [ ] 메시지 파싱 및 검증
  - [ ] 세션 상태 초기화
  - [ ] 첫 AI 질문 생성
  - [ ] ACK 메시지 전송

- [ ] **세션 상태 관리 (`SessionManager`)**
  - [ ] 상태 머신 (INIT → WAITING → PROCESSING → FINISHED)
  - [ ] 턴 카운팅
  - [ ] 타이머 관리

### 1.3 STT (Speech-to-Text) 처리

- [ ] **오디오 청크 수신**
  - [ ] 바이너리 프레임 처리
  - [ ] 청크 누적 버퍼 관리
  - [ ] 메모리 효율성 고려

- [ ] **Whisper 통합**
  - [ ] 로컬 또는 OpenAI API 선택
  - [ ] 모델 로드 및 초기화
  - [ ] 오디오 처리 (WAV/WebM)
  - [ ] STT_PARTIAL 메시지 전송
  - [ ] STT_FINAL 메시지 전송

- [ ] **오디오 저장**
  - [ ] 임시 파일 생성
  - [ ] Spring 2로 업로드 요청
  - [ ] S3 URL 받기
  - [ ] 파일 정리

### 1.4 AI 응답 생성

- [ ] **AI Tutor Service 구현**
  - [ ] OpenAI/Claude/Ollama 클라이언트 선택
  - [ ] 프롬프트 구성
    - [ ] 시스템 프롬프트 (역할, 문맥)
    - [ ] 대화 히스토리
    - [ ] 고정 질문 관리

- [ ] **고정 질문 관리**
  - [ ] 3개 고정 질문 저장
  - [ ] 턴별 질문 선택 (1, 5, 10 턴)
  - [ ] `is_fixed_question` 플래그 설정

- [ ] **동적 응답 생성**
  - [ ] 사용자 입력 분석
  - [ ] 컨텍스트 고려
  - [ ] 피드백 포함 (선택사항)

- [ ] **AI_TYPING 메시지**
  - [ ] 응답 생성 전 전송

### 1.5 메시지 처리

- [ ] **USER_TEXT 메시지 처리** (테스트용)
  - [ ] 텍스트 검증
  - [ ] STT 단계 스킵
  - [ ] 바로 AI 응답 생성

- [ ] **UTTERANCE_END 메시지 처리**
  - [ ] STT 최종 결과 확정
  - [ ] Spring 2에 발화 저장 요청
  - [ ] UTTERANCE_SAVED 메시지 전송

- [ ] **END_SESSION 메시지 처리**
  - [ ] 세션 종료 처리
  - [ ] Spring 2에 종료 신호 전송
  - [ ] SESSION_ENDED 메시지 전송
  - [ ] 리소스 정리

- [ ] **에러 처리**
  - [ ] 유효하지 않은 메시지 → ERROR 메시지
  - [ ] 처리 실패 → ERROR 메시지
  - [ ] 심각한 오류 → 연결 종료

### 1.6 Spring 2 통합

- [ ] **Spring 2 클라이언트 구현** (`integrations/clients/spring2_client.py`)
  - [ ] HTTP 클라이언트 설정 (httpx)
  - [ ] 기본 에러 처리
  - [ ] 재시도 로직 (exponential backoff)

- [ ] **세션 생성 API 호출**
  - [ ] `POST /api/v1/roleplaying/sessions`
  - [ ] 요청: session_id, user_id, scenario_id
  - [ ] 응답 처리

- [ ] **발화 저장 API 호출**
  - [ ] `POST /api/v1/roleplaying/sessions/{session_id}/utterances`
  - [ ] 요청: utterance_index, speaker, text, s3_url, timestamps
  - [ ] 응답 처리

- [ ] **세션 종료 API 호출**
  - [ ] `PUT /api/v1/roleplaying/sessions/{session_id}/finish`
  - [ ] 요청: end_reason, ended_at
  - [ ] 응답 처리

### 1.7 테스트

- [ ] **단위 테스트**
  - [ ] STT Service
  - [ ] AI Tutor Service
  - [ ] Session Manager
  - [ ] Spring 2 Client

- [ ] **통합 테스트**
  - [ ] WebSocket 연결 → INIT → 첫 AI 질문
  - [ ] 오디오 → STT → AI 응답 → 발화 저장
  - [ ] 다중 턴 대화
  - [ ] 타임아웃 및 에러

- [ ] **E2E 테스트**
  - [ ] 실제 클라이언트와 테스트
  - [ ] 부하 테스트 (동시 연결)

---

## 🎯 Phase 2: 추가 API 엔드포인트

### 2.1 사용자 정보 API

- [ ] **`GET /roleplaying/userInfo`**
  - [ ] 인증 토큰 검증
  - [ ] 사용자 정보 조회
  - [ ] 통합 상태 반환

- [ ] **`GET /roleplaying/userStatics`**
  - [ ] 대화 시간 집계
  - [ ] 순위 조회
  - [ ] 팀 정보 반환

### 2.2 롤플레잉 목록 API

- [ ] **`GET /roleplaying/roleplayList`**
  - [ ] 페이지네이션 (page, size)
  - [ ] 필터링 (status, source_type)
  - [ ] 정렬 (created_at, updated_at)
  - [ ] 날짜 범위 필터

### 2.3 프롬프트 기반 생성 API

- [ ] **`POST /roleplaying/prompt_create`**
  - [ ] AI 역할, 사용자 역할, 상황 입력
  - [ ] 총 턴 수 설정
  - [ ] 턴 플랜 생성
  - [ ] 응답 반환

### 2.4 세션 시작/다음 턴 API

- [ ] **`POST /roleplaying/{roleplayingId}/session/start`**
  - [ ] 세션 생성
  - [ ] 첫 AI 질문 생성

- [ ] **`POST /roleplaying/{sessionId}/nextTurn`**
  - [ ] 사용자 메시지 저장
  - [ ] AI 응답 생성

- [ ] **`GET /roleplaying/{sessionId}/messages`**
  - [ ] 대화 히스토리 조회
  - [ ] 페이지네이션

---

## 🎯 Phase 3: 교재 및 피드백 모듈

### 3.1 Textbook 모듈

- [ ] **`POST /textbook/lessons/{lessonId}/start`**
- [ ] **`POST /textbook/lessons/{sessionId}/submit-answer`**
- [ ] **`POST /textbook/lessons/{sessionId}/finish`**
- [ ] **`GET /textbook/lessons/{sessionId}/review`**

### 3.2 Feedback 모듈

- [ ] **피드백 수집**
  - [ ] 점수 계산
  - [ ] 요약 생성
  - [ ] 개선 제안

### 3.3 MyPage 모듈

- [ ] **프로필 관리**
- [ ] **북마크 관리**
- [ ] **순위 시스템**
- [ ] **설정 관리**

---

## ✅ Quality Assurance

### 코드 품질

- [ ] **타입 체크**
  ```bash
  mypy app/ --strict
  ```

- [ ] **코드 포매팅**
  ```bash
  black app/
  isort app/
  ```

- [ ] **린팅**
  ```bash
  flake8 app/ --max-line-length=100
  ```

### 테스트 커버리지

- [ ] 단위 테스트 (70% 이상)
- [ ] 통합 테스트 (중요 경로)
- [ ] 커버리지 리포트 생성

### 문서화

- [ ] 함수 docstring 작성
- [ ] API 엔드포인트 문서화
- [ ] WebSocket 메시지 명세
- [ ] 환경 변수 설명

### 보안

- [ ] SQL Injection 방지 (SQLAlchemy ORM 사용)
- [ ] CORS 설정 검증
- [ ] 타임아웃 설정
- [ ] 에러 메시지 보안 검토

---

## 📊 진행률 추적

| Phase | 상태 | 진행도 | 예상 완료일 |
|-------|------|--------|-----------|
| Phase 1: Core WebSocket | ⏳ 진행 중 | 0% | 2025-12-10 |
| Phase 2: 추가 API | 📋 계획 중 | 0% | 2025-12-24 |
| Phase 3: 부가 기능 | 📋 계획 중 | 0% | 2026-01-10 |
| QA & 배포 | 📋 계획 중 | 0% | 2026-01-31 |

---

## 🔗 관련 문서

- **[요구사항 정의서](REQUIREMENTS_DEFINITION.md)** - 상세 명세
- **[WebSocket 아키텍처](websocket_realtime_architecture.md)** - 시스템 구조
- **[Spring 2 통합 가이드](spring2_roleplaying_implementation_prompt.md)** - 연동 방법
- **[API 테스트 가이드](api_test_guide.md)** - 테스트 방법

---

**마지막 업데이트:** 2025-11-20
**담당자:** Backend Team