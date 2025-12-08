# SKALA 프로젝트 도메인별 WBS (Work Breakdown Structure)

**문서 버전:** 1.0
**작성일:** 2025-11-20
**범위:** 백엔드 + 프런트엔드 전체 구현 (구현된 것 + 미구현)

---

## 📋 개요

SKALA는 AI 기반 실시간 영어 회화 연습 플랫폼입니다. 다음 2개의 도메인으로 구성됩니다:

1. **Roleplaying Domain** (역할극 도메인) - 핵심 기능
2. **User Domain** (사용자 도메인) - 사용자 관리 및 통계

---

## 1. ROLEPLAYING DOMAIN (역할극 도메인)

### 1.1 시나리오 생성 (Scenario Creation)

#### 백엔드
**상태:** ✅ 부분 완료

- [x] Slack 기반 시나리오 분석
  - [x] `POST /roleplaying/internal/scenarios/analyze-conversation`
  - [x] 메시지 분석 및 LLM 처리
  - [x] 시나리오 + 고정 질문 자동 생성
- [ ] GitHub 기반 시나리오 분석 (미구현)
  - [ ] GitHub Issues/Commits 분석
  - [ ] 기술 토론 시나리오 생성
- [ ] Prompt 기반 시나리오 생성
  - [ ] `POST /roleplaying/prompt_create` (미구현)
  - [ ] AI 역할 + 사용자 역할 + 상황 입력
  - [ ] 턴 플랜 생성

**데이터베이스 모델:**
- [x] Subject 테이블 (대화 주제)
- [x] Scenario 테이블 (구체적 시나리오)
- [ ] ScenarioStep 테이블 (미구현) - 턴별 계획

**Repository 패턴:**
- [ ] ScenarioRepository.find_by_id_and_user_id()
- [ ] ScenarioRepository.find_all_by_user_id()
- [ ] ScenarioRepository.find_all_by_source_type()

**API 엔드포인트:**
- [x] `POST /roleplaying/internal/scenarios/analyze-conversation`
- [ ] `POST /roleplaying/prompt_create` (미구현)
- [ ] `GET /roleplaying/roleplayList` (미구현)

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] Slack 대화 선택 화면
- [ ] GitHub 저장소/이슈 선택 화면
- [ ] 시나리오 미리보기
- [ ] 고정 질문 확인

---

### 1.2 세션 생성 및 관리 (Session Management)

#### 백엔드
**상태:** ⚠️ 진행 중

**세션 생성:**
- [x] `POST /roleplaying/sessions` 엔드포인트
- [x] 요청 검증 (userId, scenarioId)
- [x] DB에서 시나리오 조회
- [x] Redis에 세션 저장 (30분 TTL)
- [x] SessionCreateResponse 반환

**데이터베이스 모델:**
- [ ] Session 테이블 (미구현)
  - [ ] session_id (UUID)
  - [ ] user_id, scenario_id
  - [ ] status (ACTIVE/FINISHED/ERROR)
  - [ ] timestamps (started_at, ended_at)
- [ ] Alembic 마이그레이션 (미구현)

**Redis 세션 저장소:**
- [x] Key format: `session:{session_id}`
- [x] TTL 30분 설정
- [ ] 세션 자동 정리 (미구현)

**Repository 패턴:**
- [ ] SessionRepository.create_session() (미구현)
- [ ] SessionRepository.find_session() (미구현)
- [ ] SessionRepository.update_session_status() (미구현)

**API 엔드포인트:**
- [x] `POST /roleplaying/sessions`

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 세션 시작 화면
- [ ] WebSocket 연결 관리
- [ ] 세션 상태 표시
- [ ] 세션 종료 확인

---

### 1.3 실시간 WebSocket 통신 (Real-time Communication)

#### 백엔드
**상태:** ⚠️ 진행 중

**WebSocket 엔드포인트:**
- [x] `WS /ws/roleplaying/{session_id}` 기본 구조
- [x] 연결 수락 로직
- [x] Redis 세션 검증
- [ ] 메시지 처리 완성 (미구현)

**메시지 처리:**
- [ ] INIT 메시지 처리 (미구현)
  - [ ] 세션 상태 초기화
  - [ ] 첫 AI 질문 생성
  - [ ] ACK 응답
- [ ] UTTERANCE_END 메시지 처리 (미구현)
  - [ ] STT 최종화
  - [ ] Spring 2 발화 저장 요청
  - [ ] UTTERANCE_SAVED 응답
- [ ] USER_TEXT 메시지 처리 (미구현, 테스트용)
  - [ ] 텍스트 검증
  - [ ] 바로 AI 응답 생성
- [ ] END_SESSION 메시지 처리 (미구현)
  - [ ] 세션 종료
  - [ ] 리소스 정리
  - [ ] SESSION_ENDED 응답
- [ ] 오디오 청크 처리 (미구현)
  - [ ] 바이너리 프레임 수신
  - [ ] 버퍼 누적 관리

**세션 상태 관리:**
- [x] SessionManager 클래스 정의
- [ ] 상태 머신 구현 (미구현)
  - [ ] INIT → WAITING → PROCESSING → FINISHED
  - [ ] 상태 전이 검증
- [ ] 턴 카운팅 (미구현)
- [ ] 타이머 관리 (미구현)
  - [ ] 세션 타임아웃 (30분)
  - [ ] INIT 메시지 타임아웃 (30초)
  - [ ] 응답 대기 타임아웃 (60초)

**메시지 모델:**
- [x] 인바운드 메시지 정의
  - [x] InitMessage
  - [x] UtteranceEndMessage
  - [x] UserTextMessage
  - [x] EndSessionMessage
- [x] 아웃바운드 메시지 정의
  - [x] AckMessage
  - [x] AiTextMessage
  - [x] SttPartialMessage
  - [x] SttFinalMessage
  - [x] UtteranceSavedMessage
  - [x] SessionEndedMessage
  - [x] ErrorMessage

**API 엔드포인트:**
- [ ] `WS /ws/roleplaying/{session_id}` (미완성)

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] WebSocket 클라이언트 구현
  - [ ] 연결 로직
  - [ ] 메시지 송수신
  - [ ] 연결 종료 처리
  - [ ] 재연결 로직
- [ ] UI 컴포넌트
  - [ ] 대화 화면
  - [ ] 음성 입력 UI
  - [ ] AI 응답 표시
  - [ ] 상태 표시기

---

### 1.4 음성 처리 (Audio Processing)

#### STT (Speech-to-Text)

**백엔드**
**상태:** ❌ 미구현

- [ ] STT Service 구현
  - [ ] OpenAI Whisper 또는 Google Cloud Speech 선택
  - [ ] 모델 로드 및 캐싱
  - [ ] 오디오 전처리 (샘플링, 정규화)
  - [ ] 음성 인식
  - [ ] 에러 처리
- [ ] 오디오 저장
  - [ ] 임시 파일 관리
  - [ ] Spring 2를 통한 S3 업로드
  - [ ] URL 생성
- [ ] STT 메시지 전송
  - [ ] STT_PARTIAL (부분 결과)
  - [ ] STT_FINAL (최종 결과)
- [ ] 성능 최적화
  - [ ] 모델 캐싱
  - [ ] 배치 처리 검토

**API 엔드포인트:**
- [ ] 내부 STT 엔드포인트 (WebSocket 내)

**프런트엔드**
**상태:** ❌ 미구현

- [ ] 마이크 입력 캡처
  - [ ] Web Audio API
  - [ ] 권한 요청
  - [ ] 녹음 시작/중지
- [ ] 오디오 인코딩
  - [ ] WebM/WAV 포맷
  - [ ] 청크 전송 (버퍼링)
- [ ] STT 결과 표시
  - [ ] 부분 결과
  - [ ] 최종 결과

#### TTS (Text-to-Speech)

**백엔드**
**상태:** ❌ 미구현

- [ ] TTS Service 구현
  - [ ] OpenAI TTS 또는 Google TTS 선택
  - [ ] 텍스트 → 오디오 생성
  - [ ] 오디오 포맷 선택 (MP3, Opus, WAV)
  - [ ] 캐싱 전략
- [ ] 오디오 전송
  - [ ] 스트리밍 또는 전체 다운로드
  - [ ] 청크 단위 전송

**프런트엔드**
**상태:** ❌ 미구현

- [ ] 오디오 재생
  - [ ] HTML5 Audio API
  - [ ] 재생/일시중지/정지
- [ ] 자막 동기화
  - [ ] 타이밍 정보

---

### 1.5 AI 응답 생성 (AI Response Generation)

#### 백엔드
**상태:** ❌ 미구현

**AI Tutor Service:**
- [ ] LLM 클라이언트 구현
  - [ ] OpenAI API 또는 Claude API 또는 Ollama 선택
  - [ ] API 키 관리
  - [ ] 요청/응답 포맷팅
  - [ ] 스트리밍 지원
- [ ] 프롬프트 엔지니어링
  - [ ] 시스템 프롬프트 (역할 정의, 문맥)
  - [ ] 대화 히스토리 포함
  - [ ] 고정 질문 vs 동적 응답 전환
- [ ] 고정 질문 관리
  - [ ] 3개 고정 질문 저장
  - [ ] 턴 1, 5, 10에서 선택
  - [ ] `is_fixed_question` 플래그
- [ ] 동적 응답 생성
  - [ ] 사용자 입력 분석
  - [ ] 컨텍스트 참고
  - [ ] 피드백 포함 (선택사항)
- [ ] 응답 캐싱
- [ ] 에러 처리 및 재시도

**API 엔드포인트:**
- [ ] 내부 AI 응답 생성 (WebSocket 내)

**프런트엔드**
**상태:** ❌ 미구현

- [ ] AI 응답 표시
  - [ ] 타이핑 효과
  - [ ] 점진적 표시
- [ ] 피드백 표시
  - [ ] 발음 평가
  - [ ] 문법 오류
  - [ ] 제안사항

---

### 1.6 Spring 2 통합 (Spring 2 Integration)

#### 백엔드
**상태:** ❌ 미구현

**Spring 2 클라이언트:**
- [ ] httpx 기반 HTTP 클라이언트 설정
  - [ ] 기본 URL 설정
  - [ ] 타임아웃 설정
  - [ ] SSL 검증
- [ ] 요청/응답 모델 정의
- [ ] 기본 에러 처리
- [ ] 재시도 로직 (exponential backoff)

**세션 생성 API:**
- [ ] `POST /api/v1/roleplaying/sessions`
  - [ ] 요청: session_id, user_id, scenario_id
  - [ ] 응답 처리
  - [ ] 에러 처리

**발화 저장 API:**
- [ ] `POST /api/v1/roleplaying/sessions/{session_id}/utterances`
  - [ ] 사용자 발화 저장
    - [ ] utterance_index
    - [ ] speaker: "user"
    - [ ] text (STT 결과)
    - [ ] s3_url (오디오)
    - [ ] timestamps
  - [ ] AI 응답 저장
    - [ ] speaker: "ai"
    - [ ] text (AI 응답)
  - [ ] 배치 저장 최적화

**세션 종료 API:**
- [ ] `PUT /api/v1/roleplaying/sessions/{session_id}/finish`
  - [ ] end_reason: user_end, timeout, disconnected, error, turn_limit
  - [ ] ended_at 타임스탐프

**오디오 업로드:**
- [ ] S3/MinIO 업로드
  - [ ] boto3 클라이언트 설정
  - [ ] 파일 생성 및 업로드
  - [ ] URL 관리
  - [ ] 정리 처리

**API 엔드포인트:**
- [ ] Spring 2 통신 (내부)

---

### 1.7 롤플레잉 관련 API 엔드포인트

#### 백엔드
**상태:** ⚠️ 진행 중

**구현된 엔드포인트:**
- [x] `POST /roleplaying/sessions`
- [x] `POST /roleplaying/internal/scenarios/analyze-conversation`

**미구현 엔드포인트:**
- [ ] `GET /roleplaying/roleplayList`
  - [ ] 사용자의 모든 롤플레잉 조회
  - [ ] 페이지네이션 (page, size)
  - [ ] 필터링 (status, source_type)
  - [ ] 정렬 (created_at, updated_at)
  - [ ] 날짜 범위 필터
- [ ] `POST /roleplaying/prompt_create`
  - [ ] 프롬프트 기반 롤플레잉 생성
  - [ ] 턴 플랜 생성
- [ ] `POST /roleplaying/{roleplayingId}/session/start`
  - [ ] 기존 롤플레잉으로 세션 시작
  - [ ] 첫 AI 질문 생성
- [ ] `POST /roleplaying/{sessionId}/nextTurn`
  - [ ] 사용자 메시지 저장
  - [ ] AI 응답 생성
- [ ] `GET /roleplaying/{sessionId}/messages`
  - [ ] 대화 히스토리 조회
  - [ ] 페이지네이션

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 롤플레잉 목록 화면
  - [ ] 스크롤/페이지네이션
  - [ ] 필터링 UI
  - [ ] 정렬 옵션
  - [ ] 아이템 디테일
- [ ] 세션 시작 화면
- [ ] 대화 히스토리 조회

---

## 2. USER DOMAIN (사용자 도메인)

### 2.1 사용자 정보 관리 (User Profile)

#### 백엔드
**상태:** ❌ 미구현

**데이터베이스 모델:**
- [ ] User 확장 필드 (Spring 2 연동)
- [ ] UserProfile 테이블

**API 엔드포인트:**
- [ ] `GET /roleplaying/userInfo`
  - [ ] 사용자 기본 정보
  - [ ] 통합 상태 (Spring 2)
  - [ ] 설정 정보
- [ ] `PUT /roleplaying/userInfo` (선택사항)
  - [ ] 프로필 수정
  - [ ] 설정 업데이트

**비즈니스 로직:**
- [ ] 사용자 정보 조회
- [ ] 팀 정보 조회

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 프로필 조회 화면
- [ ] 프로필 수정 화면
- [ ] 설정 화면

---

### 2.2 사용자 통계 및 분석

#### 백엔드
**상태:** ❌ 미구현

**API 엔드포인트:**
- [ ] `GET /roleplaying/userStatics`
  - [ ] 총 대화 시간
  - [ ] 완료한 세션 수
  - [ ] 사용한 시나리오 수
  - [ ] 정확도/발음 점수
  - [ ] 순위 정보
  - [ ] 팀 정보
  - [ ] 주간/월간 통계

**비즈니스 로직:**
- [ ] 통계 계산 (캐싱 포함)
- [ ] 순위 계산
- [ ] 추세 분석
- [ ] 비교 분석

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 통계 대시보드
- [ ] 그래프/차트
- [ ] 순위 표시
- [ ] 개인 목표 설정

---

### 3.3 북마크 및 저장 (Bookmarks)

#### 백엔드
**상태:** ❌ 미구현

**데이터베이스 모델:**
- [ ] Bookmark 테이블
  - [ ] user_id, scenario_id
  - [ ] created_at

**API 엔드포인트:**
- [ ] `POST /roleplaying/{scenarioId}/bookmark`
- [ ] `DELETE /roleplaying/{scenarioId}/bookmark`
- [ ] `GET /roleplaying/bookmarks`
  - [ ] 북마크 목록 조회
  - [ ] 페이지네이션

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 북마크 버튼
- [ ] 북마크 목록 화면
- [ ] 북마크 관리

---

### 3.4 순위 및 경쟁 (Leaderboard)

#### 백엔드
**상태:** ❌ 미구현

**API 엔드포인트:**
- [ ] `GET /roleplaying/leaderboard`
  - [ ] 전체 순위
  - [ ] 팀별 순위
  - [ ] 주간/월간 순위
- [ ] `GET /roleplaying/rankings`
  - [ ] 더 상세한 순위 정보

**비즈니스 로직:**
- [ ] 순위 계산
- [ ] 포인트 시스템
- [ ] 배지/업적 시스템

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 순위 화면
- [ ] 개인 순위 표시
- [ ] 팀 순위 표시
- [ ] 배지/업적 표시

---

### 3.5 GitHub/Slack 통합

#### 백엔드
**상태:** ❌ 미구현

**GitHub 통합:**
- [ ] GitHub OAuth 연동
- [ ] 저장소/이슈 조회
- [ ] 커밋/PR 분석
- [ ] 토론 추출

**Slack 통합:**
- [ ] Slack OAuth 연동
- [ ] 채널 메시지 조회
- [ ] 스레드 분석
- [ ] 워크스페이스/팀 정보

**API 엔드포인트:**
- [ ] `POST /integration/github/connect`
- [ ] `POST /integration/slack/connect`
- [ ] `GET /integration/status`
- [ ] `DELETE /integration/{platform}/disconnect`

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] OAuth 연결 화면
- [ ] 저장소/채널 선택 UI
- [ ] 통합 상태 표시
- [ ] 연결 해제 UI

---

## 4. 공통 인프라 & 지원 기능

### 4.1 인프라 및 설정

#### 백엔드
**상태:** ⚠️ 부분 완료

- [x] FastAPI 기본 설정
- [x] 환경 설정 관리 (app/config.py)
- [x] 데이터베이스 연결 설정
- [x] 로깅 시스템
- [x] 예외 처리
- [x] Redis 클라이언트
- [ ] CORS 설정 확장 (미구현)
- [ ] 레이트 제한 설정 (미구현)
- [ ] 타임아웃 설정 확장 (미구현)

**마이그레이션:**
- [ ] Alembic 마이그레이션 파일
  - [ ] sessions 테이블
  - [ ] utterances 테이블
  - [ ] 기타 필요한 테이블

---

### 4.2 API 문서화

#### 백엔드
**상태:** ⚠️ 진행 중

- [x] OpenAPI YAML 파일 (roleplaying_openapi.yaml)
- [ ] Swagger UI 통합
- [ ] 스키마 완성
- [ ] 예제 추가

---

### 4.3 테스트

#### 백엔드
**상태:** ❌ 미구현

**단위 테스트:**
- [ ] STT Service 테스트
- [ ] AI Tutor Service 테스트
- [ ] Session Manager 테스트
- [ ] Repository 테스트
- [ ] Spring 2 Client 테스트

**통합 테스트:**
- [ ] WebSocket 엔드투엔드 테스트
- [ ] API 통합 테스트
- [ ] 데이터베이스 마이그레이션 테스트

**성능 테스트:**
- [ ] 동시 연결 부하 테스트
- [ ] 메모리 프로파일링
- [ ] 응답 시간 측정

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 컴포넌트 단위 테스트
- [ ] WebSocket 클라이언트 테스트
- [ ] UI 통합 테스트
- [ ] E2E 테스트

---

### 4.4 배포 및 운영

#### 백엔드
**상태:** ❌ 미구현

- [ ] Docker 이미지 생성
- [ ] docker-compose 설정
- [ ] Kubernetes 매니페스트 (선택사항)
- [ ] CI/CD 파이프라인
- [ ] 환경별 설정 (dev/staging/prod)
- [ ] 모니터링 설정
- [ ] 로그 수집 설정

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 빌드 설정
- [ ] 번들 최적화
- [ ] CI/CD 파이프라인
- [ ] 배포 스크립트
- [ ] 모니터링

---

## 📊 도메인별 구현 현황 요약

| 도메인 | 영역 | 백엔드 상태 | 프런트엔드 상태 | 우선순위 |
|--------|------|-----------|--------------|---------|
| Roleplaying | 시나리오 생성 | ✅ 부분 | ❌ 미구현 | 🔴 높음 |
| Roleplaying | 세션 관리 | ⚠️ 진행중 | ❌ 미구현 | 🔴 높음 |
| Roleplaying | WebSocket | ⚠️ 진행중 | ❌ 미구현 | 🔴 높음 |
| Roleplaying | STT/TTS | ❌ 미구현 | ❌ 미구현 | 🔴 높음 |
| Roleplaying | AI 응답 | ❌ 미구현 | ❌ 미구현 | 🔴 높음 |
| Roleplaying | Spring 2 통합 | ❌ 미구현 | - | 🔴 높음 |
| Roleplaying | API 엔드포인트 | ⚠️ 부분 | ❌ 미구현 | 🟡 중간 |
| User | 사용자 정보 | ❌ 미구현 | ❌ 미구현 | 🟢 낮음 |
| User | 통계/분석 | ❌ 미구현 | ❌ 미구현 | 🟢 낮음 |
| User | 북마크 | ❌ 미구현 | ❌ 미구현 | 🟢 낮음 |
| User | 순위 | ❌ 미구현 | ❌ 미구현 | 🟢 낮음 |
| User | 통합 | ❌ 미구현 | ❌ 미구현 | 🟢 낮음 |
| 공통 | 인프라 | ⚠️ 부분 | ❌ 미구현 | 🔴 높음 |
| 공통 | 문서화 | ⚠️ 진행중 | ❌ 미구현 | 🟡 중간 |
| 공통 | 테스트 | ❌ 미구현 | ❌ 미구현 | 🟡 중간 |
| 공통 | 배포 | ❌ 미구현 | ❌ 미구현 | 🟡 중간 |

---

## 🎯 구현 로드맵

### Phase 1: Roleplaying Core (핵심 기능) - **우선순위 높음**

**목표:** 기본 롤플레잉 회화 기능 완성

**포함 영역:**
- ✅ 시나리오 생성 (Slack 분석)
- ⚠️ 세션 생성 및 관리
- ⚠️ WebSocket 통신 (메시지 처리)
- ❌ STT/TTS 처리
- ❌ AI 응답 생성
- ❌ Spring 2 통합
- ❌ 프런트엔드 UI 구현

**예상 시간:** 140-170시간

**마일스톤:**
- M1.1: WebSocket 메시지 처리 완성 (20시간)
- M1.2: STT/AI 통합 (30시간)
- M1.3: Spring 2 통합 (27시간)
- M1.4: 프런트엔드 기본 UI (40시간)
- M1.5: 통합 테스트 & 디버깅 (30시간)

---

### Phase 2: Roleplaying 확장 (추가 API) - **우선순위 중간**

**목표:** 추가 API 엔드포인트 완성

**포함 영역:**
- [ ] `GET /roleplaying/roleplayList`
- [ ] `POST /roleplaying/prompt_create`
- [ ] 사용자 통계 API
- [ ] GitHub 기반 시나리오
- [ ] 프런트엔드 확장

**예상 시간:** 80시간

---

### Phase 3: User 도메인 - **우선순위 낮음**

**목표:** 사용자 관리 기능

**포함 영역:**
- [ ] User 프로필 및 통계
- [ ] 북마크, 순위, 통합

**예상 시간:** 80시간

---

### Phase 4: 최적화 & 배포 - **우선순위 중간**

**목표:** 성능 최적화 및 프로덕션 배포

**포함 영역:**
- [ ] 성능 테스트 & 최적화
- [ ] Docker & Kubernetes
- [ ] CI/CD 파이프라인
- [ ] 모니터링 설정

**예상 시간:** 60시간

---

## 📌 주요 의존성

### 필수
- Spring 2 API 명세 확정
- 데이터베이스 접근 권한
- STT/LLM API 키
- Redis 서버

### 선택사항
- GitHub/Slack OAuth
- S3/MinIO 서버
- Kubernetes 클러스터

---

## 🚀 빠른 시작 가이드

### 1단계: Phase 1 시작 (가장 중요)
1. WebSocket 메시지 처리 완성
2. STT 서비스 통합
3. AI Tutor 서비스 통합
4. Spring 2 연동
5. 기본 프런트엔드 UI

### 2단계: Phase 2 진행
1. 추가 API 개발
2. GitHub 통합
3. 프런트엔드 확장

### 3단계: Phase 3 & 4
1. 교재/사용자 도메인
2. 최적화 및 배포

---

**문서 최종 업데이트:** 2025-11-20
**다음 검토일:** 2025-12-04
