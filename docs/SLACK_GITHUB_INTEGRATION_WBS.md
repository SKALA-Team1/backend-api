# Slack/GitHub 연동 데이터 수집 및 DB 저장 WBS

**문서 버전:** 1.0
**작성일:** 2025-11-20
**범위:** Slack/GitHub 인증 → 데이터 수집 → DB 저장 → 시나리오 생성

---

## 📋 개요

**목적:** Slack과 GitHub에서 대화/코드 데이터를 수집하여 FastAPI 백엔드에 저장하고, 이를 기반으로 AI 시나리오를 자동 생성

**데이터 흐름:**
```
사용자 인증 (OAuth)
    ↓
Slack/GitHub API 호출
    ↓
데이터 수집 (메시지, 커밋, PR 등)
    ↓
데이터 정규화 및 검증
    ↓
FastAPI DB 저장
    ↓
시나리오 자동 생성
    ↓
사용자에게 제시
```

---

## 1. SLACK 연동 (Slack Integration)

### 1.1 Slack OAuth 인증

#### 백엔드
**상태:** ❌ 미구현

**OAuth 설정:**
- [ ] Slack App 생성
  - [ ] App 이름 및 설정
  - [ ] OAuth Scopes 설정
    - [ ] `channels:history` - 채널 메시지 읽기
    - [ ] `users:read` - 사용자 정보 읽기
    - [ ] `team:read` - 팀 정보 읽기
    - [ ] `users.profile:read` - 프로필 읽기
  - [ ] Redirect URI 설정
  - [ ] Client ID/Secret 발급

**Slack OAuth Flow 구현:**
- [ ] 데이터베이스 모델
  - [ ] SlackOAuthToken 테이블
    - [ ] user_id
    - [ ] access_token (암호화)
    - [ ] refresh_token (선택사항)
    - [ ] token_type
    - [ ] expires_at
    - [ ] scope
    - [ ] workspace_id
    - [ ] workspace_name
    - [ ] created_at, updated_at
- [ ] API 엔드포인트
  - [ ] `GET /integration/slack/auth-url` - OAuth URL 생성
  - [ ] `POST /integration/slack/callback` - OAuth 콜백 처리
  - [ ] `POST /integration/slack/disconnect` - 연동 해제
- [ ] 토큰 관리
  - [ ] 토큰 저장 (암호화)
  - [ ] 토큰 갱신 로직
  - [ ] 토큰 만료 시간 설정

**Slack 클라이언트:**
- [ ] `integrations/clients/slack_client.py` 작성
  - [ ] slack-sdk 사용
  - [ ] 기본 설정 (토큰, 베이스 URL)
  - [ ] 에러 처리
  - [ ] 재시도 로직

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] Slack 연결 버튼
  - [ ] OAuth 링크 생성
  - [ ] 팝업 또는 리다이렉트
- [ ] 연결 상태 표시
  - [ ] 연결됨/연결 안됨
  - [ ] 워크스페이스 이름 표시
  - [ ] 연결 해제 버튼

---

### 1.2 Slack 데이터 수집

#### 백엔드
**상태:** ❌ 미구현

**데이터베이스 모델:**
- [ ] SlackMessage 테이블
  - [ ] id (기본 키)
  - [ ] user_id (SKALA 사용자)
  - [ ] slack_message_id (Slack의 ts)
  - [ ] slack_user_id (메시지 작성자)
  - [ ] slack_username (메시지 작성자 이름)
  - [ ] channel_id (채널 ID)
  - [ ] channel_name (채널 이름)
  - [ ] text (메시지 내용)
  - [ ] thread_ts (스레드 ID, NULL이면 부모 메시지)
  - [ ] timestamp (메시지 작성 시간)
  - [ ] is_bot (봇 메시지 여부)
  - [ ] file_urls (첨부 파일 URL, JSON)
  - [ ] reaction_count (반응 수)
  - [ ] reply_count (댓글 수)
  - [ ] created_at, updated_at
- [ ] SlackThread 테이블 (스레드별 메타데이터)
  - [ ] id
  - [ ] user_id
  - [ ] thread_ts (스레드 ID)
  - [ ] channel_id
  - [ ] parent_message_id
  - [ ] message_count (메시지 수)
  - [ ] last_message_timestamp
  - [ ] created_at, updated_at

**API 엔드포인트:**
- [ ] `GET /integration/slack/channels` - 채널 목록 조회
  - [ ] 토큰 검증
  - [ ] Slack API 호출
  - [ ] 채널 목록 반환
- [ ] `POST /integration/slack/import-channels` - 채널 메시지 수집
  - [ ] 채널 ID 배열 입력
  - [ ] 날짜 범위 (선택사항)
  - [ ] 백그라운드 작업으로 실행
  - [ ] 진행 상황 반환
- [ ] `GET /integration/slack/import-status` - 수집 상태 조회
  - [ ] 진행률
  - [ ] 수집된 메시지 수
  - [ ] 마지막 수집 시간

**Slack 메시지 수집 로직:**
- [ ] Channel 목록 조회
  - [ ] `conversations.list()` API 호출
  - [ ] 공개/프라이빗 채널 구분
  - [ ] 페이지네이션 처리
- [ ] 채널별 메시지 수집
  - [ ] `conversations.history()` API 호출
  - [ ] 날짜 범위 필터링 (latest, oldest)
  - [ ] 페이지네이션 처리 (cursor)
  - [ ] 각 메시지 저장
  - [ ] 스레드 감지 및 처리
- [ ] 스레드 메시지 수집
  - [ ] `conversations.replies()` API 호출
  - [ ] 스레드의 모든 메시지 수집
  - [ ] 부모-자식 관계 저장
- [ ] 사용자 정보 수집
  - [ ] `users.info()` API 호출
  - [ ] 사용자 이름, 이메일, 프로필 사진 저장
  - [ ] 봇 사용자 필터링

**데이터 정규화:**
- [ ] 메시지 텍스트 정제
  - [ ] Slack 형식 문자 제거 (예: `<@U123>`)
  - [ ] URL 정규화
  - [ ] 이모지 처리
  - [ ] 특수 문자 정리
- [ ] 타임스탬프 정규화
  - [ ] Unix timestamp → ISO 8601
  - [ ] 타임존 처리

**에러 처리:**
- [ ] 토큰 만료 처리 (갱신 또는 재인증)
- [ ] Rate limiting 처리 (재시도 로직)
- [ ] 권한 부족 처리
- [ ] 네트워크 오류 처리
- [ ] 데이터 일관성 검증

**백그라운드 작업:**
- [ ] Celery 또는 APScheduler 사용
  - [ ] 비동기 처리
  - [ ] 진행 상황 추적
  - [ ] 실패 시 재시도
  - [ ] 작업 큐 관리

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 채널 선택 화면
  - [ ] 채널 목록 표시
  - [ ] 검색 기능
  - [ ] 다중 선택
- [ ] 날짜 범위 선택
  - [ ] 시작일, 종료일
  - [ ] 프리셋 (최근 1주, 1개월 등)
- [ ] 수집 진행 화면
  - [ ] 진행률 표시
  - [ ] 수집된 메시지 수
  - [ ] 소요 시간
  - [ ] 취소 버튼

---

### 1.3 Slack 데이터 분석 및 시나리오 생성

#### 백엔드
**상태:** ✅ 부분 완료

**대화 분석 로직:**
- [x] 메시지 필터링
  - [x] 봇 메시지 제외
  - [x] 시스템 메시지 제외
  - [x] 너무 짧은 메시지 제외
- [x] 주제 추출
  - [x] LLM을 사용한 주제 분석
- [x] 참가자 식별
  - [x] 사용자별 메시지 수
  - [x] 주요 참가자 선정
- [x] 상황 요약
  - [x] 전체 대화 문맥 파악
  - [x] 핵심 내용 추출

**API 엔드포인트:**
- [x] `POST /roleplaying/internal/scenarios/analyze-conversation`
  - [x] 메시지 배열 입력
  - [x] myRole, aiRoles 입력
  - [x] 시나리오 + 고정 질문 생성
  - [x] 결과 반환

**시나리오 생성:**
- [ ] 개요 시나리오 (1개)
- [ ] 상세 시나리오 (3개)
  - [ ] 각 시나리오마다 AI 역할 다름
  - [ ] 각 시나리오마다 고정 질문 3개

---

## 2. GITHUB 연동 (GitHub Integration)

### 2.1 GitHub OAuth 인증

#### 백엔드
**상태:** ❌ 미구현

**OAuth 설정:**
- [ ] GitHub App 생성
  - [ ] App 이름 및 설정
  - [ ] OAuth Scopes 설정
    - [ ] `repo` - 저장소 접근
    - [ ] `read:user` - 사용자 정보
    - [ ] `user:email` - 이메일 주소
    - [ ] `read:org` - 조직 정보 (선택사항)
  - [ ] Webhook 설정 (선택사항)
  - [ ] Redirect URI 설정
  - [ ] Client ID/Secret 발급

**GitHub OAuth Flow:**
- [ ] 데이터베이스 모델
  - [ ] GitHubOAuthToken 테이블
    - [ ] user_id
    - [ ] access_token (암호화)
    - [ ] token_type
    - [ ] expires_at (선택사항)
    - [ ] scope
    - [ ] github_login (GitHub 사용자 이름)
    - [ ] github_id
    - [ ] created_at, updated_at
- [ ] API 엔드포인트
  - [ ] `GET /integration/github/auth-url` - OAuth URL 생성
  - [ ] `POST /integration/github/callback` - OAuth 콜백 처리
  - [ ] `POST /integration/github/disconnect` - 연동 해제
- [ ] 토큰 관리
  - [ ] 토큰 저장 (암호화)
  - [ ] 토큰 갱신 (선택사항)
  - [ ] 토큰 만료 시간 설정

**GitHub 클라이언트:**
- [ ] `integrations/clients/github_client.py` 작성
  - [ ] PyGithub 또는 requests 사용
  - [ ] 기본 설정 (토큰, 베이스 URL)
  - [ ] 에러 처리
  - [ ] 재시도 로직

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] GitHub 연결 버튼
- [ ] 연결 상태 표시
  - [ ] GitHub 사용자 이름 표시
  - [ ] 연결 해제 버튼

---

### 2.2 GitHub 데이터 수집

#### 백엔드
**상태:** ❌ 미구현

**데이터베이스 모델:**

**Issues & Discussions:**
- [ ] GitHubIssue 테이블
  - [ ] id (기본 키)
  - [ ] user_id (SKALA 사용자)
  - [ ] github_issue_id
  - [ ] repository_id
  - [ ] repository_name
  - [ ] title
  - [ ] body (이슈 설명)
  - [ ] creator_login (이슈 작성자)
  - [ ] labels (라벨, JSON)
  - [ ] state (open/closed)
  - [ ] created_at, updated_at
  - [ ] closed_at

**Comments:**
- [ ] GitHubComment 테이블
  - [ ] id
  - [ ] user_id
  - [ ] github_comment_id
  - [ ] issue_id (GitHubIssue 참조)
  - [ ] comment_author_login
  - [ ] body (댓글 내용)
  - [ ] created_at, updated_at

**Pull Requests:**
- [ ] GitHubPullRequest 테이블
  - [ ] id
  - [ ] user_id
  - [ ] github_pr_id
  - [ ] repository_id
  - [ ] repository_name
  - [ ] title
  - [ ] description
  - [ ] creator_login
  - [ ] base_branch
  - [ ] head_branch
  - [ ] state (open/merged/closed)
  - [ ] created_at, updated_at

**Commits:**
- [ ] GitHubCommit 테이블
  - [ ] id
  - [ ] user_id
  - [ ] github_commit_id (SHA)
  - [ ] repository_id
  - [ ] repository_name
  - [ ] message
  - [ ] author_name
  - [ ] committer_login
  - [ ] created_at

**API 엔드포인트:**
- [ ] `GET /integration/github/repositories` - 저장소 목록
  - [ ] 토큰 검증
  - [ ] GitHub API 호출
  - [ ] 저장소 목록 반환
- [ ] `POST /integration/github/import-data` - 데이터 수집
  - [ ] 저장소 선택
  - [ ] 수집 대상 선택 (Issues, PRs, Commits 등)
  - [ ] 날짜 범위 (선택사항)
  - [ ] 백그라운드 작업으로 실행
- [ ] `GET /integration/github/import-status` - 수집 상태

**GitHub 데이터 수집 로직:**
- [ ] Repository 목록 조회
  - [ ] `GET /user/repos` API 호출
  - [ ] 페이지네이션 처리
  - [ ] 저장소별 메타데이터 저장
- [ ] Issues 수집
  - [ ] `GET /repos/{owner}/{repo}/issues` API 호출
  - [ ] state 필터 (open/closed)
  - [ ] 날짜 범위 필터
  - [ ] 페이지네이션 처리
  - [ ] 각 이슈마다 댓글 수집
    - [ ] `GET /repos/{owner}/{repo}/issues/{issue_number}/comments`
- [ ] Pull Requests 수집
  - [ ] `GET /repos/{owner}/{repo}/pulls` API 호출
  - [ ] state 필터
  - [ ] 각 PR마다 댓글, 리뷰 수집
- [ ] Commits 수집
  - [ ] `GET /repos/{owner}/{repo}/commits` API 호출
  - [ ] 날짜 범위 필터
  - [ ] 페이지네이션 처리
- [ ] 토론 (Discussions) 수집 (선택사항)
  - [ ] GraphQL API 사용
  - [ ] 토론 및 댓글 수집

**데이터 정규화:**
- [ ] Markdown 포맷 정제
  - [ ] 코드 블록 처리
  - [ ] 링크 정규화
  - [ ] 테이블 변환
- [ ] 사용자 정보
  - [ ] GitHub 로그인 → 실명 변환
  - [ ] 프로필 정보 수집
- [ ] 타임스탐프 정규화
  - [ ] ISO 8601 포맷 통일
  - [ ] 타임존 처리

**백그라운드 작업:**
- [ ] 비동기 처리 (Celery/APScheduler)
- [ ] 진행 상황 추적
- [ ] 실패 시 재시도
- [ ] 작업 큐 관리

#### 프런트엔드
**상태:** ❌ 미구현

- [ ] 저장소 선택 화면
  - [ ] 저장소 목록
  - [ ] 검색 기능
  - [ ] 다중 선택
- [ ] 수집 대상 선택
  - [ ] Issues/PRs/Commits 체크박스
- [ ] 날짜 범위 선택
- [ ] 수집 진행 화면

---

### 2.3 GitHub 데이터 분석 및 시나리오 생성

#### 백엔드
**상태:** ❌ 미구현

**토론 분석 로직:**
- [ ] Issue 스레드 분석
  - [ ] 이슈 설명 + 댓글 병합
  - [ ] 토론 흐름 파악
  - [ ] 의견 충돌 감지
- [ ] PR 리뷰 분석
  - [ ] PR 설명 + 리뷰 병합
  - [ ] 코드 리뷰 대화
  - [ ] 피드백 및 응답
- [ ] 주제 추출
  - [ ] 기술 토픽 (언어, 라이브러리 등)
  - [ ] 비즈니스 토픽 (기능, 버그 등)
- [ ] 참가자 식별

**API 엔드포인트:**
- [ ] `POST /roleplaying/github/scenarios/analyze` (Slack과 유사)
  - [ ] GitHub 데이터 입력
  - [ ] 시나리오 + 고정 질문 생성

---

## 3. 통합 데이터 관리 (Unified Data Management)

### 3.1 통합 데이터 모델

#### 백엔드

**ConversationSource 테이블 (공통)**
- [ ] id (기본 키)
- [ ] user_id
- [ ] source_type (slack/github)
- [ ] source_id (Slack: workspace_id, GitHub: repository_id)
- [ ] source_name
- [ ] metadata (JSON)
  - [ ] Slack: workspace_name, channel_id, channel_name
  - [ ] GitHub: owner, repo, issue_id, pr_number 등
- [ ] message_count (수집된 메시지/댓글 수)
- [ ] last_synced_at (마지막 동기화 시간)
- [ ] created_at, updated_at

**ConversationMessage 테이블 (통합)**
- [ ] id
- [ ] user_id
- [ ] source_type (slack/github)
- [ ] source_message_id (Slack: ts, GitHub: comment_id 등)
- [ ] conversation_source_id (ConversationSource 참조)
- [ ] author_login
- [ ] author_name
- [ ] text (정규화된 메시지)
- [ ] raw_text (원본)
- [ ] message_type (user/system/bot)
- [ ] timestamp
- [ ] parent_message_id (스레드/댓글)
- [ ] metadata (JSON) - 각 플랫폼 특화 정보
- [ ] created_at, updated_at

### 3.2 데이터 동기화 (선택사항)

#### 백엔드

- [ ] 정기적 동기화
  - [ ] 새 메시지/댓글만 수집
  - [ ] 수정/삭제 반영
  - [ ] 스케줄링 (일일, 주간 등)
- [ ] 실시간 동기화 (Webhook)
  - [ ] Slack: Event API
  - [ ] GitHub: Webhooks
  - [ ] 새 메시지 자동 수집

---

## 4. 데이터 흐름 통합 (End-to-End Flow)

### 전체 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 사용자 인증                                              │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐           ┌──────────────┐                │
│ │ Slack OAuth  │           │ GitHub OAuth │                │
│ │ 1.1 인증     │           │ 2.1 인증     │                │
│ └──────────────┘           └──────────────┘                │
│      │ access_token             │ access_token             │
│      ▼                           ▼                          │
│   DB 저장 (암호화)            DB 저장 (암호화)             │
└─────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 데이터 수집                                              │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐           ┌──────────────┐                │
│ │ Slack        │           │ GitHub       │                │
│ │ 1.2 수집     │           │ 2.2 수집     │                │
│ │ - 채널 목록  │           │ - Repo 목록  │                │
│ │ - 메시지     │           │ - Issues     │                │
│ │ - 스레드     │           │ - PRs        │                │
│ │ - 사용자정보 │           │ - Commits    │                │
│ └──────────────┘           └──────────────┘                │
│      │ 백그라운드 작업         │ 백그라운드 작업            │
│      ▼                        ▼                             │
│   SlackMessage              GitHubIssue                     │
│   SlackThread               GitHubComment                   │
│   (+ 정규화, 검증)          GitHubPullRequest              │
│                             (+ 정규화, 검증)               │
└─────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 통합 데이터 모델                                         │
├─────────────────────────────────────────────────────────────┤
│   ConversationSource (Slack/GitHub 메타데이터)              │
│   ConversationMessage (통합 메시지 모델)                    │
│                                                             │
│   API: /integration/slack/channels                         │
│        /integration/slack/import-channels                  │
│        /integration/github/repositories                    │
│        /integration/github/import-data                     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 데이터 분석 & 시나리오 생성                              │
├─────────────────────────────────────────────────────────────┤
│ 1.3 / 2.3 데이터 분석                                      │
│                                                             │
│ POST /roleplaying/internal/scenarios/analyze-conversation  │
│ (또는 GitHub 용 별도 엔드포인트)                           │
│                                                             │
│ 입력: 메시지 배열                                          │
│ 출력: 시나리오 + 고정 질문 (1개 개요 + 3개 상세)          │
│                                                             │
│ LLM 처리:                                                  │
│ - 주제 추출                                                 │
│ - 참가자 식별                                               │
│ - 상황 요약                                                 │
│ - 시나리오 생성                                             │
│ - 고정 질문 생성                                            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. DB 저장                                                  │
├─────────────────────────────────────────────────────────────┤
│ - Subject 테이블에 주제 저장                                │
│ - Scenario 테이블에 시나리오 저장                           │
│ - fixed_questions JSON 저장                                 │
│ - source_type = 'slack' 또는 'github' 기록                 │
│ - conversation_source_id 연결                              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 사용자에게 제시                                          │
├─────────────────────────────────────────────────────────────┤
│ - 롤플레잉 목록 조회 (GET /roleplaying/roleplayList)       │
│ - 롤플레잉 세션 시작 (POST /roleplaying/sessions)          │
│ - WebSocket 실시간 회화 (WS /ws/roleplaying/{session_id})  │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 구현 상세 WBS

### Phase 1: Slack 연동 (우선순위: 높음)

#### 5.1.1 OAuth 인증 (6-8시간)
- [ ] Slack App 생성 (1시간)
- [ ] SlackOAuthToken 모델 정의 (1시간)
- [ ] OAuth Flow 엔드포인트 구현 (2시간)
  - [ ] GET /integration/slack/auth-url
  - [ ] POST /integration/slack/callback
  - [ ] POST /integration/slack/disconnect
- [ ] 토큰 암호화 및 저장 (2시간)
- [ ] 토큰 갱신 로직 (1시간)
- [ ] 프론트엔드 OAuth 버튼 (1시간)

**체크포인트:** Slack OAuth 완료 후 access_token 획득 가능

#### 5.1.2 메시지 수집 (12-15시간)
- [ ] SlackMessage, SlackThread 모델 (2시간)
- [ ] Slack 클라이언트 구현 (3시간)
  - [ ] slack-sdk 초기화
  - [ ] 기본 메서드 (conversations.list, .history, .replies)
  - [ ] 에러 처리 및 재시도
- [ ] 채널 목록 엔드포인트 (2시간)
  - [ ] GET /integration/slack/channels
- [ ] 메시지 수집 엔드포인트 (3시간)
  - [ ] POST /integration/slack/import-channels
  - [ ] 백그라운드 작업 구현
  - [ ] 진행 상황 추적
- [ ] 데이터 정규화 (2시간)
- [ ] 프론트엔드 UI (3시간)
  - [ ] 채널 선택 화면
  - [ ] 수집 진행 화면

**체크포인트:** Slack 메시지 DB 저장 완료

#### 5.1.3 시나리오 생성 (3시간)
- [x] 분석 로직 (이미 구현됨)
- [ ] 엔드포인트 테스트 및 최적화 (2시간)
- [ ] 프론트엔드 통합 (1시간)

**소계:** 21-26시간

---

### Phase 2: GitHub 연동 (우선순위: 높음)

#### 5.2.1 OAuth 인증 (5-7시간)
- [ ] GitHub App 생성 (1시간)
- [ ] GitHubOAuthToken 모델 (1시간)
- [ ] OAuth Flow 엔드포인트 (2시간)
- [ ] 프론트엔드 (1시간)

**체크포인트:** GitHub OAuth 완료

#### 5.2.2 데이터 수집 (14-18시간)
- [ ] GitHub 모델 정의 (3시간)
  - [ ] GitHubIssue, GitHubComment
  - [ ] GitHubPullRequest
  - [ ] GitHubCommit
- [ ] GitHub 클라이언트 (4시간)
  - [ ] PyGithub 또는 requests 초기화
  - [ ] 각 API 메서드
  - [ ] 에러 처리
- [ ] 저장소 조회 엔드포인트 (2시간)
- [ ] 데이터 수집 엔드포인트 (3시간)
- [ ] 데이터 정규화 (2시간)
- [ ] 프론트엔드 (3시간)

**체크포인트:** GitHub 데이터 DB 저장 완료

#### 5.2.3 시나리오 생성 (3시간)
- [ ] GitHub 데이터 분석 로직 (2시간)
- [ ] 엔드포인트 및 테스트 (1시간)

**소계:** 22-28시간

---

### Phase 3: 통합 및 최적화 (우선순위: 중간)

#### 5.3.1 통합 데이터 모델 (4-6시간)
- [ ] ConversationSource, ConversationMessage 모델 (2시간)
- [ ] 마이그레이션 (1시간)
- [ ] 데이터 마이그레이션 스크립트 (2시간)

#### 5.3.2 동기화 (선택사항, 6-8시간)
- [ ] 정기적 동기화 스케줄러 (2시간)
- [ ] Slack Event API 웹훅 (2시간)
- [ ] GitHub Webhooks (2시간)

#### 5.3.3 성능 및 보안 (4-6시간)
- [ ] 토큰 암호화/복호화 개선 (1시간)
- [ ] Rate limiting 처리 (1시간)
- [ ] 에러 처리 강화 (1시간)
- [ ] 로깅 및 모니터링 (2시간)

**소계:** 14-20시간

---

### Phase 4: 테스트 (우선순위: 높음)

#### 5.4.1 단위 테스트 (6-8시간)
- [ ] Slack 클라이언트 테스트 (2시간)
- [ ] GitHub 클라이언트 테스트 (2시간)
- [ ] 데이터 정규화 테스트 (2시간)
- [ ] OAuth Flow 테스트 (2시간)

#### 5.4.2 통합 테스트 (4-6시간)
- [ ] Slack → DB 통합 테스트 (2시간)
- [ ] GitHub → DB 통합 테스트 (2시간)
- [ ] 시나리오 생성 통합 테스트 (2시간)

#### 5.4.3 E2E 테스트 (3-4시간)
- [ ] 전체 Slack 플로우 테스트 (1시간)
- [ ] 전체 GitHub 플로우 테스트 (1시간)
- [ ] 사용자 시나리오 테스트 (2시간)

**소계:** 13-18시간

---

## 📊 전체 시간 추정

| Phase | Slack | GitHub | 통합 | 테스트 | 합계 |
|-------|-------|--------|-----|--------|------|
| 구현 | 21-26h | 22-28h | 14-20h | - | 57-74h |
| 테스트 | - | - | - | 13-18h | 13-18h |
| **총계** | | | | | **70-92시간** |

---

## 🎯 마일스톤

### M1: Slack 기본 (1주일)
- Slack OAuth 인증 ✓
- 메시지 수집 ✓
- DB 저장 ✓
- 기본 테스트 ✓

### M2: GitHub 기본 (1주일)
- GitHub OAuth 인증 ✓
- 데이터 수집 ✓
- DB 저장 ✓
- 기본 테스트 ✓

### M3: 통합 및 최적화 (4-5일)
- 통합 모델 완성 ✓
- 동기화 (선택) ✓
- 성능 최적화 ✓

### M4: 완전 테스트 (3-4일)
- 전체 E2E 테스트 ✓
- 버그 수정 ✓
- 문서화 ✓

---

## 🔗 관련 API 문서

### Slack
- https://api.slack.com/methods
- https://slack.dev/python-slack-sdk/

### GitHub
- https://docs.github.com/en/rest
- https://pygithub.readthedocs.io/

---

**문서 최종 업데이트:** 2025-11-20
**담당자:** Backend Team
**상태:** 📋 계획 중