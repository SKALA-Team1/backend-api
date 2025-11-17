CREATE DATABASE skuseme_db
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE skuseme_db;

 CREATE TABLE `user` (
  user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(100) NOT NULL,
  profile_image_url VARCHAR(512),
  auth_provider VARCHAR(50) NOT NULL,
  provider_user_id VARCHAR(255),
  job_role VARCHAR(100),
  team_name VARCHAR(100),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uk_user_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification (
  notification_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  push_token VARCHAR(512),
  on_off TINYINT(1) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (notification_id),
  CONSTRAINT fk_notification_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE integration (
  integration_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  provider VARCHAR(50) NOT NULL,     -- 'slack', 'github'
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (integration_id),
  CONSTRAINT fk_integration_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE project (
  project_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  creation_type VARCHAR(50) NOT NULL, -- 'prompt', 'slack_auto', 'github_auto'
  project_name VARCHAR(200) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (project_id),
  CONSTRAINT fk_project_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE slack_message (
  slack_message_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  message_ts TIMESTAMP NOT NULL,
  sender_name VARCHAR(100),
  text TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (slack_message_id),
  CONSTRAINT fk_slack_message_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id),
  KEY idx_slack_message_user_date (user_id, message_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE github_issue (
  github_issue_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  repo_owner VARCHAR(100) NOT NULL,
  repo_name VARCHAR(200) NOT NULL,
  issue_number INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  body TEXT,
  state VARCHAR(30),
  external_created_at TIMESTAMP NULL,
  external_updated_at TIMESTAMP NULL,
  closed_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (github_issue_id),
  CONSTRAINT fk_github_issue_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id),
  UNIQUE KEY uk_github_issue_repo_number (repo_owner, repo_name, issue_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE subject (
  subject_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  slack_message_id BIGINT UNSIGNED NULL,
  github_issue_id BIGINT UNSIGNED NULL,
  creation_type VARCHAR(50) NOT NULL,       -- 'prompt', 'slack', 'github'
  creation_type_detail VARCHAR(100),
  my_role TEXT,
  ai_role TEXT,
  situation TEXT,
  topic_type ENUM('overview', 'detail'),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (subject_id),
  CONSTRAINT fk_subject_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id),
  CONSTRAINT fk_subject_slack_message
    FOREIGN KEY (slack_message_id) REFERENCES slack_message(slack_message_id),
  CONSTRAINT fk_subject_github_issue
    FOREIGN KEY (github_issue_id) REFERENCES github_issue(github_issue_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario (
  scenario_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  subject_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(200) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'draft',   -- 'draft', 'ready', 'archived'
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (scenario_id),
  CONSTRAINT fk_scenario_subject
    FOREIGN KEY (subject_id) REFERENCES subject(subject_id),
  CONSTRAINT fk_scenario_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario_session (
  session_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scenario_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  status VARCHAR(30) NOT NULL, -- 'IN_PROGRESS', 'FINISHED'
  total_turns_planned INT NOT NULL,
  played_turns INT NOT NULL DEFAULT 0,
  completed_all_turns TINYINT(1) NOT NULL DEFAULT 0,
  finish_reason VARCHAR(50),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  finished_at TIMESTAMP NULL,
  PRIMARY KEY (session_id),
  CONSTRAINT fk_scenario_session_scenario
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id),
  CONSTRAINT fk_scenario_session_user
    FOREIGN KEY (user_id) REFERENCES `user`(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario_message (
  message_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  session_id BIGINT UNSIGNED NOT NULL,
  turn_index INT NOT NULL,
  speaker VARCHAR(30) NOT NULL,  -- 'ai', 'user'
  message_text TEXT NOT NULL,
  audio_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (message_id),
  CONSTRAINT fk_scenario_message_session
    FOREIGN KEY (session_id) REFERENCES scenario_session(session_id),
  KEY idx_scenario_message_session_turn (session_id, turn_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario_message_feedback (
  feedback_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  message_id BIGINT UNSIGNED NOT NULL,
  session_id BIGINT UNSIGNED NOT NULL,
  original_expression TEXT,
  suggested_expression TEXT,
  pronunciation DECIMAL(5,2),
  grammar DECIMAL(5,2),
  diversity DECIMAL(5,2),
  score DECIMAL(5,2),
  criterion VARCHAR(50),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (feedback_id),
  CONSTRAINT fk_scenario_message_feedback_message
    FOREIGN KEY (message_id) REFERENCES scenario_message(message_id),
  CONSTRAINT fk_scenario_message_feedback_session
    FOREIGN KEY (session_id) REFERENCES scenario_session(session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario_feedback (
  feedback_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  session_id BIGINT UNSIGNED NOT NULL,
  scenario_id BIGINT UNSIGNED NOT NULL,
  total_pronunciation DECIMAL(5,2),
  total_grammar DECIMAL(5,2),
  total_diversity DECIMAL(5,2),
  total_score DECIMAL(5,2),
  comment TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (feedback_id),
  CONSTRAINT fk_scenario_feedback_session
    FOREIGN KEY (session_id) REFERENCES scenario_session(session_id),
  CONSTRAINT fk_scenario_feedback_scenario
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE reference_doc (
  reference_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  document TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (reference_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE scenario_reference (
  scenario_id BIGINT UNSIGNED NOT NULL,
  reference_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (scenario_id, reference_id),
  CONSTRAINT fk_scenario_reference_scenario
    FOREIGN KEY (scenario_id) REFERENCES scenario(scenario_id),
  CONSTRAINT fk_scenario_reference_reference
    FOREIGN KEY (reference_id) REFERENCES reference_doc(reference_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;