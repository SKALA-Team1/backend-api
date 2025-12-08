-- user 테이블
CREATE TABLE IF NOT EXISTS `user` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `profile_image_url` VARCHAR(512),
  `auth_provider` VARCHAR(50) NOT NULL,
  `provider_user_id` VARCHAR(255),
  `job_role` VARCHAR(100),
  `team_name` VARCHAR(100),
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `password_hash` VARCHAR(255),
  `terms_agreed` TINYINT(1) NOT NULL DEFAULT 0,
  `onboarding_completed` TINYINT(1) NOT NULL DEFAULT 0,
  `refresh_token` TEXT,
  `refresh_token_expires_at` DATETIME,
  `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `role` VARCHAR(255) NOT NULL DEFAULT 'ROLE_USER',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_user_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- email_verification
-- (Postgres에서 length 미지정 varchar → 여기서는 255로 통일)
CREATE TABLE IF NOT EXISTS `email_verification` (
  `email` VARCHAR(255) NOT NULL,
  `code` VARCHAR(255) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- reference
CREATE TABLE IF NOT EXISTS `reference` (
  `reference_id` BIGINT NOT NULL AUTO_INCREMENT,
  `document` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reference_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- github_issue
CREATE TABLE IF NOT EXISTS `github_issue` (
  `github_issue_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `repo_owner` VARCHAR(100) NOT NULL,
  `repo_name` VARCHAR(200) NOT NULL,
  `issue_number` INT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `body` TEXT,
  `state` VARCHAR(30),
  `external_created_at` DATETIME,
  `external_updated_at` DATETIME,
  `closed_at` DATETIME,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`github_issue_id`),

  CONSTRAINT `uk_github_issue_repo_number`
      UNIQUE (`repo_owner`, `repo_name`, `issue_number`),
  CONSTRAINT `fk_github_issue_user`
      FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- integration
CREATE TABLE IF NOT EXISTS `integration` (
  `integration_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `provider` VARCHAR(50) NOT NULL,
  `access_token` TEXT,
  `refresh_token` TEXT,
  `token_expires_at` DATETIME,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`integration_id`),
  KEY `idx_integration_user_id` (`user_id`),
  CONSTRAINT `fk_integration_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- notification
CREATE TABLE IF NOT EXISTS `notification` (
  `notification_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `push_token` VARCHAR(512),
  `on_off` TINYINT(1) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  KEY `idx_notification_user_id` (`user_id`),
  CONSTRAINT `fk_notification_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- project
CREATE TABLE IF NOT EXISTS `project` (
  `project_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `creation_type` VARCHAR(50) NOT NULL,
  `project_name` VARCHAR(200) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`project_id`),
  KEY `idx_project_user_id` (`user_id`),
  CONSTRAINT `fk_project_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- slack_message
CREATE TABLE IF NOT EXISTS `slack_message` (
  `slack_message_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `message_ts` DATETIME NOT NULL,
  `sender_name` VARCHAR(100),
  `text` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`slack_message_id`),
  KEY `idx_slack_message_user_id` (`user_id`),
  CONSTRAINT `fk_slack_message_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- subject (topic_type_enum → ENUM)
CREATE TABLE IF NOT EXISTS `subject` (
  `subject_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `slack_message_id` BIGINT,
  `github_issue_id` BIGINT,
  `creation_type` VARCHAR(255) NOT NULL,
  `creation_type_detail` VARCHAR(255),
  `my_role` TEXT,
  `ai_role` TEXT,
  `situation` TEXT,
  `topic_type` ENUM('overview', 'detail'),
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `conversation_date` DATE,
  `message_count` INT,
  PRIMARY KEY (`subject_id`),
  KEY `idx_subject_user_id` (`user_id`),
  KEY `idx_subject_slack_message_id` (`slack_message_id`),
  KEY `idx_subject_github_issue_id` (`github_issue_id`),
  CONSTRAINT `fk_subject_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`),
  CONSTRAINT `fk_subject_slack_message` FOREIGN KEY (`slack_message_id`) REFERENCES `slack_message`(`slack_message_id`),
  CONSTRAINT `fk_subject_github_issue` FOREIGN KEY (`github_issue_id`) REFERENCES `github_issue`(`github_issue_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario
CREATE TABLE IF NOT EXISTS `scenario` (
  `scenario_id` BIGINT NOT NULL AUTO_INCREMENT,
  `subject_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `title` VARCHAR(200) NOT NULL,
  `status` VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ai_role` VARCHAR(100),
  `topic_type` VARCHAR(50),
  PRIMARY KEY (`scenario_id`),
  KEY `idx_scenario_subject_id` (`subject_id`),
  KEY `idx_scenario_user_id` (`user_id`),
  CONSTRAINT `fk_scenario_subject` FOREIGN KEY (`subject_id`) REFERENCES `subject`(`subject_id`),
  CONSTRAINT `fk_scenario_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario_session
CREATE TABLE IF NOT EXISTS `scenario_session` (
  `session_id` BIGINT NOT NULL AUTO_INCREMENT,
  `scenario_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `status` VARCHAR(30) NOT NULL,
  `total_turns_planned` INT NOT NULL,
  `played_turns` INT NOT NULL DEFAULT 0,
  `completed_all_turns` TINYINT(1) NOT NULL DEFAULT 0,
  `finish_reason` VARCHAR(50),
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME,
  PRIMARY KEY (`session_id`),
  KEY `idx_scenario_session_scenario_id` (`scenario_id`),
  KEY `idx_scenario_session_user_id` (`user_id`),
  CONSTRAINT `fk_scenario_session_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario`(`scenario_id`),
  CONSTRAINT `fk_scenario_session_user` FOREIGN KEY (`user_id`) REFERENCES `user`(`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario_message
CREATE TABLE IF NOT EXISTS `scenario_message` (
  `message_id` BIGINT NOT NULL AUTO_INCREMENT,
  `session_id` BIGINT NOT NULL,
  `turn_index` INT NOT NULL,
  `speaker` VARCHAR(30) NOT NULL,
  `message_text` TEXT NOT NULL,
  `audio_url` TEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  KEY `idx_scenario_message_session_id` (`session_id`),
  CONSTRAINT `fk_scenario_message_session` FOREIGN KEY (`session_id`) REFERENCES `scenario_session`(`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario_feedback
CREATE TABLE IF NOT EXISTS `scenario_feedback` (
  `feedback_id` BIGINT NOT NULL AUTO_INCREMENT,
  `session_id` BIGINT NOT NULL,
  `scenario_id` BIGINT NOT NULL,
  `total_pronunciation` DECIMAL(5,2),
  `total_grammar` DECIMAL(5,2),
  `total_diversity` DECIMAL(5,2),
  `total_score` DECIMAL(5,2),
  `comment` TEXT,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`feedback_id`),
  KEY `idx_scenario_feedback_session_id` (`session_id`),
  KEY `idx_scenario_feedback_scenario_id` (`scenario_id`),
  CONSTRAINT `fk_scenario_feedback_session` FOREIGN KEY (`session_id`) REFERENCES `scenario_session`(`session_id`),
  CONSTRAINT `fk_scenario_feedback_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario`(`scenario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario_message_feedback
CREATE TABLE IF NOT EXISTS `scenario_message_feedback` (
  `feedback_id` BIGINT NOT NULL AUTO_INCREMENT,
  `message_id` BIGINT NOT NULL,
  `session_id` BIGINT NOT NULL,
  `original_expression` TEXT,
  `suggested_expression` TEXT,
  `pronunciation` DECIMAL(5,2),
  `grammar` DECIMAL(5,2),
  `diversity` DECIMAL(5,2),
  `score` DECIMAL(5,2),
  `criterion` VARCHAR(50),
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`feedback_id`),
  KEY `idx_scenario_msg_feedback_message_id` (`message_id`),
  KEY `idx_scenario_msg_feedback_session_id` (`session_id`),
  CONSTRAINT `fk_scenario_msg_feedback_message` FOREIGN KEY (`message_id`) REFERENCES `scenario_message`(`message_id`),
  CONSTRAINT `fk_scenario_msg_feedback_session` FOREIGN KEY (`session_id`) REFERENCES `scenario_session`(`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- scenario_reference
CREATE TABLE IF NOT EXISTS `scenario_reference` (
  `scenario_id` BIGINT NOT NULL,
  `reference_id` BIGINT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`scenario_id`, `reference_id`),
  KEY `idx_scenario_reference_reference_id` (`reference_id`),
  CONSTRAINT `fk_scenario_reference_scenario` FOREIGN KEY (`scenario_id`) REFERENCES `scenario`(`scenario_id`),
  CONSTRAINT `fk_scenario_reference_reference` FOREIGN KEY (`reference_id`) REFERENCES `reference`(`reference_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE scenario
    ADD COLUMN fixed_questions JSON NULL AFTER topic_type;

