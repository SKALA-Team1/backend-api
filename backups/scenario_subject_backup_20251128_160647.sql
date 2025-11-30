-- MySQL dump 10.13  Distrib 9.5.0, for macos15.7 (arm64)
--
-- Host: localhost    Database: SKUseme_DB
-- ------------------------------------------------------
-- Server version	9.5.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '21df2dfe-be0e-11f0-b8d9-d58f4eda592e:1-477,
c6cddc84-c679-11f0-9535-782a67856879:1-497';

--
-- Table structure for table `scenario`
--

DROP TABLE IF EXISTS `scenario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `scenario` (
  `scenario_id` bigint NOT NULL AUTO_INCREMENT,
  `subject_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `title` varchar(200) NOT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'draft',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ai_role` varchar(100) DEFAULT NULL,
  `topic_type` varchar(50) DEFAULT NULL,
  `fixed_questions` json DEFAULT NULL,
  PRIMARY KEY (`scenario_id`),
  KEY `idx_scenario_subject_id` (`subject_id`),
  KEY `idx_scenario_user_id` (`user_id`),
  CONSTRAINT `fk_scenario_subject` FOREIGN KEY (`subject_id`) REFERENCES `subject` (`subject_id`),
  CONSTRAINT `fk_scenario_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scenario`
--

LOCK TABLES `scenario` WRITE;
/*!40000 ALTER TABLE `scenario` DISABLE KEYS */;
INSERT INTO `scenario` VALUES (1,1,1,'Project Manager Overview Sync | Project Manager\'s Overview: Backend System Deployment Issue - Reports Endpoint Error Impact Analysis','GENERATED','2025-11-18 17:46:09','2025-11-18 17:46:09','Project Manager','overview','[\"Can you summarize the root cause of the /reports endpoint error after enabling finance advanced filters?\", \"How do you plan to implement a temporary workaround for the Redis connection pool issues, and what\'s the expected impact on system performance?\", \"What are the next steps to resolve the issue, and when can we expect a fix or further updates from your team?\"]'),(2,2,1,'Project Manager Overview Sync | Project Manager\'s Overview: Reports Endpoint Error Impact on Finance Advanced Filter Toggles','GENERATED','2025-11-18 17:50:48','2025-11-18 17:50:48','Project Manager','overview','[\"Hi, can you tell me about the main problem of today\'s issue with reports endpoint returns 500 error when finance toggles advanced filters?\", \"How do you plan to address the technical challenges caused by hitting the max connection pool in Redis due to high load?\", \"What are the key action items your team will focus on to resolve this issue and prevent similar issues in the future?\"]'),(3,2,1,'Project Manager Deep Dive Focus | Project Manager\'s Review: \'500 Error Rate Reduction in Finance Advanced Filter Reports\' - Technical Analysis','GENERATED','2025-11-18 17:50:48','2025-11-18 17:50:48','Project Manager','detail','[\"What are the top concerns that led to implementing a temporary fix for the reports endpoint issue?\", \"Can you elaborate on the technical details behind the failover process and how it affects Redis CPU usage?\", \"Before we move forward with further investigation, what is the expected timeline for resolving this issue and when can we expect a more permanent solution?\"]'),(4,2,1,'Tech Lead Deep Dive Focus | Tech Lead Analysis: 500 Error Rate Optimization for Finance Advanced Filters in Reports Endpoint','GENERATED','2025-11-18 17:50:48','2025-11-18 17:50:48','Tech Lead','detail','[\"Hi! Can you tell me about the main problem with the reports endpoint when finance toggles advanced filters?\", \"How do you plan to address the technical challenges that caused the Redis connection pool to reach its max capacity?\", \"Before we wrap up, what are the key action items you\'ll focus on to resolve this issue and ensure it doesn\'t happen again in the future?\"]'),(5,2,1,'QA Engineer Deep Dive Focus | QA Engineer Deep Dive: Reports Endpoint Error Rate Analysis - Finance Advanced Filters','GENERATED','2025-11-18 17:50:48','2025-11-18 17:50:48','QA Engineer','detail','[\"Can you walk me through the steps taken to resolve the Redis connection pool issue and its impact on the reports endpoint?\", \"How does the temporary restriction implemented earlier fit into your overall plan to address the technical challenges with the advanced filters?\", \"Before we move forward, can you confirm that the key action items for resolving the reports endpoint issue are being tracked and assigned to specific team members?\"]');
/*!40000 ALTER TABLE `scenario` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subject`
--

DROP TABLE IF EXISTS `subject`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subject` (
  `subject_id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `slack_message_id` bigint DEFAULT NULL,
  `github_issue_id` bigint DEFAULT NULL,
  `creation_type` varchar(255) NOT NULL,
  `creation_type_detail` varchar(255) DEFAULT NULL,
  `my_role` text,
  `ai_role` text,
  `situation` text,
  `topic_type` enum('overview','detail') DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `conversation_date` date DEFAULT NULL,
  `message_count` int DEFAULT NULL,
  PRIMARY KEY (`subject_id`),
  KEY `idx_subject_user_id` (`user_id`),
  KEY `idx_subject_slack_message_id` (`slack_message_id`),
  KEY `idx_subject_github_issue_id` (`github_issue_id`),
  CONSTRAINT `fk_subject_github_issue` FOREIGN KEY (`github_issue_id`) REFERENCES `github_issue` (`github_issue_id`),
  CONSTRAINT `fk_subject_slack_message` FOREIGN KEY (`slack_message_id`) REFERENCES `slack_message` (`slack_message_id`),
  CONSTRAINT `fk_subject_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subject`
--

LOCK TABLES `subject` WRITE;
/*!40000 ALTER TABLE `subject` DISABLE KEYS */;
INSERT INTO `subject` VALUES (1,1,NULL,NULL,'slack',NULL,'Backend Engineer',NULL,'Discussing backend system deployment issue with /reports endpoint error after finance advanced filters toggle.',NULL,'2025-11-18 17:46:09','2025-11-18 17:46:09','2025-02-20',6),(2,1,NULL,NULL,'slack',NULL,'Backend Engineer',NULL,'Reports endpoint returns 500 error when finance toggles advanced filters; temporary restriction implemented to resolve issue.',NULL,'2025-11-18 17:50:48','2025-11-18 17:50:48','2025-02-20',6);
/*!40000 ALTER TABLE `subject` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-28 16:06:48
