# Spring2 통합 사양서: 바이링궐 피드백 & 추천 키워드

## 개요
Python Backend에서 생성되는 **영문/한글 바이링궐 피드백**과 **AI 질문과 함께 제공되는 추천 키워드**를 Spring2 DB에 저장하고 조회할 수 있도록 통합합니다.

---

## 1. 데이터 구조

### 1.1 AI 질문 (Questions)
```json
{
  "question_id": "uuid",
  "session_id": "uuid",
  "turn_number": 5,

  // 영문/한글 이중 언어 지원
  "question_en": "Can you summarize the root cause of the /reports endpoint error?",
  "question_ko": "/reports 엔드포인트 오류의 근본 원인을 요약해줄 수 있나요?",

  // 추천 키워드 (원본 Slack 메시지 기반)
  "recommended_keywords": [
    "root cause analysis",
    "error logging",
    "database query performance"
  ],

  "is_fixed_question": false,
  "created_at": "2025-12-03T10:15:00Z",
  "created_by": "ai_tutor_service"
}
```

### 1.2 피드백 (Feedback)
```json
{
  "feedback_id": "uuid",
  "session_id": "uuid",
  "utterance_id": "uuid",
  "turn_number": 5,

  // 피드백 타입
  "feedback_type": "combined",  // "pronunciation" | "grammar" | "relevance" | "combined"

  // 점수들
  "pronunciation_score": 70,
  "grammar_score": 80,
  "relevance_score": 40,
  "overall_score": 63,

  // 영문/한글 이중 언어 지원
  "feedback_sections": [
    {
      "type": "pronunciation",
      "feedback_en": "Pronunciation is clear. Well done!",
      "feedback_ko": "발음이 명확합니다. 잘했습니다!"
    },
    {
      "type": "grammar",
      "feedback_en": "No grammatical issues detected.",
      "feedback_ko": "문법 오류가 없습니다."
    },
    {
      "type": "relevance",
      "feedback_en": "The response lacks specificity regarding the root cause analysis details.",
      "feedback_ko": "응답이 근본 원인 분석 세부사항에 대한 구체성이 부족합니다."
    }
  ],

  // 메타정보
  "needs_correction": true,
  "primary_issue": "relevance",
  "retry_count": 1,
  "max_retries": 3,

  "created_at": "2025-12-03T10:15:30Z",
  "created_by": "feedback_orchestrator"
}
```

---

## 2. API 명세

### 2.1 질문 저장 (POST)
**Endpoint**: `/api/sessions/{session_id}/questions`

**Request** (Python FastAPI → Spring2):
```json
{
  "turn_number": 5,
  "question_en": "Can you summarize...",
  "question_ko": "/reports 엔드포인트...",
  "recommended_keywords": ["root cause analysis", "error logging", "..."],
  "is_fixed_question": false,
  "scenario_id": "scenario-uuid"
}
```

**Response** (Spring2 → Python FastAPI):
```json
{
  "success": true,
  "question_id": "q-12345",
  "message": "Question saved successfully"
}
```

### 2.2 피드백 저장 (POST)
**Endpoint**: `/api/sessions/{session_id}/feedback`

**Request** (Python FastAPI → Spring2):
```json
{
  "turn_number": 5,
  "utterance_id": "utt-12345",
  "feedback_type": "combined",

  "scores": {
    "pronunciation_score": 70,
    "grammar_score": 80,
    "relevance_score": 40,
    "overall_score": 63
  },

  "feedback_sections": [
    {
      "type": "pronunciation",
      "feedback_en": "...",
      "feedback_ko": "..."
    },
    {
      "type": "grammar",
      "feedback_en": "...",
      "feedback_ko": "..."
    },
    {
      "type": "relevance",
      "feedback_en": "...",
      "feedback_ko": "..."
    }
  ],

  "needs_correction": true,
  "primary_issue": "relevance",
  "retry_count": 1,
  "max_retries": 3
}
```

**Response** (Spring2 → Python FastAPI):
```json
{
  "success": true,
  "feedback_id": "fb-12345",
  "message": "Feedback saved successfully"
}
```

### 2.3 질문 조회 (GET)
**Endpoint**: `/api/sessions/{session_id}/questions/{question_id}`

**Response**:
```json
{
  "question_id": "q-12345",
  "question_en": "...",
  "question_ko": "...",
  "recommended_keywords": [...],
  "is_fixed_question": false,
  "created_at": "2025-12-03T10:15:00Z"
}
```

### 2.4 피드백 조회 (GET)
**Endpoint**: `/api/sessions/{session_id}/feedback/{feedback_id}`

**Response**:
```json
{
  "feedback_id": "fb-12345",
  "feedback_type": "combined",
  "scores": {...},
  "feedback_sections": [...],
  "needs_correction": true,
  "primary_issue": "relevance",
  "created_at": "2025-12-03T10:15:30Z"
}
```

---

## 3. DB 스키마

### 3.1 Questions 테이블
```sql
CREATE TABLE questions (
  question_id VARCHAR(36) PRIMARY KEY,
  session_id VARCHAR(36) NOT NULL,
  turn_number INT NOT NULL,

  -- 바이링궐 지원
  question_en TEXT NOT NULL,
  question_ko TEXT NOT NULL,

  -- 추천 키워드 (JSON 배열)
  recommended_keywords JSON,

  -- 메타정보
  is_fixed_question BOOLEAN DEFAULT FALSE,
  scenario_id VARCHAR(36),

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (session_id) REFERENCES sessions(session_id),
  INDEX idx_session_turn (session_id, turn_number)
);
```

### 3.2 Feedback 테이블
```sql
CREATE TABLE feedback (
  feedback_id VARCHAR(36) PRIMARY KEY,
  session_id VARCHAR(36) NOT NULL,
  utterance_id VARCHAR(36) NOT NULL,
  turn_number INT NOT NULL,

  -- 피드백 타입
  feedback_type VARCHAR(50) NOT NULL,  -- 'pronunciation', 'grammar', 'relevance', 'combined'

  -- 점수들
  pronunciation_score INT,
  grammar_score INT,
  relevance_score INT,
  overall_score INT,

  -- 바이링궐 피드백 섹션 (JSON 배열)
  feedback_sections JSON NOT NULL,

  -- 메타정보
  needs_correction BOOLEAN DEFAULT FALSE,
  primary_issue VARCHAR(50),  -- 'pronunciation', 'grammar', 'relevance', 'none'
  retry_count INT DEFAULT 0,
  max_retries INT DEFAULT 3,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (session_id) REFERENCES sessions(session_id),
  FOREIGN KEY (utterance_id) REFERENCES utterances(utterance_id),
  INDEX idx_session_turn (session_id, turn_number),
  INDEX idx_feedback_type (feedback_type)
);
```

### 3.3 Feedback Sections 스키마 (JSON)
```sql
-- feedback_sections JSON 구조
[
  {
    "type": "pronunciation",
    "feedback_en": "string",
    "feedback_ko": "string",
    "score": integer
  },
  {
    "type": "grammar",
    "feedback_en": "string",
    "feedback_ko": "string",
    "score": integer
  },
  {
    "type": "relevance",
    "feedback_en": "string",
    "feedback_ko": "string",
    "score": integer
  }
]
```

---

## 4. 데이터 흐름

```
Python FastAPI
    ↓
[1] AI 질문 생성
    - 영문 질문: FOLLOWUP_QUESTION_PROMPT
    - 한글 질문: QUESTION_BILINGUAL_PROMPT로 번역
    - 추천 키워드: RECOMMENDED_KEYWORDS_PROMPT (Slack 메시지 기반)
    ↓
[2] POST /api/sessions/{session_id}/questions
    → Spring2에 저장
    ↓

[1] 사용자 응답 평가
    - 발음: PronunciationEvaluatorImpl (Azure + LLM)
    - 문법: GrammarEvaluatorImpl (LLM)
    - 관련성: RelevanceEvaluatorImpl (LLM)
    ↓
[2] 영문/한글 번역
    - 발음 피드백: 영문 생성 → 한글 번역
    - 문법 피드백: 영문 생성 → 한글 번역
    - 관련성 피드백: 영문 생성 → 한글 번역
    ↓
[3] POST /api/sessions/{session_id}/feedback
    → Spring2에 저장
    ↓

웹 클라이언트 (학습자)
    ↓
[GET] /api/sessions/{session_id}/questions/{question_id}
    ← 영문/한글 질문 + 추천 키워드
    ↓
[사용자 답변]
    ↓
[GET] /api/sessions/{session_id}/feedback/{feedback_id}
    ← 영문/한글 피드백 (발음/문법/관련성)
```

---

## 5. 주요 고려사항

### 5.1 성능
- **Indexing**: session_id + turn_number 복합 인덱스로 조회 성능 향상
- **JSON 컬럼**: feedback_sections, recommended_keywords는 JSON으로 저장 (유연성)
- **배치 저장**: 여러 피드백을 한 번에 저장하는 경우 트랜잭션 활용

### 5.2 보안
- **접근 제어**: session_id로 사용자 데이터 격리
- **검증**: 모든 입력값 길이 제한 및 SQL Injection 방지
- **감사로그**: created_by, created_at로 데이터 소스 추적

### 5.3 확장성
- **국제화**: 향후 더 많은 언어 추가 시 feedback_sections 확장
- **버전관리**: feedback_type 추가 시 기존 데이터 호환성 유지
- **마이그레이션**: 기존 utterances 테이블의 피드백 필드와 분리

### 5.4 호환성
- **기존 데이터**: 기존 utterances 테이블의 feedback 필드는 유지 (마이그레이션 단계별 진행)
- **Fallback**: 바이링궐 데이터 없을 경우 영문만 제공
- **레거시 API**: 기존 API 엔드포인트도 계속 지원

---

## 6. 마이그레이션 전략

### Phase 1: 새 테이블 생성 (선택적, 권장)
```sql
-- Questions 테이블
CREATE TABLE questions (...);

-- Feedback 테이블 (별도)
CREATE TABLE feedback (...);
```

### Phase 2: 기존 데이터 통합 (선택사항)
- utterances.feedback 데이터 → feedback 테이블로 마이그레이션
- feedback_sections JSON으로 변환

### Phase 3: API 배포
- 새로운 엔드포인트 활성화
- 기존 엔드포인트와 병행 운영

---

## 7. 테스트 체크리스트

### Backend → Spring2 통신
- [ ] POST /api/sessions/{session_id}/questions 정상 작동
- [ ] POST /api/sessions/{session_id}/feedback 정상 작동
- [ ] 대량 저장 시 성능 (1000개 이상)
- [ ] 트랜잭션 롤백 시 일관성
- [ ] 중복 저장 방지 (idempotency)

### DB 검증
- [ ] 복합 인덱스 효율성 (실행 계획 확인)
- [ ] JSON 쿼리 성능 (WHERE절에 JSON_EXTRACT 사용)
- [ ] 데이터 integrity (FK 제약)

### 클라이언트 조회
- [ ] GET /api/sessions/{session_id}/questions/{question_id}
- [ ] GET /api/sessions/{session_id}/feedback/{feedback_id}
- [ ] 영문/한글 모두 포함 여부

---

## 8. 문의

Python Backend 담당자: [이메일 또는 연락처]