-- ============================================
-- Database Migration: Add Bilingual Feedback Sections
-- ============================================
--
-- 목적:
--   ScenarioMessage에 structured bilingual feedback 지원 추가
--   feedback_sections JSON 컬럼을 추가하여 발음/문법/관련성 피드백을 한 곳에서 관리
--
-- 변경사항:
--   1. scenario_message 테이블에 feedback_sections JSON 컬럼 추가
--   2. 기존 feedback_text는 유지 (하위호환성)
--   3. SessionFeedback 및 ScenarioMessageFeedback 테이블은 활용하지 않음 (정규화)
--
-- 주의사항:
--   - 이 마이그레이션은 non-breaking change입니다 (기존 데이터 영향 없음)
--   - feedback_sections은 선택사항입니다 (nullable)
--
-- ============================================

-- Step 1: 컬럼 추가 (feedback_sections JSON)
ALTER TABLE scenario_message
ADD COLUMN feedback_sections JSON COMMENT 'Bilingual feedback sections (pronunciation, grammar, relevance)'
AFTER primary_issue;

-- Step 1b: 컬럼 추가 (question_ko - 한글 질문)
ALTER TABLE scenario_message
ADD COLUMN question_ko TEXT COMMENT 'Korean translation of AI question'
AFTER message_text;

-- Step 1c: 컬럼 추가 (recommended_keywords JSON - 추천 키워드)
ALTER TABLE scenario_message
ADD COLUMN recommended_keywords JSON COMMENT 'Recommended keywords for AI question'
AFTER question_ko;

-- Step 2: 기존 데이터와 새로운 스키마의 호환성 확인
-- 새로운 컬럼은 NULL 상태로 추가되므로 기존 데이터는 영향 없음

-- Step 3: 인덱스 추가 (선택사항 - 향후 feedback_sections에서 검색 필요 시)
-- ALTER TABLE scenario_message ADD INDEX idx_feedback_sections
-- ((CAST(feedback_sections AS CHAR(255)))) USING HASH;

-- ============================================
-- Rollback 방법 (필요시):
-- ============================================
-- ALTER TABLE scenario_message DROP COLUMN feedback_sections;

-- ============================================
-- JSON 구조 예시:
-- ============================================
-- [
--   {
--     "type": "pronunciation",
--     "feedback_en": "Pronunciation is clear. Well done!",
--     "feedback_ko": "발음이 명확합니다. 잘했습니다!",
--     "score": 70
--   },
--   {
--     "type": "grammar",
--     "feedback_en": "No grammatical issues detected.",
--     "feedback_ko": "문법 오류가 없습니다.",
--     "score": 80
--   },
--   {
--     "type": "relevance",
--     "feedback_en": "The response lacks specificity regarding the root cause analysis details.",
--     "feedback_ko": "응답이 근본 원인 분석 세부사항에 대한 구체성이 부족합니다.",
--     "score": 40
--   }
-- ]

-- ============================================
-- 쿼리 예시:
-- ============================================

-- 특정 세션의 모든 메시지와 피드백 조회
-- SELECT
--   m.message_id,
--   m.speaker,
--   m.message_text,
--   m.feedback_text,
--   m.feedback_sections
-- FROM scenario_message m
-- WHERE m.session_id = 'SESSION_UUID'
-- ORDER BY m.turn_index;

-- JSON 배열 길이 확인
-- SELECT
--   m.message_id,
--   JSON_LENGTH(m.feedback_sections) AS section_count,
--   m.feedback_sections
-- FROM scenario_message m
-- WHERE m.feedback_sections IS NOT NULL;

-- 특정 피드백 타입만 조회
-- SELECT
--   m.message_id,
--   JSON_EXTRACT(m.feedback_sections, '$[0].feedback_en') AS pronunciation_feedback,
--   JSON_EXTRACT(m.feedback_sections, '$[0].score') AS pronunciation_score
-- FROM scenario_message m
-- WHERE m.feedback_sections IS NOT NULL;