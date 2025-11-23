# FastAPI 롤플레잉 서버 구현 WBS (Work Breakdown Structure)

**문서 버전:** 1.0
**작성일:** 2025-11-20
**범위:** FastAPI 백엔드 전체 구현

---

## 📋 WBS 개요

```
SKALA FastAPI 백엔드 구현
├── 1. 인프라 및 설정 (Infra & Config)
├── 2. 데이터베이스 및 모델링 (Database & Models)
├── 3. 세션 및 메시지 처리 (Session & Messages)
├── 4. 실시간 통신 (Real-time Communication)
├── 5. AI 및 외부 서비스 (AI & External Services)
├── 6. Spring 2 통합 (Spring 2 Integration)
├── 7. API 엔드포인트 (API Endpoints)
├── 8. 테스트 및 검증 (Testing & Validation)
└── 9. 문서화 및 배포 (Documentation & Deployment)
```

---

## 1. 인프라 및 설정 (Infra & Config)

### 1.1 환경 설정 관리
**예상 시간:** 4h
- [ ] `.env.example` 완성
- [ ] `app/config.py` 확장 (Redis, Spring 2, STT, LLM 설정)
- [ ] 개발/프로덕션 환경 분리
- [ ] 환경 변수 검증 로직
- [ ] 설정 마이그레이션 가이드 작성

### 1.2 로깅 및 모니터링
**예상 시간:** 6h
- [ ] 구조화된 로깅 설정 확인
- [ ] WebSocket 로그 추가
- [ ] 성능 모니터링 메트릭
- [ ] 에러 추적 (Sentry 선택사항)
- [ ] 로그 레벨 관리

### 1.3 예외 처리 및 상태 코드
**예상 시간:** 4h
- [ ] AppException 상속 클래스 정의
  - [ ] WebSocketException
  - [ ] STTException
  - [ ] AIServiceException
  - [ ] Spring2Exception
- [ ] HTTP 상태 코드 확장
- [ ] 에러 응답 표준화

### 1.4 CORS 및 보안 설정
**예상 시간:** 3h
- [ ] CORS 정책 설정
- [ ] CSRF 토큰 처리
- [ ] 레이트 제한 설정
- [ ] 타임아웃 설정

**소계:** 17h

---

## 2. 데이터베이스 및 모델링 (Database & Models)

### 2.1 데이터베이스 스키마 설계
**예상 시간:** 6h
- [ ] subjects 테이블 확인 및 인덱스 최적화
- [ ] scenarios 테이블 확인 및 필드 검증
- [ ] sessions 테이블 생성 (Spring 2용)
- [ ] utterances 테이블 생성 (Spring 2용)
- [ ] 외래 키 관계 설정
- [ ] 인덱스 전략 수립

### 2.2 Alembic 마이그레이션
**예상 시간:** 4h
- [ ] 마이그레이션 파일 생성
  - [ ] sessions 테이블 마이그레이션
  - [ ] utterances 테이블 마이그레이션
- [ ] 마이그레이션 테스트
- [ ] 롤백 테스트

### 2.3 SQLAlchemy 모델 정의
**예상 시간:** 5h
- [ ] Subject 모델 확인
- [ ] Scenario 모델 확인
- [ ] Session 모델 생성
- [ ] Utterance 모델 생성
- [ ] 관계 매핑 설정
- [ ] 유효성 검증 추가

### 2.4 repository 패턴 구현
**예상 시간:** 6h
- [ ] ScenarioRepository
  - [ ] find_by_id_and_user_id()
  - [ ] find_by_user_id()
- [ ] SessionRepository
  - [ ] create_session()
  - [ ] find_session()
  - [ ] update_session_status()
- [ ] UtteranceRepository
  - [ ] save_utterance()
  - [ ] get_utterances()

**소계:** 21h

---

## 3. 세션 및 메시지 처리 (Session & Messages)

### 3.1 메시지 모델 정의
**예상 시간:** 4h
- [ ] 인바운드 메시지 모델 확인
  - [ ] InitMessage
  - [ ] UtteranceEndMessage
  - [ ] UserTextMessage
  - [ ] EndSessionMessage
- [ ] 아웃바운드 메시지 모델 확인
  - [ ] AckMessage
  - [ ] AiTextMessage
  - [ ] SttPartialMessage
  - [ ] SttFinalMessage
  - [ ] ErrorMessage 등
- [ ] 메시지 검증 로직

### 3.2 세션 상태 관리자
**예상 시간:** 8h
- [ ] SessionState 클래스 설계
  - [ ] 상태 머신 구현
  - [ ] 전이 검증
- [ ] SessionManager 클래스 구현
  - [ ] 세션 생성/조회/업데이트
  - [ ] 턴 관리
  - [ ] 타이머 관리
- [ ] 인메모리 세션 저장소
- [ ] 타임아웃 처리

### 3.3 Redis 세션 검증
**예상 시간:** 6h
- [ ] RedisSessionValidator 구현
  - [ ] 세션 조회
  - [ ] TTL 갱신
  - [ ] 세션 생성
  - [ ] 세션 삭제
- [ ] 에러 처리 (연결 실패, 키 없음)
- [ ] 재시도 로직

### 3.4 메시지 라우팅
**예상 시간:** 5h
- [ ] 메시지 타입별 핸들러 매핑
- [ ] 메시지 검증 미들웨어
- [ ] 메시지 큐/버퍼 관리
- [ ] 동시성 제어

**소계:** 23h

---

## 4. 실시간 통신 (Real-time Communication)

### 4.1 WebSocket 엔드포인트
**예상 시간:** 8h
- [ ] `WS /ws/roleplaying/{session_id}` 완성
  - [ ] 연결 수락
  - [ ] 세션 검증
  - [ ] 연결 유지 관리
  - [ ] 에러 처리
  - [ ] 종료 처리
- [ ] WebSocket 대역폭 최적화
- [ ] 연결 모니터링

### 4.2 메시지 처리 흐름
**예상 시간:** 12h
- [ ] INIT 메시지 처리
  - [ ] 세션 초기화
  - [ ] 첫 AI 질문 생성
  - [ ] ACK 응답
- [ ] UTTERANCE_END 메시지 처리
  - [ ] STT 최종화
  - [ ] Spring 2 저장 요청
  - [ ] UTTERANCE_SAVED 응답
- [ ] USER_TEXT 메시지 처리
  - [ ] 텍스트 검증
  - [ ] AI 응답 생성
- [ ] END_SESSION 메시지 처리
  - [ ] 세션 종료
  - [ ] 리소스 정리
  - [ ] SESSION_ENDED 응답

### 4.3 오디오 스트리밍 처리
**예상 시간:** 6h
- [ ] 바이너리 프레임 수신
- [ ] 오디오 버퍼 관리
- [ ] 청크 누적 로직
- [ ] 메모리 최적화

### 4.4 타이머 및 타임아웃
**예상 시간:** 4h
- [ ] 세션 타임아웃 (30분)
- [ ] INIT 메시지 타임아웃 (30초)
- [ ] 응답 대기 타임아웃 (60초)
- [ ] 타이머 정리 및 취소

**소계:** 30h

---

## 5. AI 및 외부 서비스 (AI & External Services)

### 5.1 STT (Speech-to-Text) 서비스
**예상 시간:** 10h
- [ ] Whisper 통합
  - [ ] 모델 초기화
  - [ ] 오디오 전처리
  - [ ] 음성 인식
  - [ ] 에러 처리
- [ ] 대체 STT 지원 (Google Cloud Speech, Azure)
- [ ] STT 결과 캐싱
- [ ] 성능 최적화

### 5.2 AI Tutor 서비스
**예상 시간:** 12h
- [ ] OpenAI 클라이언트 통합
  - [ ] API 키 관리
  - [ ] 요청 포맷팅
  - [ ] 응답 파싱
  - [ ] 스트리밍 지원 (선택사항)
- [ ] Claude/Ollama 대체 지원
- [ ] 프롬프트 엔지니어링
  - [ ] 시스템 프롬프트
  - [ ] 컨텍스트 구성
  - [ ] 고정 질문 관리
- [ ] 응답 캐싱

### 5.3 고정 질문 관리
**예상 시간:** 4h
- [ ] 3개 고정 질문 저장/조회
- [ ] 턴별 질문 선택 로직
- [ ] `is_fixed_question` 플래그 설정
- [ ] 질문 다양성 보장

### 5.4 TTS (Text-to-Speech) 지원
**예상 시간:** 6h
- [ ] OpenAI TTS 또는 Google TTS 선택
- [ ] 오디오 생성 및 인코딩
- [ ] 클라이언트로 전송
- [ ] 캐싱 전략

### 5.5 외부 서비스 에러 처리
**예상 시간:** 4h
- [ ] 타임아웃 처리
- [ ] 재시도 로직 (exponential backoff)
- [ ] 폴백 전략
- [ ] 서킷 브레이커 패턴

**소계:** 36h

---

## 6. Spring 2 통합 (Spring 2 Integration)

### 6.1 HTTP 클라이언트 구현
**예상 시간:** 5h
- [ ] httpx 클라이언트 설정
- [ ] 요청/응답 모델 정의
- [ ] 기본 에러 처리
- [ ] 재시도 로직 (exponential backoff)
- [ ] 타임아웃 설정

### 6.2 세션 생성 API 호출
**예상 시간:** 4h
- [ ] `POST /api/v1/roleplaying/sessions`
- [ ] 요청 포맷: session_id, user_id, scenario_id
- [ ] 응답 처리 (성공/실패)
- [ ] 에러 메시지 매핑

### 6.3 발화 저장 API 호출
**예상 시간:** 6h
- [ ] `POST /api/v1/roleplaying/sessions/{session_id}/utterances`
- [ ] 사용자 발화 저장
  - [ ] utterance_index
  - [ ] speaker: "user"
  - [ ] text (STT 결과)
  - [ ] s3_url (오디오)
  - [ ] started_at, ended_at
- [ ] AI 응답 저장
  - [ ] speaker: "ai"
  - [ ] text (AI 응답)
- [ ] 배치 저장 최적화

### 6.4 세션 종료 API 호출
**예상 시간:** 3h
- [ ] `PUT /api/v1/roleplaying/sessions/{session_id}/finish`
- [ ] end_reason: user_end, timeout, disconnected, error, turn_limit
- [ ] ended_at 타임스탐프
- [ ] 에러 처리

### 6.5 오디오 업로드 (S3/MinIO)
**예상 시간:** 5h
- [ ] boto3 S3 클라이언트 설정
- [ ] 오디오 파일 생성
- [ ] Spring 2를 통한 S3 업로드 (또는 직접 업로드)
- [ ] URL 생성 및 관리
- [ ] 정리 처리

### 6.6 통신 보안 및 재시도
**예상 시간:** 4h
- [ ] API 요청 서명 (필요시)
- [ ] 타임아웃 설정
- [ ] 재시도 로직 (최대 3회)
- [ ] 데드레터 큐 고려 (선택사항)

**소계:** 27h

---

## 7. API 엔드포인트 (API Endpoints)

### 7.1 기본 엔드포인트
**예상 시간:** 2h
- [ ] `GET /` - 루트 엔드포인트
- [ ] `GET /health/health/ping` - 건강 확인
- [ ] `GET /roleplaying/health/ping` - 롤플레잉 건강 확인

### 7.2 시나리오 생성 API
**예상 시간:** 6h
- [ ] `POST /roleplaying/internal/scenarios/analyze-conversation`
  - [ ] 입력 검증
  - [ ] Slack 메시지 분석
  - [ ] LLM 호출
  - [ ] 시나리오 생성
  - [ ] 고정 질문 생성
  - [ ] 응답 반환

### 7.3 세션 생성 API
**예상 시간:** 6h
- [ ] `POST /roleplaying/sessions`
  - [ ] 요청 검증
  - [ ] DB 조회
  - [ ] Redis 저장
  - [ ] 응답 반환

### 7.4 사용자 정보 API
**예상 시간:** 5h
- [ ] `GET /roleplaying/userInfo`
  - [ ] 인증 검증
  - [ ] 사용자 정보 조회
  - [ ] 통합 상태 반환
- [ ] `GET /roleplaying/userStatics`
  - [ ] 통계 데이터 조회
  - [ ] 순위 계산

### 7.5 롤플레잉 목록 API
**예상 시간:** 6h
- [ ] `GET /roleplaying/roleplayList`
  - [ ] 페이지네이션
  - [ ] 필터링 (status, source_type)
  - [ ] 정렬 (created_at, updated_at)
  - [ ] 날짜 범위 필터

### 7.6 프롬프트 기반 생성 API
**예상 시간:** 7h
- [ ] `POST /roleplaying/prompt_create`
  - [ ] 입력 검증
  - [ ] 턴 플랜 생성
  - [ ] 롤플레잉 저장
  - [ ] 응답 반환

### 7.7 세션 시작/다음 턴 API
**예상 시간:** 8h
- [ ] `POST /roleplaying/{roleplayingId}/session/start`
- [ ] `POST /roleplaying/{sessionId}/nextTurn`
- [ ] `GET /roleplaying/{sessionId}/messages`

### 7.8 OpenAPI 문서화
**예상 시간:** 4h
- [ ] Swagger 통합 확인
- [ ] API 스키마 생성
- [ ] 응답 모델 문서화
- [ ] 예제 추가

**소계:** 44h

---

## 8. 테스트 및 검증 (Testing & Validation)

### 8.1 단위 테스트
**예상 시간:** 20h
- [ ] STT Service 테스트
  - [ ] 오디오 처리
  - [ ] 에러 처리
- [ ] AI Tutor Service 테스트
  - [ ] 프롬프트 생성
  - [ ] 응답 파싱
  - [ ] 컨텍스트 관리
- [ ] Session Manager 테스트
  - [ ] 상태 전이
  - [ ] 턴 관리
- [ ] Repository 테스트
  - [ ] CRUD 연산
  - [ ] 쿼리 검증
- [ ] Spring 2 Client 테스트
  - [ ] API 호출
  - [ ] 에러 처리

### 8.2 통합 테스트
**예상 시간:** 20h
- [ ] WebSocket 연결 → INIT → 첫 질문
- [ ] 오디오 수신 → STT → AI 응답
- [ ] 다중 턴 대화 흐름
- [ ] 발화 저장 → Spring 2 동기화
- [ ] 타임아웃 및 에러 처리
- [ ] 동시 연결 테스트

### 8.3 성능 테스트
**예상 시간:** 8h
- [ ] 동시 연결 부하 테스트 (100+)
- [ ] 메모리 사용량 모니터링
- [ ] CPU 사용량 분석
- [ ] 네트워크 대역폭 측정
- [ ] 응답 시간 측정

### 8.4 보안 테스트
**예상 시간:** 6h
- [ ] SQL Injection 검증
- [ ] WebSocket 취약점 검증
- [ ] 인증/인가 검증
- [ ] 레이트 제한 검증
- [ ] CORS 정책 검증

### 8.5 호환성 테스트
**예상 시간:** 4h
- [ ] 다양한 브라우저 테스트
- [ ] 다양한 오디오 형식 테스트
- [ ] Python 버전 호환성 테스트 (3.11+)

**소계:** 58h

---

## 9. 문서화 및 배포 (Documentation & Deployment)

### 9.1 기술 문서
**예상 시간:** 12h
- [ ] 아키텍처 문서 작성
- [ ] API 엔드포인트 문서화
- [ ] WebSocket 메시지 명세서
- [ ] 데이터베이스 스키마 문서
- [ ] 배포 가이드 작성
- [ ] 트러블슈팅 가이드

### 9.2 코드 문서화
**예상 시간:** 10h
- [ ] Docstring 작성 (모든 함수/클래스)
- [ ] 주석 추가 (복잡한 로직)
- [ ] 타입 힌트 완성
- [ ] 코드 예제 추가

### 9.3 개발자 가이드
**예상 시간:** 6h
- [ ] 환경 설정 가이드
- [ ] 로컬 개발 환경 구축
- [ ] 테스트 실행 방법
- [ ] 디버깅 팁
- [ ] 변수명 및 코드 스타일 가이드

### 9.4 배포 준비
**예상 시간:** 10h
- [ ] Docker 이미지 작성
- [ ] docker-compose 설정
- [ ] 환경별 설정 파일 준비
- [ ] 데이터베이스 마이그레이션 스크립트
- [ ] 배포 체크리스트 작성

### 9.5 배포 및 모니터링
**예상 시간:** 8h
- [ ] 스테이징 배포
- [ ] 프로덕션 배포
- [ ] 모니터링 설정
- [ ] 알림 설정
- [ ] 롤백 계획 수립

### 9.6 사후 관리
**예상 시간:** 4h
- [ ] 배포 후 검증
- [ ] 성능 모니터링
- [ ] 사용자 피드백 수집
- [ ] 버그 수정

**소계:** 50h

---

## 📊 WBS 요약표

| ID | 작업 | 예상 시간 | 상태 |
|----|------|---------|------|
| 1 | 인프라 및 설정 | 17h | 📋 계획 |
| 2 | 데이터베이스 및 모델링 | 21h | 📋 계획 |
| 3 | 세션 및 메시지 처리 | 23h | 📋 계획 |
| 4 | 실시간 통신 | 30h | 📋 계획 |
| 5 | AI 및 외부 서비스 | 36h | 📋 계획 |
| 6 | Spring 2 통합 | 27h | 📋 계획 |
| 7 | API 엔드포인트 | 44h | 📋 계획 |
| 8 | 테스트 및 검증 | 58h | 📋 계획 |
| 9 | 문서화 및 배포 | 50h | 📋 계획 |
| | **총계** | **306h** | |

---

## ⏱️ 예상 일정 (290일 기준 = 6주)

### Week 1-2: 인프라 & 데이터베이스 (38h)
- 작업 1: 인프라 및 설정 (17h)
- 작업 2: 데이터베이스 및 모델링 (21h)

### Week 2-3: 세션 & 메시지 처리 (53h)
- 작업 3: 세션 및 메시지 처리 (23h)
- 작업 4: 실시간 통신 - Part 1 (30h)

### Week 3-4: 실시간 통신 완성 & AI 서비스 (30h+36h=66h)
- 작업 4: 실시간 통신 - Part 2
- 작업 5: AI 및 외부 서비스 (36h)

### Week 4-5: Spring 2 통합 & API (71h)
- 작업 6: Spring 2 통합 (27h)
- 작업 7: API 엔드포인트 (44h)

### Week 5-6: 테스트 & 문서화 (108h)
- 작업 8: 테스트 및 검증 (58h)
- 작업 9: 문서화 및 배포 (50h)

---

## 🎯 마일스톤

| 마일스톤 | 일정 | 산출물 |
|---------|------|--------|
| M1: 기초 구축 완료 | Week 2 | 환경설정, DB 스키마, ORM 모델 |
| M2: WebSocket 기본 | Week 3 | 메시지 처리, 세션 관리 |
| M3: 실시간 회화 | Week 4 | STT, AI, 메시지 흐름 |
| M4: Spring 2 연동 | Week 5 | API 통신, 데이터 동기화 |
| M5: API 완성 | Week 5 | 전체 REST API |
| M6: QA 통과 | Week 6 | 테스트 커버리지 >70% |
| M7: 배포 준비 | Week 6 | 문서, Docker, 모니터링 |

---

## 📌 주요 의존성 및 위험 요소

### 의존성
- Spring 2 API 명세 확정 (필수)
- 데이터베이스 접근 권한 (필수)
- STT/LLM API 키 (필수)
- Redis 서버 (필수)

### 위험 요소
1. **기술적 위험**
   - WebSocket 동시성 이슈 → 조기 부하 테스트
   - STT 성능 → 모델 선택 조기 결정
   - LLM API 비용 → 모니터링 및 제한 설정

2. **일정 위험**
   - Spring 2 API 지연 → 모의 API 준비
   - 테스트 실패 → 조기 단위 테스트
   - 성능 최적화 → 병렬 처리 필요시

3. **운영 위험**
   - 데이터 일관성 → 트랜잭션 관리 강화
   - 보안 취약점 → 보안 감시 (SAST)
   - 모니터링 부족 → 조기 로깅 구축

---

## 🔄 병렬 처리 기회

다음 작업들은 병렬로 수행 가능:

- 작업 1 + 2: 인프라 설정과 DB 모델링 (의존성 낮음)
- 작업 3 + 5: 세션 관리와 AI 서비스 (독립적)
- 작업 7 + 8: API 개발과 테스트 (협력)

---

**문서 작성일:** 2025-11-20
**최종 검토:** -
**배포 예상일:** 2025-12-31