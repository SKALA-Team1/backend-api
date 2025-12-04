-- 마이그레이션: scenario_feedback 테이블에 짧은/긴 피드백 컬럼 추가
-- 작성일: 2025-12-04
-- 목적: 기존 comment 컬럼을 final_feedback_short와 final_feedback_long으로 분리

ALTER TABLE `scenario_feedback`
  ADD COLUMN `final_feedback_short` TEXT NULL COMMENT '짧은 피드백 (1-2문장)' AFTER `comment`,
  ADD COLUMN `final_feedback_long` TEXT NULL COMMENT '긴 피드백 (7문장)' AFTER `final_feedback_short`;

-- 기존 comment 컬럼은 유지 (하위 호환성을 위해)
-- 향후 comment 컬럼 삭제 예정 시:
-- ALTER TABLE `scenario_feedback` DROP COLUMN `comment`;
