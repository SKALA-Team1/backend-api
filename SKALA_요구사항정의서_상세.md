# SKALA 프로젝트 요구사항 정의서

**프로젝트명**: SKALA - AI 기반 IT 영어 회화 학습 플랫폼
**버전**: 1.0
**작성일**: 2025-12-16
**고객사명**: SKALA Team

---

## 목차
1. [사용자 관리](#1-사용자-관리)
2. [인증 및 인가](#2-인증-및-인가)
3. [시나리오 관리](#3-시나리오-관리)
4. [롤플레잉 세션](#4-롤플레잉-세션)
5. [실시간 음성 대화](#5-실시간-음성-대화)
6. [피드백 및 평가](#6-피드백-및-평가)
7. [IT 용어 학습](#7-it-용어-학습)
8. [통합 (Slack/GitHub)](#8-통합-슬랙github)
9. [마이페이지](#9-마이페이지)
10. [북마크 관리](#10-북마크-관리)

---

## 시스템 아키텍처 개요

### 전체 구성
```
클라이언트 (React)
    ↓
Spring 1 Gateway (Port 8080) - JWT 인증, 라우팅
    ↓
┌───────────────┬─────────────────┐
Spring 2 (8081)  FastAPI (8082)
  (CRUD/Biz)       (AI/WebSocket)
    ↓                   ↓
  MySQL          Redis (세션 캐시)
```

### 주요 기술 스택
- **Frontend**: React 18, Material-UI, Three.js, WebSocket
- **Backend Gateway**: Spring Boot 3.5.7, Java 17, JWT
- **Backend CRUD**: Spring Boot 3.5.7, JPA, MySQL
- **Backend AI**: FastAPI, Python 3.11, OpenAI GPT-4, Deepgram STT, Azure Speech
- **Database**: MySQL 8.0
- **Cache**: Redis

---

## 데이터베이스 스키마 전체 목록

### 1. user (사용자)
- `user_id` BIGINT PK AUTO_INCREMENT
- `email` VARCHAR(255) UNIQUE NOT NULL
- `name` VARCHAR(100) NOT NULL
- `profile_image_url` VARCHAR(512)
- `auth_provider` VARCHAR(50) NOT NULL (LOCAL/GOOGLE)
- `provider_user_id` VARCHAR(255)
- `job_role` VARCHAR(100)
- `team_name` VARCHAR(100)
- `password_hash` VARCHAR(255) (BCrypt, LOCAL만)
- `refresh_token` TEXT
- `refresh_token_expires_at` DATETIME
- `email_verified` BOOLEAN DEFAULT FALSE
- `terms_agreed` BOOLEAN
- `watch_device_token` VARCHAR(255)
- `created_at` DATETIME
- `updated_at` DATETIME

### 2. user_settings (사용자 설정)
- `user_id` BIGINT PK FK
- `watch_notification_enabled` BOOLEAN DEFAULT FALSE
- `watch_notification_time` VARCHAR(5) (HH:MM)
- `watch_notification_timezone` VARCHAR(50)
- `last_watch_notification_sent_at` DATETIME
- `created_at` DATETIME
- `updated_at` DATETIME

### 3. email_verification (이메일 인증)
- `email` VARCHAR(255) PK
- `code` VARCHAR(255) NOT NULL (6자리 숫자)
- `expires_at` DATETIME NOT NULL
- `created_at` DATETIME

### 4. subject (시나리오 주제)
- `subject_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `creation_type` ENUM('PROMPT', 'SLACK', 'GITHUB') NOT NULL
- `creation_type_detail` VARCHAR(100)
- `conversation_date` DATE
- `message_count` INT
- `my_role` TEXT
- `situation` TEXT
- `created_at` DATETIME
- `updated_at` DATETIME

### 5. scenario (시나리오)
- `scenario_id` BIGINT PK AUTO_INCREMENT
- `subject_id` BIGINT FK NOT NULL
- `user_id` BIGINT FK NOT NULL
- `ai_role` VARCHAR(100)
- `topic_type` ENUM('OVERVIEW', 'DETAIL', 'DIRECT')
- `fixed_questions` TEXT (JSON 배열)
- `title` VARCHAR(80) NOT NULL
- `status` ENUM('DRAFT', 'GENERATED', 'READY', 'ARCHIVED') DEFAULT 'DRAFT'
- `created_at` DATETIME
- `updated_at` DATETIME

### 6. scenario_session (롤플레잉 세션)
- `session_id` VARCHAR(36) PK (UUID)
- `scenario_id` BIGINT FK NOT NULL
- `user_id` BIGINT FK NOT NULL
- `status` VARCHAR(30) NOT NULL (IN_PROGRESS/FINISHED)
- `total_turns_planned` INT NOT NULL (기본 7)
- `played_turns` INT DEFAULT 0
- `completed_all_turns` BOOLEAN DEFAULT FALSE
- `finish_reason` VARCHAR(50)
- `interaction_mode` VARCHAR(20) DEFAULT 'default'
- `created_at` DATETIME
- `updated_at` DATETIME
- `finished_at` DATETIME

### 7. scenario_message (발화 메시지)
- `message_id` BIGINT PK AUTO_INCREMENT
- `session_id` VARCHAR(36) FK NOT NULL
- `turn_index` INT NOT NULL
- `speaker` VARCHAR(30) NOT NULL (user/ai)
- `message_text` TEXT NOT NULL
- `audio_url` TEXT (S3 URL, 사용자만)
- `started_at` DATETIME
- `ended_at` DATETIME
- `created_at` DATETIME
- **평가 점수 (사용자 발화만)**:
  - `pronunciation_score` INT (0-100)
  - `grammar_score` INT (0-100)
  - `relevance_score` INT (0-100)
  - `overall_score` INT
  - `needs_correction` BOOLEAN
  - `retry_count` INT
  - `primary_issue` VARCHAR(50)
- **AI 질문 필드 (AI 발화만)**:
  - `question_ko` TEXT (한글 질문)
  - `recommended_keywords` JSON (추천 키워드 배열)
- **피드백 상세**:
  - `feedback_sections` JSON (양방향 피드백)
- INDEX: `idx_scenario_message_session_turn (session_id, turn_index)`

### 8. scenario_feedback (종합 피드백)
- `feedback_id` BIGINT PK AUTO_INCREMENT
- `session_id` VARCHAR(36) FK NOT NULL
- `scenario_id` BIGINT FK NOT NULL
- `avg_pronunciation` DECIMAL(5,2)
- `avg_grammar` DECIMAL(5,2)
- `avg_relevance` DECIMAL(5,2)
- `final_feedback_short` TEXT (200자)
- `final_feedback_long` TEXT (600자)
- `created_at` DATETIME

### 9. scenario_reference (시나리오 참조 문서 연결)
- **Composite PK**: (`scenario_id`, `reference_id`)
- `scenario_id` BIGINT FK NOT NULL → scenario.scenario_id
- `reference_id` BIGINT FK NOT NULL → reference.reference_id
- `created_at` DATETIME
- **설명**: 시나리오와 참조 문서 간의 다대다 관계를 나타내는 연결 테이블

### 10. github_issue (GitHub 이슈)
- `github_issue_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `repo_owner` VARCHAR(100) NOT NULL (예: "facebook")
- `repo_name` VARCHAR(200) NOT NULL (예: "react")
- `issue_number` INT NOT NULL (이슈 번호)
- `title` VARCHAR(255) NOT NULL
- `body` TEXT (이슈 본문)
- `state` VARCHAR(30) (open/closed)
- `external_created_at` DATETIME (GitHub 이슈 생성 시간)
- `external_updated_at` DATETIME (GitHub 이슈 수정 시간)
- `closed_at` DATETIME (이슈 종료 시간)
- `created_at` DATETIME
- `updated_at` DATETIME
- **UNIQUE**: `uk_github_issue_repo_number (repo_owner, repo_name, issue_number)`

### 11. reference (참조 문서)
- `reference_id` BIGINT PK AUTO_INCREMENT
- `document` TEXT NOT NULL (문서 내용)
- `created_at` DATETIME

### 12. slack_message (Slack 메시지)
- `slack_message_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `message_ts` DATETIME NOT NULL
- `sender_name` VARCHAR(100)
- `text` TEXT NOT NULL
- `created_at` DATETIME
- INDEX: `idx_slack_message_user_date (user_id, message_ts)`

### 13. integration (외부 통합)
- `integration_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `provider` VARCHAR(50) NOT NULL (slack/github)
- `access_token` TEXT
- `selected_channel_id` VARCHAR(50)
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` DATETIME
- `updated_at` DATETIME

### 14. user_bookmarks (북마크)
- `id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT NOT NULL
- `message_id` BIGINT FK NOT NULL (scenario_message)
- `created_at` DATETIME

### 15. it_question (IT 질문)
- `question_id` BIGINT PK AUTO_INCREMENT
- `question_text` VARCHAR(500) NOT NULL (영어)
- `question_text_ko` VARCHAR(500) (한글)
- `category` VARCHAR(50) (Architecture/Database/DevOps/Security)
- `difficulty` ENUM('EASY', 'MEDIUM', 'HARD')
- `key_keywords` JSON (핵심 키워드 배열)
- `model_answer` TEXT (모범 답안)
- `created_at` DATETIME
- `updated_at` DATETIME

### 16. it_practice_session (IT 연습 세션)
- `session_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `question_id` BIGINT FK NOT NULL
- `user_answer` TEXT (사용자 답변 텍스트)
- `audio_url` VARCHAR(500) (S3 오디오 파일 URL, 음성 입력 시)
- **평가 점수**:
  - `clarity_score` INT (0-100, 명확성 점수)
  - `technical_accuracy_score` INT (0-100, 기술적 정확성 점수)
  - `terminology_score` INT (0-100, 전문용어 사용 점수)
  - `overall_score` INT (0-100, 종합 점수)
- `feedback` TEXT (LLM 생성 평가 피드백)
- `session_type` ENUM('TEXT', 'VOICE') DEFAULT 'TEXT'
- `completed_at` DATETIME (평가 완료 시간)
- `created_at` DATETIME

### 17. it_chatbot_conversation (IT 챗봇 대화)
- `conversation_id` BIGINT PK AUTO_INCREMENT
- `user_id` BIGINT FK NOT NULL
- `user_message` TEXT NOT NULL (사용자 질문/메시지)
- `bot_response` TEXT NOT NULL (챗봇 응답)
- `context` JSON (이전 대화 히스토리, 최근 5턴)
- `created_at` DATETIME

---

## 1. 사용자 관리

### 1.1 회원가입

#### 1.1.1 이메일 인증 코드 발송

**소분류 요구사항 명**: 이메일 인증 코드 발송 및 검증

**요구사항 설명**:

[요구사항]
- 사용자가 이메일 주소를 입력하면 6자리 숫자 인증 코드를 발송해야 함
- 인증 코드는 5분간 유효하며, 중복 발송 시 기존 코드를 덮어씀
- Gmail SMTP를 통해 이메일 전송

[대상업무]
- **backend-gateway**: POST /auth/email/send-code
- **backend-crud2**: POST /internal/auth/email/send-code
- **frontend-web**: SignUpPage > SendEmailCodeForm

[요건처리 상세]
1. 사용자가 email 입력
2. Spring Gateway에서 @Valid 검증 (이메일 형식)
3. Spring 2로 이메일 인증 코드 발송 요청
4. Spring 2의 EmailService가:
   - email_verification 테이블 조회 (기존 코드 확인)
   - 6자리 랜덤 숫자 생성 (예: "123456")
   - email_verification 테이블에 UPSERT (email=PK, code, expires_at=현재+5분)
   - Gmail SMTP로 이메일 발송
5. 클라이언트에 "인증 코드가 발송되었습니다" 응답

**관련 필드**:
- `email_verification.email` VARCHAR(255) PK
- `email_verification.code` VARCHAR(255) NOT NULL
- `email_verification.expires_at` DATETIME NOT NULL
- `email_verification.created_at` DATETIME

---

#### 1.1.2 이메일 인증 코드 검증

**소분류 요구사항 명**: 이메일 인증 코드 검증

**요구사항 설명**:

[요구사항]
- 사용자가 입력한 인증 코드가 올바른지 검증해야 함
- 만료된 코드는 거부

[대상업무]
- **backend-gateway**: POST /auth/email/verify-code
- **backend-crud2**: POST /internal/auth/email/verify-code
- **frontend-web**: SignUpPage > VerifyEmailCodeForm

[요건처리 상세]
1. 사용자가 email, code 입력
2. Spring 2가 email_verification 테이블 조회
3. code 일치 여부 확인
4. expires_at < 현재시각이면 "만료됨" 오류 반환
5. 검증 성공 시 "인증 코드가 확인되었습니다" 응답

**관련 필드**:
- `email_verification.email`
- `email_verification.code`
- `email_verification.expires_at`

---

#### 1.1.3 회원가입 처리

**소분류 요구사항 명**: 이메일 기반 회원가입 및 JWT 토큰 발급

**요구사항 설명**:

[요구사항]
- 사용자가 이메일 인증 후 회원가입을 완료하고 JWT 토큰을 발급받아야 함
- 비밀번호는 BCrypt로 암호화하여 저장
- 약관 동의 필수

[대상업무]
- **backend-gateway**: POST /auth/signup
- **backend-crud2**: POST /internal/users
- **frontend-web**: SignUpPage

[요건처리 상세]
1. 사용자가 email, password, name, job_role, terms_agreed 입력
2. Spring Gateway에서 @Valid 검증:
   - 이메일 형식
   - 비밀번호 8자 이상
   - terms_agreed=true
3. Spring 2로 회원가입 요청
4. Spring 2가:
   - user 테이블에 이메일 중복 확인
   - password를 BCrypt 해싱
   - user 테이블에 INSERT:
     - auth_provider="LOCAL"
     - email_verified=true
     - password_hash=(해시값)
5. Spring Gateway가 JWT Access Token (만료 30분) + Refresh Token (만료 7일) 발급
6. user 테이블에 refresh_token, refresh_token_expires_at 업데이트
7. 클라이언트에 {accessToken, refreshToken, expiresIn} 반환

**관련 필드**:
- `user.email` VARCHAR(255) UNIQUE NOT NULL
- `user.password_hash` VARCHAR(255)
- `user.name` VARCHAR(100)
- `user.job_role` VARCHAR(100)
- `user.auth_provider` VARCHAR(50) = "LOCAL"
- `user.email_verified` BOOLEAN = TRUE
- `user.terms_agreed` BOOLEAN
- `user.refresh_token` TEXT
- `user.refresh_token_expires_at` DATETIME

---

### 1.2 로그인

#### 1.2.1 이메일/비밀번호 로그인

**소분류 요구사항 명**: 이메일/비밀번호 로그인 및 JWT 발급

**요구사항 설명**:

[요구사항]
- 사용자가 이메일과 비밀번호로 로그인하고 JWT 토큰을 발급받아야 함

[대상업무]
- **backend-gateway**: POST /auth/login
- **backend-crud2**: POST /internal/auth/login
- **frontend-web**: LoginPage

[요건처리 상세]
1. 사용자가 email, password 입력
2. Spring Gateway가 Spring 2로 로그인 요청
3. Spring 2가:
   - user 테이블에서 email 조회
   - password_hash와 BCrypt.matches(password, password_hash) 검증
   - 검증 실패 시 401 Unauthorized
4. 검증 성공 시 Spring Gateway가:
   - JWT Access Token (Claims: userId, role, exp) 발급
   - JWT Refresh Token 발급
5. user 테이블에 refresh_token, refresh_token_expires_at 업데이트
6. 클라이언트에 {accessToken, refreshToken, expiresIn} 반환

**관련 필드**:
- `user.email`
- `user.password_hash`
- `user.user_id` (JWT subject)
- `user.refresh_token`

---

#### 1.2.2 Google OAuth 로그인

**소분류 요구사항 명**: Google OAuth 2.0 소셜 로그인

**요구사항 설명**:

[요구사항]
- 사용자가 Google 계정으로 간편 로그인할 수 있어야 함
- 최초 로그인 시 자동 회원가입

[대상업무]
- **backend-gateway**: GET /auth/google, GET /auth/google/callback
- **backend-crud2**: POST /internal/users (신규 사용자 생성)
- **frontend-web**: GoogleLoginButton

[요건처리 상세]
1. 사용자가 "Google로 로그인" 클릭
2. Spring Gateway가 Google OAuth 인증 페이지로 리다이렉트
3. Google에서 사용자 로그인 및 권한 승인
4. Google이 authorization code를 callback URL로 전달
5. Spring Gateway가:
   - authorization code로 Google Access Token 교환
   - Google User Info API 호출 → email, name, profile_image_url 획득
6. Spring 2가 user 테이블 조회:
   - 기존 사용자(email 일치): 로그인 처리
   - 신규 사용자: INSERT (auth_provider="GOOGLE", provider_user_id=Google user ID)
7. JWT 토큰 발급 및 반환

**관련 필드**:
- `user.auth_provider` VARCHAR(50) = "GOOGLE"
- `user.provider_user_id` VARCHAR(255)
- `user.email`
- `user.name`
- `user.profile_image_url` VARCHAR(512)

---

#### 1.2.3 토큰 갱신

**소분류 요구사항 명**: Refresh Token으로 Access Token 갱신

**요구사항 설명**:

[요구사항]
- Access Token 만료 시 Refresh Token으로 새 Access Token을 발급받을 수 있어야 함

[대상업무]
- **backend-gateway**: POST /auth/refresh
- **frontend-web**: httpClient (자동 갱신)

[요건처리 상세]
1. 클라이언트가 {refreshToken} 전송
2. Spring Gateway가 Refresh Token 검증:
   - JWT 서명 확인
   - exp 확인
3. Spring 2에서 user 테이블 조회 (userId로):
   - refresh_token 일치 확인
   - refresh_token_expires_at 확인
4. 검증 성공 시 새 Access Token 발급
5. {accessToken, expiresIn} 반환

**관련 필드**:
- `user.refresh_token`
- `user.refresh_token_expires_at`

---

### 1.3 사용자 정보 관리

#### 1.3.1 사용자 프로필 조회

**소분류 요구사항 명**: 현재 사용자 정보 조회

**요구사항 설명**:

[요구사항]
- 로그인한 사용자가 자신의 프로필 정보를 조회할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /user/me
- **backend-crud2**: GET /internal/users/{user_id}
- **frontend-web**: UserPage > ProfileSummary

[요건처리 상세]
1. 클라이언트가 JWT 토큰과 함께 요청
2. Spring Gateway가 JWT에서 userId 추출
3. Spring 2가 user 테이블 조회
4. {userId, email, name, profileImageUrl, jobRole, teamName, createdAt} 반환

**관련 필드**:
- `user.user_id`
- `user.email`
- `user.name`
- `user.profile_image_url`
- `user.job_role`
- `user.team_name`
- `user.created_at`

---

#### 1.3.2 사용자 프로필 수정

**소분류 요구사항 명**: 사용자 프로필 수정

**요구사항 설명**:

[요구사항]
- 사용자가 자신의 이름, 직무, 팀명, 프로필 이미지를 수정할 수 있어야 함

[대상업무]
- **backend-gateway**: PATCH /user/profile
- **backend-crud2**: PATCH /internal/users/{user_id}
- **frontend-web**: UserPage > ProfileEditForm

[요건처리 상세]
1. 사용자가 name, job_role, team_name, profile_image_url 입력
2. Spring Gateway가 JWT에서 userId 추출
3. Spring 2가 user 테이블 UPDATE
4. 수정된 프로필 정보 반환

**관련 필드**:
- `user.name`
- `user.job_role`
- `user.team_name`
- `user.profile_image_url`
- `user.updated_at`

---

#### 1.3.3 Apple Watch 알림 설정

**소분류 요구사항 명**: Apple Watch 알림 시간 설정

**요구사항 설명**:

[요구사항]
- 사용자가 Apple Watch 알림을 활성화하고 시간을 설정할 수 있어야 함

[대상업무]
- **backend-crud2**: POST /internal/users/{user_id}/watch-settings
- **frontend-web**: UserPage > WatchSettingsForm

[요건처리 상세]
1. 사용자가 watch_notification_enabled, watch_notification_time, watch_notification_timezone 입력
2. Spring 2가 user_settings 테이블 UPSERT
3. 설정 완료 응답

**관련 필드**:
- `user_settings.user_id` (PK)
- `user_settings.watch_notification_enabled` BOOLEAN
- `user_settings.watch_notification_time` VARCHAR(5) (HH:MM)
- `user_settings.watch_notification_timezone` VARCHAR(50)

---

## 2. 인증 및 인가

### 2.1 JWT 인증 필터

**소분류 요구사항 명**: JWT 토큰 검증 및 SecurityContext 설정

**요구사항 설명**:

[요구사항]
- 모든 보호된 API 요청 시 JWT 토큰을 검증하고 사용자 ID를 추출해야 함

[대상업무]
- **backend-gateway**: JwtAuthenticationFilter

[요건처리 상세]
1. 클라이언트가 Authorization: Bearer {token} 헤더 전송
2. JwtAuthenticationFilter가:
   - JWT 서명 검증
   - exp 확인
   - Claims에서 userId, role 추출
3. SecurityContext에 Authentication 객체 저장 (principal=userId)
4. 컨트롤러에서 SecurityContextHolder.getContext().getAuthentication() 사용

**인증 제외 경로**:
- /auth/signup
- /auth/login
- /auth/refresh
- /auth/email/*
- /auth/google/*
- /swagger-ui/*
- /actuator/*

---

## 3. 시나리오 관리

### 3.1 Slack 기반 시나리오 생성

#### 3.1.1 Slack 대화 분석 및 시나리오 생성

**소분류 요구사항 명**: Slack 메시지 분석 및 4개 시나리오 자동 생성

**요구사항 설명**:

[요구사항]
- 사용자가 Slack 채널의 대화 내역을 제공하면 LLM이 분석하여 4개의 롤플레잉 시나리오를 생성해야 함
- Overview 시나리오 1개 + AI 역할별 Detail 시나리오 3개
- 각 시나리오마다 3개의 고정 질문 포함

[대상업무]
- **backend-api**: POST /internal/scenarios/analyze-conversation
- **backend-crud2**: POST /internal/scenarios/slack/analyze-and-save
- **frontend-web**: SlackScenarioPage

[요건처리 상세]
1. 사용자가 제공:
   - messages: List<SlackMessageDto> (timestamp, senderName, text, myMessage)
   - myRole: VARCHAR(100)
   - aiRoles: List<String> (3개)
   - conversationDate: DATE
2. Spring 2가 FastAPI로 분석 요청
3. FastAPI의 SlackScenarioService가:
   - ConversationAnalyzer (LLM GPT-4): 주제, 상황, 사용자 역할 추출
   - ScenarioGenerator (LLM GPT-4) × 4:
     - Overview 시나리오 1개
     - aiRoles 각각에 대한 Detail 시나리오 3개
     - 각 시나리오마다: title, aiRole, fixedQuestions (3개)
4. Spring 2가 저장:
   - subject 테이블 INSERT (creation_type='SLACK', my_role, situation, conversation_date, message_count)
   - scenario 테이블 INSERT × 4:
     - topic_type: 'OVERVIEW' (1개), 'DETAIL' (3개)
     - status: 'GENERATED'
     - fixed_questions: JSON 배열
5. 클라이언트에 {subjectId, scenarios[]} 반환

**관련 필드**:
- `subject.subject_id`
- `subject.user_id`
- `subject.creation_type` = 'SLACK'
- `subject.my_role`
- `subject.situation`
- `subject.conversation_date`
- `subject.message_count`
- `scenario.scenario_id`
- `scenario.subject_id` (FK)
- `scenario.title` VARCHAR(80)
- `scenario.ai_role` VARCHAR(100)
- `scenario.topic_type` ENUM
- `scenario.fixed_questions` TEXT (JSON)
- `scenario.status` = 'GENERATED'

---

#### 3.1.2 Slack 메시지 저장

**소분류 요구사항 명**: Slack 대화 히스토리 영구 저장

**요구사항 설명**:

[요구사항]
- Slack 메시지를 DB에 저장하여 추후 참조 및 재분석 가능

[대상업무]
- **backend-crud2**: POST /internal/slack-messages

[요건처리 상세]
1. Slack 분석 요청 시 messages를 slack_message 테이블에 INSERT
2. 각 메시지마다:
   - message_ts: DATETIME
   - sender_name: VARCHAR(100)
   - text: TEXT
3. 저장 완료

**관련 필드**:
- `slack_message.slack_message_id`
- `slack_message.user_id` (FK)
- `slack_message.message_ts`
- `slack_message.sender_name`
- `slack_message.text`

---

### 3.2 프롬프트 기반 시나리오 생성

**소분류 요구사항 명**: 사용자 입력 프롬프트로 맞춤형 시나리오 생성

**요구사항 설명**:

[요구사항]
- 사용자가 직접 역할과 상황을 입력하여 1개의 맞춤형 시나리오를 생성할 수 있어야 함

[대상업무]
- **backend-gateway**: POST /scenarios/roleplaying/generate-from-prompt
- **backend-api**: POST /internal/scenarios/generate-from-prompt
- **backend-crud2**: POST /internal/scenarios/prompt/generate-and-save
- **frontend-web**: PromptScenarioForm

[요건처리 상세]
1. 사용자가 제공:
   - myRole: VARCHAR(100) (1-100자)
   - aiRole: VARCHAR(100) (1-100자)
   - situation: TEXT (1-500자)
2. Spring Gateway가 userId 추출 후 Spring 2로 요청
3. Spring 2가 FastAPI로 시나리오 생성 요청
4. FastAPI의 PromptBasedScenarioService가:
   - DB에서 사용자의 과거 시나리오 조회 (중복 방지)
   - ScenarioEnhancer (LLM): 상황 강화
   - TitleGenerator (LLM): 제목 생성
   - FixedQuestionBuilder (LLM): 3개 고정 질문 생성
5. Spring 2가 저장:
   - subject 테이블 INSERT (creation_type='PROMPT', my_role, situation)
   - scenario 테이블 INSERT (topic_type='DIRECT', status='READY')
6. {scenarioId, subjectId, title} 반환

**관련 필드**:
- `subject.creation_type` = 'PROMPT'
- `subject.my_role`
- `subject.situation`
- `scenario.topic_type` = 'DIRECT'
- `scenario.title`
- `scenario.ai_role`
- `scenario.fixed_questions` (JSON)
- `scenario.status` = 'READY'

---

### 3.3 시나리오 조회

**소분류 요구사항 명**: 사용자별 시나리오 목록 조회

**요구사항 설명**:

[요구사항]
- 로그인한 사용자가 자신이 생성한 시나리오 목록을 조회할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /scenarios/my-scenarios
- **backend-crud2**: GET /internal/scenarios/user/{userId}
- **frontend-web**: HomePage > ScenarioList

[요건처리 상세]
1. 클라이언트가 JWT와 함께 요청
2. Spring Gateway가 userId 추출
3. Spring 2가 scenario 테이블 조회 (user_id, ORDER BY created_at DESC)
4. 각 시나리오의 subject 정보도 JOIN 조회
5. [{scenarioId, title, aiRole, topicType, fixedQuestions, createdAt, subject{...}}] 반환

**관련 필드**:
- `scenario.scenario_id`
- `scenario.title`
- `scenario.ai_role`
- `scenario.topic_type`
- `scenario.fixed_questions`
- `scenario.created_at`
- `subject.subject_id`
- `subject.creation_type`

---

## 4. 롤플레잉 세션

### 4.1 세션 생성

**소분류 요구사항 명**: 롤플레잉 세션 생성 및 WebSocket 준비

**요구사항 설명**:

[요구사항]
- 사용자가 시나리오를 선택하면 session_id를 발급하고 WebSocket URL을 제공해야 함
- MySQL (scenario_session) + Redis (임시 세션) 양쪽에 저장

[대상업무]
- **backend-gateway**: POST /roleplaying/sessions
- **backend-crud2**: POST /internal/sessions
- **backend-api**: POST /internal/sessions/setup
- **frontend-web**: useRoleplaySession Hook

[요건처리 상세]
1. 사용자가 {scenarioId, interactionMode} 제공
2. Spring Gateway가 UUID 기반 session_id 생성
3. Spring 2가 scenario_session 테이블 INSERT:
   - session_id: UUID
   - scenario_id: FK
   - user_id: FK
   - status: 'IN_PROGRESS'
   - total_turns_planned: 7
   - played_turns: 0
   - interaction_mode: 'default'
4. FastAPI로 세션 설정 요청:
   - Redis에 세션 저장 (TTL 2시간)
   - WebSocket URL 생성: ws://{host}/ws/roleplaying/{session_id}
5. 클라이언트에 반환:
   - sessionId
   - wsUrl
   - scenario {scenarioId, title, aiRole, myRole, fixedQuestions}
   - expiresAt

**관련 필드**:
- `scenario_session.session_id` VARCHAR(36) PK
- `scenario_session.scenario_id` FK
- `scenario_session.user_id` FK
- `scenario_session.status` = 'IN_PROGRESS'
- `scenario_session.total_turns_planned` = 7
- `scenario_session.played_turns` = 0
- `scenario_session.interaction_mode`
- Redis: {sessionId, userId, scenarioId, expiresAt}

---

### 4.2 세션 종료

**소분류 요구사항 명**: 롤플레잉 세션 종료 및 종합 피드백 생성

**요구사항 설명**:

[요구사항]
- 사용자가 세션을 종료하면 scenario_session.status를 'FINISHED'로 변경하고 종합 피드백을 자동 생성해야 함

[대상업무]
- **backend-api**: WS 메시지 END_SESSION
- **backend-crud2**: POST /internal/sessions/{sessionId}/complete
- **frontend-web**: useRoleplaySession Hook (종료 처리)

[요건처리 상세]
1. 클라이언트가 END_SESSION WebSocket 메시지 전송
2. FastAPI가:
   - Spring 2로 세션 완료 요청
   - scenario_session 테이블 UPDATE:
     - status = 'FINISHED'
     - finish_reason = 'user_end' / 'turn_limit' / 'error'
     - finished_at = 현재시각
   - Redis 세션 삭제
3. FastAPI가 종합 피드백 생성 (POST /feedback/sessions/{sessionId}/end-hook)
4. SESSION_ENDED 메시지 전송

**관련 필드**:
- `scenario_session.status` = 'FINISHED'
- `scenario_session.finish_reason` VARCHAR(50)
- `scenario_session.finished_at` DATETIME

---

## 5. 실시간 음성 대화

### 5.1 WebSocket 연결 및 초기화

**소분류 요구사항 명**: WebSocket 연결 및 첫 질문 전송

**요구사항 설명**:

[요구사항]
- 클라이언트가 WebSocket으로 연결하고 INIT 메시지를 보내면 첫 고정 질문을 전송해야 함

[대상업무]
- **backend-api**: WS /ws/roleplaying/{session_id}
- **frontend-web**: useRoleplaySession Hook (WebSocket)

[요건처리 상세]
1. 클라이언트가 ws://{host}/ws/roleplaying/{session_id} 연결
2. Redis에서 session_id 검증
3. 클라이언트가 INIT 메시지 전송
4. FastAPI가:
   - SessionState 메모리 로드
   - 첫 고정 질문 (fixed_questions[0]) 전송
   - AI_TEXT 메시지로 전송
5. 클라이언트에서 TTS로 음성 재생

---

### 5.2 실시간 STT (음성 인식)

**소분류 요구사항 명**: 실시간 음성 인식 (Deepgram STT)

**요구사항 설명**:

[요구사항]
- 사용자가 마이크로 발화하면 실시간으로 STT 처리하여 부분 결과 및 최종 결과를 전송해야 함

[대상업무]
- **backend-api**: STTService (Deepgram SDK)
- **frontend-web**: AudioContext, MediaRecorder

[요건처리 상세]
1. 사용자가 마이크 버튼 클릭
2. 클라이언트의 AudioContext가 PCM 16-bit mono, 16kHz 데이터 생성
3. 100ms 단위로 AUDIO_CHUNK (Binary) WebSocket 전송
4. FastAPI의 STTService (Deepgram)가:
   - 실시간 스트리밍 STT 수행
   - STT_PARTIAL 메시지 전송 (부분 결과)
   - 발화 종료 감지 시 STT_FINAL 메시지 전송 (최종 결과)
5. 사용자가 마이크 버튼 해제 시 UTTERANCE_END 전송

---

### 5.3 발화 평가 및 피드백

**소분류 요구사항 명**: 사용자 발화 즉시 평가 (발음/문법/맥락)

**요구사항 설명**:

[요구사항]
- 사용자 발화마다 발음, 문법, 맥락을 병렬 평가하여 점수와 피드백을 즉시 제공해야 함
- 점수 미달 시 재시도 요청 (최대 3회)

[대상업무]
- **backend-api**: FeedbackService
  - PronunciationEvaluator (Azure Speech API)
  - GrammarEvaluator (LLM GPT-4)
  - RelevanceEvaluator (LLM GPT-4)
  - FeedbackJudge
- **backend-crud2**: scenario_message 테이블 (점수 저장)

[요건처리 상세]
1. 사용자가 UTTERANCE_END 전송
2. FastAPI가 병렬 평가 실행 (asyncio.gather):
   - **PronunciationEvaluator** (Azure Speech API):
     - 오디오 데이터 + 텍스트 전송
     - 발음 점수 (0-100) + 단어별 발음 상세 반환
   - **GrammarEvaluator** (LLM GPT-4):
     - GRAMMAR_EVALUATION_PROMPT
     - 출력: {"score": 0-100, "feedback_en": "...", "feedback_ko": "..."}
   - **RelevanceEvaluator** (LLM GPT-4):
     - RELEVANCE_EVALUATION_PROMPT
     - 대화 히스토리 + 현재 질문 + 사용자 응답
     - 출력: {"score": 0-100, "feedback_en": "...", "feedback_ko": "..."}
3. FeedbackJudge가 재시도 필요 여부 판단:
   - pronunciation_score < 70 OR grammar_score < 70
   - current_question_retry_count < 3이면 RETRY_REQUIRED 전송
   - 3회 이상이면 다음 질문으로 진행
4. Spring 2에 scenario_message INSERT:
   - speaker = 'user'
   - message_text = STT 결과
   - audio_url = S3 URL
   - pronunciation_score
   - grammar_score
   - relevance_score
   - overall_score = (pronunciation + grammar + relevance) / 3
   - needs_correction = TRUE/FALSE
   - retry_count
   - primary_issue = 'pronunciation' / 'grammar' / 'relevance'
   - feedback_sections = JSON:
     [
       {"type": "pronunciation", "feedback_en": "...", "feedback_ko": "..."},
       {"type": "grammar", "feedback_en": "...", "feedback_ko": "..."},
       {"type": "relevance", "feedback_en": "...", "feedback_ko": "..."}
     ]
5. 클라이언트에 FEEDBACK 메시지 전송:
   - {pronunciationScore, grammarScore, relevanceScore}
6. 클라이언트에 FEEDBACK_STREAMING 메시지 전송 (한글 피드백 텍스트)

**관련 필드**:
- `scenario_message.speaker` = 'user'
- `scenario_message.message_text` TEXT
- `scenario_message.audio_url` TEXT (S3)
- `scenario_message.pronunciation_score` INT (0-100)
- `scenario_message.grammar_score` INT (0-100)
- `scenario_message.relevance_score` INT (0-100)
- `scenario_message.overall_score` INT
- `scenario_message.needs_correction` BOOLEAN
- `scenario_message.retry_count` INT
- `scenario_message.primary_issue` VARCHAR(50)
- `scenario_message.feedback_sections` JSON

---

### 5.4 AI 응답 생성

**소분류 요구사항 명**: AI 역할 기반 동적 질문 생성

**요구사항 설명**:

[요구사항]
- 사용자 발화 후 AI가 다음 질문을 생성해야 함
- Turn 1, 4, 7: 고정 질문 사용
- 그 외: LLM으로 동적 질문 생성

[대상업무]
- **backend-api**: AITutorService, LLMQuestionGenerator

[요건처리 상세]
1. 사용자 발화 평가 완료 후
2. AITutorService가 AI 턴 번호 확인:
   - ai_turn_count = 1, 4, 7: fixed_questions[index] 사용
   - 그 외: LLMQuestionGenerator 호출
3. LLMQuestionGenerator (GPT-4):
   - FOLLOWUP_QUESTION_PROMPT
   - 입력: 시나리오 (myRole, aiRole), 대화 히스토리, 사용자 마지막 발화
   - 출력: 다음 질문 (영어)
4. scenario_message INSERT:
   - speaker = 'ai'
   - message_text = 질문 (영어)
   - question_ko = 질문 (한글, LLM 번역)
   - recommended_keywords = JSON 배열 (LLM 생성)
5. 클라이언트에 AI_TEXT_STREAMING으로 스트리밍 전송
6. 클라이언트가 TTS로 음성 재생

**관련 필드**:
- `scenario_message.speaker` = 'ai'
- `scenario_message.message_text` TEXT (영어 질문)
- `scenario_message.question_ko` TEXT (한글 질문)
- `scenario_message.recommended_keywords` JSON (추천 키워드 배열)

---

## 6. 피드백 및 평가

### 6.1 종합 피드백 생성

**소분류 요구사항 명**: 세션 종료 시 전체 대화 분석 및 종합 피드백 생성

**요구사항 설명**:

[요구사항]
- 세션 종료 시 모든 발화를 분석하여 종합 점수와 한글 피드백을 생성해야 함
- IT 커뮤니케이션 멘토 페르소나로 따뜻하고 구체적인 피드백 제공

[대상업무]
- **backend-api**: POST /feedback/sessions/{session_id}/end-hook
- **backend-crud2**: POST /internal/sessions/{session_id}/comprehensive-feedback

[요건처리 상세]
1. 세션 종료 시 FastAPI가 자동으로 Hook 호출
2. DB에서 scenario_message 조회 (speaker='user', session_id, ORDER BY turn_index)
3. 각 발화의 점수 평균 계산:
   - avg_pronunciation = AVG(pronunciation_score)
   - avg_grammar = AVG(grammar_score)
   - avg_relevance = AVG(relevance_score)
4. 모든 발화 + 점수 + 개별 피드백을 LLM (GPT-4)에 전달:
   - COMPREHENSIVE_FEEDBACK_PROMPT_TEMPLATE
   - 페르소나: "10년 경력의 IT 커뮤니케이션 멘토, 친절하고 구체적"
   - 입력: 모든 user 발화 + 점수 + feedback_sections
   - 출력:
     ```json
     {
       "feedback_short": "200자 요약",
       "feedback_long": "600자 상세 피드백 (잘한 점 + 개선 사항 + One-Point Lesson)"
     }
     ```
5. scenario_feedback INSERT:
   - session_id
   - scenario_id
   - avg_pronunciation, avg_grammar, avg_relevance
   - final_feedback_short
   - final_feedback_long
6. Spring 2에 저장 요청

**관련 필드**:
- `scenario_feedback.session_id` FK
- `scenario_feedback.scenario_id` FK
- `scenario_feedback.avg_pronunciation` DECIMAL(5,2)
- `scenario_feedback.avg_grammar` DECIMAL(5,2)
- `scenario_feedback.avg_relevance` DECIMAL(5,2)
- `scenario_feedback.final_feedback_short` TEXT
- `scenario_feedback.final_feedback_long` TEXT

---

### 6.2 종합 피드백 조회

**소분류 요구사항 명**: 세션별 종합 피드백 조회

**요구사항 설명**:

[요구사항]
- 사용자가 완료된 세션의 종합 피드백을 조회할 수 있어야 함

[대상업무]
- **backend-api**: GET /feedback/comprehensive/{session_id}
- **frontend-web**: FeedbackPage

[요건처리 상세]
1. 클라이언트가 session_id 제공
2. FastAPI가 scenario_feedback 조회
3. 없으면 즉시 생성 (6.1과 동일)
4. {sessionId, avgPronunciation, avgGrammar, avgRelevance, feedbackShort, feedbackLong} 반환

---

## 7. IT 용어 학습

### 7.1 랜덤 IT 질문 조회

**소분류 요구사항 명**: IT 용어 학습용 랜덤 질문 제공

**요구사항 설명**:

[요구사항]
- 사용자가 IT 용어 설명 연습을 위해 랜덤 질문을 조회할 수 있어야 함

[대상업무]
- **backend-api**: GET /it-explanation/questions/random
- **backend-crud2**: it_question 테이블

[요건처리 상세]
1. 클라이언트가 랜덤 질문 요청
2. FastAPI가 DB에서 it_question 무작위 조회
3. {questionId, questionText, questionTextKo, category, difficulty} 반환

**관련 필드**:
- `it_question.question_id`
- `it_question.question_text` VARCHAR(500) (영어)
- `it_question.question_text_ko` VARCHAR(500) (한글)
- `it_question.category` VARCHAR(50)
- `it_question.difficulty` ENUM('EASY', 'MEDIUM', 'HARD')

---

### 7.2 IT 설명 연습 세션

**소분류 요구사항 명**: IT 용어 설명 답변 제출 및 3가지 기준 평가

**요구사항 설명**:

[요구사항]
- 사용자가 IT 질문에 텍스트 또는 음성으로 답변하면 LLM이 3가지 기준(명확성, 기술적 정확성, 전문용어 사용)으로 평가하여 점수와 피드백을 제공해야 함

[대상업무]
- **backend-api**: POST /it-explanation/sessions
- **backend-crud2**: it_practice_session 테이블

[요건처리 상세]
1. 사용자가 {questionId, userAnswer, sessionType, audioUrl(선택)} 제공
2. FastAPI가:
   - it_question 조회 (key_keywords, model_answer)
   - LLM (GPT-4) 평가:
     - 입력: question_text, key_keywords, model_answer, user_answer
     - 평가 기준:
       1. 명확성 (Clarity): 논리적 구조, 이해 용이성, 구체성
       2. 기술적 정확성 (Technical Accuracy): 핵심 개념 포함, 사실 정확성, 완전성
       3. 전문용어 사용 (Terminology): IT 용어 적절성, 전문성
     - 출력:
       ```json
       {
         "clarity_score": 0-100,
         "technical_accuracy_score": 0-100,
         "terminology_score": 0-100,
         "overall_score": 0-100,
         "feedback": "한글 피드백 (잘한 점 + 개선 사항)"
       }
       ```
3. it_practice_session INSERT:
   - user_id, question_id, session_type ('TEXT' or 'VOICE')
   - user_answer, audio_url
   - clarity_score, technical_accuracy_score, terminology_score, overall_score
   - feedback
   - completed_at = 현재시각
4. {clarityScore, technicalAccuracyScore, terminologyScore, overallScore, feedback} 반환

**관련 필드**:
- `it_practice_session.session_id`
- `it_practice_session.user_id` FK
- `it_practice_session.question_id` FK
- `it_practice_session.user_answer` TEXT
- `it_practice_session.audio_url` VARCHAR(500)
- `it_practice_session.clarity_score` INT (0-100)
- `it_practice_session.technical_accuracy_score` INT (0-100)
- `it_practice_session.terminology_score` INT (0-100)
- `it_practice_session.overall_score` INT (0-100)
- `it_practice_session.feedback` TEXT
- `it_practice_session.session_type` ENUM('TEXT', 'VOICE')
- `it_practice_session.completed_at` DATETIME

---

### 7.3 IT 챗봇 대화

**소분류 요구사항 명**: IT 용어 관련 챗봇 대화 (컨텍스트 기반)

**요구사항 설명**:

[요구사항]
- 사용자가 IT 용어에 대해 자유롭게 질문하고 LLM이 이전 대화 맥락을 기억하며 답변할 수 있어야 함
- 최근 5턴의 대화 히스토리를 유지하여 연속적인 대화 가능

[대상업무]
- **backend-api**: POST /it-explanation/chatbot
- **backend-crud2**: it_chatbot_conversation 테이블

[요건처리 상세]
1. 사용자가 {userId, userMessage} 전송
2. FastAPI가:
   - it_chatbot_conversation에서 최근 대화 조회 (user_id, ORDER BY created_at DESC LIMIT 5)
   - 대화 히스토리를 컨텍스트로 구성
   - LLM (GPT-4) 호출 (IT 전문가 페르소나):
     - 시스템 프롬프트: "You are an IT expert who explains technical concepts clearly."
     - 이전 대화 컨텍스트 제공
     - 사용자 메시지 전달
3. it_chatbot_conversation INSERT:
   - user_id
   - user_message = 사용자 입력
   - bot_response = LLM 응답
   - context = JSON 형태로 최근 5턴 대화 저장
     ```json
     [
       {"role": "user", "content": "..."},
       {"role": "assistant", "content": "..."},
       ...
     ]
     ```
4. {botResponse} 반환

**관련 필드**:
- `it_chatbot_conversation.conversation_id`
- `it_chatbot_conversation.user_id` FK
- `it_chatbot_conversation.user_message` TEXT
- `it_chatbot_conversation.bot_response` TEXT
- `it_chatbot_conversation.context` JSON (최근 5턴 대화 히스토리)

---

## 8. 통합 (Slack/GitHub)

### 8.1 Slack 연동

#### 8.1.1 Slack OAuth 인증

**소분류 요구사항 명**: Slack OAuth 인증 및 토큰 저장

**요구사항 설명**:

[요구사항]
- 사용자가 Slack 워크스페이스와 연동하여 채널 접근 권한을 부여해야 함

[대상업무]
- **backend-gateway**: GET /integrations/slack/auth, GET /integrations/slack/callback
- **backend-crud2**: integration 테이블

[요건처리 상세]
1. 사용자가 "Slack 연동" 클릭
2. Spring Gateway가 Slack OAuth URL로 리다이렉트
3. Slack이 authorization code를 callback URL로 전달
4. Spring 2가:
   - authorization code로 Slack Access Token 교환
   - integration INSERT:
     - provider='slack'
     - access_token=(Slack token)
     - is_active=TRUE
5. "연동 완료" 응답

**관련 필드**:
- `integration.integration_id`
- `integration.user_id` FK
- `integration.provider` = 'slack'
- `integration.access_token` TEXT
- `integration.is_active` = TRUE

---

#### 8.1.2 Slack 채널 목록 조회

**소분류 요구사항 명**: 연동된 Slack 워크스페이스의 채널 목록 조회

**요구사항 설명**:

[요구사항]
- 사용자가 Slack 채널 목록을 조회하여 분석할 채널을 선택할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /integrations/slack/channels
- **backend-crud2**: integration 테이블 (access_token 사용)

[요건처리 상세]
1. 클라이언트가 채널 목록 요청
2. Spring 2가 integration 조회 (provider='slack', is_active=TRUE)
3. Slack API (conversations.list) 호출
4. [{channelId, channelName}] 반환

---

#### 8.1.3 Slack 채널 선택 및 메시지 동기화

**소분류 요구사항 명**: 선택한 Slack 채널의 메시지 히스토리 가져오기

**요구사항 설명**:

[요구사항]
- 사용자가 채널을 선택하면 최근 메시지를 가져와서 시나리오 생성에 사용할 수 있어야 함

[대상업무]
- **backend-crud2**: POST /internal/integrations/slack/sync-messages

[요건처리 상세]
1. 사용자가 channelId 선택
2. Spring 2가:
   - integration.selected_channel_id 업데이트
   - Slack API (conversations.history) 호출
   - slack_message INSERT (최근 100개 메시지)
3. "동기화 완료" 응답

**관련 필드**:
- `integration.selected_channel_id` VARCHAR(50)
- `slack_message.message_ts`
- `slack_message.sender_name`
- `slack_message.text`

---

### 8.2 GitHub 연동

#### 8.2.1 GitHub OAuth 인증

**소분류 요구사항 명**: GitHub OAuth 인증 및 토큰 저장

**요구사항 설명**:

[요구사항]
- 사용자가 GitHub 저장소와 연동하여 이슈 접근 권한을 부여해야 함

[대상업무]
- **backend-gateway**: GET /integrations/github/auth, GET /integrations/github/callback

[요건처리 상세]
1. GitHub OAuth 인증 플로우 (Slack과 유사)
2. integration INSERT (provider='github', access_token)

**관련 필드**:
- `integration.provider` = 'github'
- `integration.access_token`

---

#### 8.2.2 GitHub 이슈 동기화

**소분류 요구사항 명**: GitHub 이슈 가져오기 및 시나리오 생성

**요구사항 설명**:

[요구사항]
- 사용자가 GitHub 이슈를 가져와서 기술 토론 롤플레이 시나리오를 생성할 수 있어야 함
- 동일한 이슈(repo_owner + repo_name + issue_number)는 중복 저장하지 않음

[대상업무]
- **backend-crud2**: POST /internal/integrations/github/sync-issues

[요건처리 상세]
1. GitHub API (GET /repos/{owner}/{repo}/issues/{issue_number}) 호출
2. github_issue UPSERT (UNIQUE 제약: repo_owner, repo_name, issue_number):
   - repo_owner, repo_name, issue_number, title, body 저장
   - state (open/closed)
   - external_created_at (GitHub 이슈 생성 시간)
   - external_updated_at (GitHub 이슈 수정 시간)
   - closed_at (종료 시간, state='closed'일 때만)
3. subject 생성 (creation_type='GITHUB')
4. 시나리오 생성 요청

**관련 필드**:
- `github_issue.github_issue_id`
- `github_issue.user_id` FK
- `github_issue.repo_owner` VARCHAR(100) NOT NULL
- `github_issue.repo_name` VARCHAR(200) NOT NULL
- `github_issue.issue_number` INT NOT NULL
- `github_issue.title` VARCHAR(255) NOT NULL
- `github_issue.body` TEXT
- `github_issue.state` VARCHAR(30)
- `github_issue.external_created_at` DATETIME
- `github_issue.external_updated_at` DATETIME
- `github_issue.closed_at` DATETIME
- `subject.creation_type` = 'GITHUB'

---

## 9. 마이페이지

### 9.1 완료된 세션 목록 조회

**소분류 요구사항 명**: 사용자별 완료된 롤플레잉 세션 목록 조회

**요구사항 설명**:

[요구사항]
- 사용자가 자신이 완료한 롤플레잉 세션 목록을 조회하고 각 세션의 종합 피드백을 확인할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /roleplaying/sessions/completed
- **backend-crud2**: GET /internal/sessions/user/{userId}/completed
- **frontend-web**: UserPage > CompletedSessionList

[요건처리 상세]
1. 클라이언트가 JWT와 함께 요청
2. Spring 2가 scenario_session 조회:
   - user_id = {userId}
   - status = 'FINISHED'
   - ORDER BY finished_at DESC
3. 각 세션의 scenario, scenario_feedback JOIN 조회
4. [{sessionId, scenarioTitle, finishedAt, avgPronunciation, avgGrammar, feedbackShort}] 반환

**관련 필드**:
- `scenario_session.session_id`
- `scenario_session.status` = 'FINISHED'
- `scenario_session.finished_at`
- `scenario.title`
- `scenario_feedback.avg_pronunciation`
- `scenario_feedback.avg_grammar`
- `scenario_feedback.final_feedback_short`

---

### 9.2 세션 상세 조회 (발화 목록)

**소분류 요구사항 명**: 특정 세션의 모든 발화 내역 조회

**요구사항 설명**:

[요구사항]
- 사용자가 완료된 세션의 전체 대화 내역을 조회할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /roleplaying/sessions/{sessionId}/utterances
- **backend-crud2**: GET /internal/sessions/{sessionId}/messages
- **frontend-web**: FeedbackPage > MessageList

[요건처리 상세]
1. 클라이언트가 sessionId 제공
2. Spring 2가 scenario_message 조회 (session_id, ORDER BY turn_index ASC)
3. [{messageId, speaker, messageText, audioUrl, scores, feedbackSections}] 반환

**관련 필드**:
- `scenario_message.message_id`
- `scenario_message.turn_index`
- `scenario_message.speaker`
- `scenario_message.message_text`
- `scenario_message.audio_url`
- `scenario_message.pronunciation_score`
- `scenario_message.feedback_sections` (JSON)

---

### 9.3 추천 키워드 조회

**소분류 요구사항 명**: AI 질문에 대한 추천 키워드 조회

**요구사항 설명**:

[요구사항]
- 사용자가 AI 질문에 답변할 때 참고할 추천 키워드를 조회할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /roleplaying/messages/{messageId}/keywords
- **backend-crud2**: GET /internal/messages/{messageId}

[요건처리 상세]
1. 클라이언트가 messageId 제공 (AI 메시지)
2. Spring 2가 scenario_message 조회
3. {recommendedKeywords: []} 반환

**관련 필드**:
- `scenario_message.recommended_keywords` JSON (배열)

---

## 10. 북마크 관리

### 10.1 북마크 추가

**소분류 요구사항 명**: 특정 발화를 북마크로 저장

**요구사항 설명**:

[요구사항]
- 사용자가 세션 중 특정 발화를 북마크하여 나중에 복습할 수 있어야 함

[대상업무]
- **backend-gateway**: POST /bookmarks
- **backend-crud2**: POST /internal/bookmarks
- **frontend-web**: MessageList > BookmarkButton

[요건처리 상세]
1. 사용자가 {messageId} 제공
2. Spring 2가 user_bookmarks INSERT:
   - user_id
   - message_id
3. "북마크 추가 완료" 응답

**관련 필드**:
- `user_bookmarks.id` PK
- `user_bookmarks.user_id`
- `user_bookmarks.message_id` FK
- `user_bookmarks.created_at`

---

### 10.2 북마크 목록 조회

**소분류 요구사항 명**: 사용자별 북마크 목록 조회

**요구사항 설명**:

[요구사항]
- 사용자가 자신이 북마크한 발화 목록을 조회할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /bookmarks
- **backend-crud2**: GET /internal/users/{userId}/bookmarks
- **frontend-web**: UserPage > BookmarkList

[요건처리 상세]
1. 클라이언트가 JWT와 함께 요청
2. Spring 2가:
   - user_bookmarks JOIN scenario_message
   - user_id = {userId}
   - ORDER BY created_at DESC
3. [{bookmarkId, messageId, messageText, audioUrl, createdAt}] 반환

**관련 필드**:
- `user_bookmarks.id`
- `user_bookmarks.message_id`
- `scenario_message.message_text`
- `scenario_message.audio_url`
- `user_bookmarks.created_at`

---

### 10.3 북마크 삭제

**소분류 요구사항 명**: 북마크 삭제

**요구사항 설명**:

[요구사항]
- 사용자가 북마크를 삭제할 수 있어야 함

[대상업무]
- **backend-gateway**: DELETE /bookmarks/{bookmarkId}
- **backend-crud2**: DELETE /internal/bookmarks/{bookmarkId}

[요건처리 상세]
1. 클라이언트가 bookmarkId 제공
2. Spring 2가 user_bookmarks DELETE (id=bookmarkId, user_id=인증된 사용자)
3. "삭제 완료" 응답

---

## 11. 기타 기능

### 11.1 헬스 체크

**소분류 요구사항 명**: 서버 상태 확인

**요구사항 설명**:

[요구사항]
- 서버가 정상 작동 중인지 확인할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /actuator/health
- **backend-crud2**: GET /health
- **backend-api**: GET /health/ping

[요건처리 상세]
1. 클라이언트가 헬스 체크 요청
2. {status: "ok", timestamp: "..."} 반환

---

### 11.2 Swagger API 문서

**소분류 요구사항 명**: API 문서 자동 생성

**요구사항 설명**:

[요구사항]
- 모든 API 엔드포인트를 Swagger UI로 확인할 수 있어야 함

[대상업무]
- **backend-gateway**: GET /swagger-ui.html
- **backend-crud2**: GET /swagger-ui.html

[요건처리 상세]
1. SpringDoc OpenAPI 자동 생성
2. 모든 컨트롤러의 @RequestMapping, @GetMapping 등 스캔
3. Swagger UI 제공

---

## 12. 비기능 요구사항

### 12.1 보안

**요구사항**:
- **JWT 인증**: 모든 보호된 API는 JWT 토큰 검증 필수
- **비밀번호 암호화**: BCrypt 해싱 (Strength 10)
- **HTTPS**: 프로덕션 환경에서 HTTPS 필수
- **CORS**: 특정 도메인만 허용
- **SQL Injection 방지**: JPA Prepared Statement 사용

### 12.2 성능

**요구사항**:
- **WebSocket 동시 연결**: 최소 100명 지원
- **STT 실시간 처리**: 100ms 이하 지연
- **LLM 응답 생성**: 10초 이내
- **Redis 세션 TTL**: 2시간
- **데이터베이스 인덱스**: session_id, user_id, message_ts 등

### 12.3 가용성

**요구사항**:
- **서버 Uptime**: 99.9% 이상
- **데이터베이스 백업**: 매일 자동 백업
- **로그 보관**: 30일

### 12.4 확장성

**요구사항**:
- **수평 확장**: Docker 컨테이너 기반, Kubernetes 배포 가능
- **데이터베이스 샤딩**: 사용자 수 증가 시 샤딩 대비
- **CDN**: S3 + CloudFront로 오디오 파일 배포

---

## 13. 데이터베이스 ER 다이어그램 요약

```
user (1) ──────── (*) scenario_session
  │                         │
  │                         └─ (1) scenario_feedback
  │                         └─ (*) scenario_message
  │
  ├─ (1:1) user_settings
  ├─ (*) subject ──── (*) scenario
  ├─ (*) user_bookmarks ──── scenario_message
  ├─ (*) integration (Slack/GitHub)
  ├─ (*) slack_message
  ├─ (*) github_issue
  └─ (*) it_practice_session ──── it_question
          └─ (*) it_chatbot_conversation
```

---

## 14. API 엔드포인트 전체 목록

### Spring 1 Gateway (Port 8080)

**인증 (Auth)**:
- POST /auth/email/send-code
- POST /auth/email/verify-code
- POST /auth/signup
- POST /auth/login
- POST /auth/refresh
- GET /auth/google
- GET /auth/google/callback

**사용자 (User)**:
- GET /user/me
- PATCH /user/profile

**시나리오 (Scenario)**:
- GET /scenarios/my-scenarios
- POST /scenarios/roleplaying/generate-from-prompt

**세션 (Session)**:
- POST /roleplaying/sessions
- GET /roleplaying/sessions/completed
- GET /roleplaying/sessions/{sessionId}/utterances
- GET /roleplaying/messages/{messageId}/keywords

**통합 (Integration)**:
- GET /integrations/slack/auth
- GET /integrations/slack/callback
- GET /integrations/slack/channels
- GET /integrations/github/auth
- GET /integrations/github/callback

**북마크 (Bookmark)**:
- GET /bookmarks
- POST /bookmarks
- DELETE /bookmarks/{bookmarkId}

**헬스 체크**:
- GET /actuator/health
- GET /swagger-ui.html

---

### Spring 2 CRUD (Port 8081)

**Internal Auth**:
- POST /internal/auth/email/send-code
- POST /internal/auth/email/verify-code
- POST /internal/auth/signup
- POST /internal/auth/login

**Internal Users**:
- POST /internal/users (회원가입)
- GET /internal/users/{userId}
- PATCH /internal/users/{userId}
- POST /internal/users/{userId}/watch-settings

**Internal Scenarios**:
- GET /internal/scenarios/user/{userId}
- POST /internal/scenarios/slack/analyze-and-save
- POST /internal/scenarios/prompt/generate-and-save

**Internal Sessions**:
- POST /internal/sessions
- POST /internal/sessions/{sessionId}/complete
- GET /internal/sessions/user/{userId}/completed
- GET /internal/sessions/{sessionId}/messages
- POST /internal/sessions/{sessionId}/utterances (발화 저장)
- POST /internal/sessions/{sessionId}/comprehensive-feedback

**Internal Integrations**:
- POST /internal/integrations/slack/sync-messages
- POST /internal/integrations/github/sync-issues

**Internal Bookmarks**:
- GET /internal/users/{userId}/bookmarks
- POST /internal/bookmarks
- DELETE /internal/bookmarks/{bookmarkId}

**Internal Messages**:
- GET /internal/messages/{messageId}

**헬스 체크**:
- GET /health
- GET /swagger-ui.html

---

### FastAPI (Port 8082)

**Internal Scenarios**:
- POST /internal/scenarios/analyze-conversation (Slack 분석)
- POST /internal/scenarios/generate-from-prompt (프롬프트 기반 생성)

**Internal Sessions**:
- POST /internal/sessions/setup (Redis 세션 설정)

**WebSocket**:
- WS /ws/roleplaying/{session_id}

**Feedback**:
- POST /feedback/sessions/{session_id}/end-hook (종합 피드백 생성)
- GET /feedback/comprehensive/{session_id} (종합 피드백 조회)

**IT Explanation**:
- GET /it-explanation/questions/random
- POST /it-explanation/sessions
- POST /it-explanation/chatbot

**헬스 체크**:
- GET /health/ping

---

## 15. 프론트엔드 주요 컴포넌트

### Pages
- **LoginPage**: 로그인 폼
- **SignUpPage**: 회원가입 폼, 이메일 인증
- **HomePage**: 시나리오 목록, 시나리오 생성 버튼
- **RoleplayPage**: 실시간 음성 대화, 3D 아바타, 메시지 리스트
- **FeedbackPage**: 종합 피드백, 발화 목록, 점수 차트
- **UserPage**: 프로필, 완료된 세션 목록, 북마크 목록
- **LearnPage**: IT 용어 학습, 챗봇

### Hooks
- **useRoleplaySession**: WebSocket, STT, TTS, 오디오 처리
- **useScenarioData**: 시나리오 조회, 생성
- **useFeedbackPage**: 종합 피드백 조회
- **useBookmarks**: 북마크 추가/삭제

### Services
- **httpClient**: JWT 토큰 자동 첨부, 토큰 갱신
- **authService**: 로그인, 회원가입, 토큰 관리
- **roleplayService**: 시나리오 생성, 세션 생성

---

## 16. 주요 외부 API 및 서비스

### LLM
- **OpenAI GPT-4**: 시나리오 생성, 질문 생성, 평가, 종합 피드백
- **Anthropic Claude**: 대체 LLM (선택 사항)
- **Ollama**: 로컬 LLM (개발 환경)

### 음성 처리
- **Deepgram STT**: 실시간 스트리밍 음성 인식 (Nova-2 모델)
- **Azure Cognitive Services Speech**: 발음 평가
- **ElevenLabs TTS**: 음성 합성 (선택 사항)

### 외부 통합
- **Slack API**: OAuth, 채널 목록, 메시지 히스토리
- **GitHub API**: OAuth, 이슈 목록
- **Gmail SMTP**: 이메일 인증 코드 발송
- **Google OAuth 2.0**: 소셜 로그인

### 인프라
- **AWS S3**: 오디오 파일 저장
- **AWS CloudFront**: CDN
- **Redis**: 세션 캐시

---

## 17. 환경 변수 목록

### Spring 1 Gateway
```
JWT_SECRET=your_jwt_secret_key_here
JWT_ACCESS_TOKEN_EXPIRATION=1800
SPRING2_BASE_URL=http://localhost:8081
FASTAPI_BASE_URL=http://localhost:8082
FASTAPI_WS_URL=ws://localhost:8082
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback
```

### Spring 2 CRUD
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=skuseme_db
DB_USER=root
DB_PASSWORD=your_password
FASTAPI_BASE_URL=http://localhost:8082
GMAIL_SMTP_USERNAME=your-email@gmail.com
GMAIL_SMTP_PASSWORD=your-app-password
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

### FastAPI
```
DATABASE_URL=mysql+pymysql://user:pass@localhost/skuseme_db
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=your-deepgram-api-key
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=eastus
ELEVENLABS_API_KEY=your-elevenlabs-api-key
SPRING2_BASE_URL=http://localhost:8081
REDIS_URL=redis://localhost:6379/0
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_BUCKET_NAME=skala-audio-files
```

---

## 18. 개발/배포 가이드

### 로컬 개발 환경 실행 순서
1. MySQL 서버 시작
2. Redis 서버 시작
3. Spring 2 CRUD 실행 (`./gradlew bootRun`)
4. FastAPI 실행 (`uvicorn app.main:app --reload`)
5. Spring 1 Gateway 실행 (`./gradlew bootRun`)
6. Frontend 실행 (`npm run dev`)

### 배포 (Docker)
```bash
docker-compose up -d
```

---

**문서 종료**

---

