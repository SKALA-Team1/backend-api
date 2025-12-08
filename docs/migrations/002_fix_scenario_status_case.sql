-- ============================================
-- Database Migration: Fix Scenario Status Case
-- ============================================
--
-- Purpose:
--   Ensure scenario.status column stores uppercase values ('DRAFT', 'GENERATED', etc.)
--   aligning with the Java Enum definition.
--
-- Changes:
--   1. Update default value of status column to 'DRAFT'.
--   2. Convert existing lowercase status values to uppercase.
--
-- ============================================

-- Step 1: Update default value (MySQL syntax)
ALTER TABLE scenario
MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'DRAFT';

-- Step 2: Update existing data to uppercase
UPDATE scenario
SET status = UPPER(status)
WHERE status != BINARY UPPER(status);

-- ============================================
-- Rollback:
-- ALTER TABLE scenario MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'draft';
-- ============================================
