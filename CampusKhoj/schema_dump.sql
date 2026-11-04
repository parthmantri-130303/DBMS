-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: campuskhoj_zero
-- ------------------------------------------------------
-- Server version	8.0.46

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

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `log_id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `action` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `details` json DEFAULT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`log_id`),
  KEY `fk_audit_user` (`user_id`),
  KEY `idx_audit_query` (`entity_type`,`entity_id`,`created_at`),
  CONSTRAINT `fk_audit_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=245 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `campuses`
--

DROP TABLE IF EXISTS `campuses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `campuses` (
  `campus_id` tinyint NOT NULL,
  `campus_name` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`campus_id`),
  UNIQUE KEY `campus_name` (`campus_name`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `categories`
--

DROP TABLE IF EXISTS `categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categories` (
  `category_id` smallint NOT NULL AUTO_INCREMENT,
  `category_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `icon` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT 'package',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `claim_messages`
--

DROP TABLE IF EXISTS `claim_messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `claim_messages` (
  `message_id` bigint NOT NULL AUTO_INCREMENT,
  `claim_id` int NOT NULL,
  `sender_id` int NOT NULL,
  `sender_role` enum('STUDENT','STAFF') COLLATE utf8mb4_unicode_ci NOT NULL,
  `message_text` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `sent_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `read_at` datetime DEFAULT NULL,
  PRIMARY KEY (`message_id`),
  KEY `fk_msg_sender` (`sender_id`),
  KEY `idx_claim_messages` (`claim_id`,`sent_at`),
  CONSTRAINT `fk_msg_claim` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`claim_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_sender` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `claim_verifications`
--

DROP TABLE IF EXISTS `claim_verifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `claim_verifications` (
  `verification_id` int NOT NULL AUTO_INCREMENT,
  `claim_id` int NOT NULL,
  `question` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expected_evidence` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `answer` text COLLATE utf8mb4_unicode_ci,
  `verification_status` enum('ASKED','ANSWERED','VERIFIED','FAILED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ASKED',
  `asked_by` int NOT NULL,
  `verified_by` int DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`verification_id`),
  KEY `fk_verif_claim` (`claim_id`),
  KEY `fk_verif_asked_by` (`asked_by`),
  KEY `fk_verif_verified_by` (`verified_by`),
  CONSTRAINT `fk_verif_asked_by` FOREIGN KEY (`asked_by`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_verif_claim` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`claim_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_verif_verified_by` FOREIGN KEY (`verified_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `claims`
--

DROP TABLE IF EXISTS `claims`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `claims` (
  `claim_id` int NOT NULL AUTO_INCREMENT,
  `found_id` int NOT NULL,
  `lost_id` int DEFAULT NULL,
  `claimant_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `claim_description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `proof_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proof_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `claim_status` enum('PENDING','UNDER_REVIEW','APPROVED','REJECTED','COMPLETED','CANCELLED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `reject_reason` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `submitted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `reviewed_at` datetime DEFAULT NULL,
  `reviewed_by` int DEFAULT NULL,
  `handed_over_at` datetime DEFAULT NULL,
  `handed_over_by` int DEFAULT NULL,
  `active_key` tinyint GENERATED ALWAYS AS ((case when (`claim_status` in (_utf8mb4'PENDING',_utf8mb4'UNDER_REVIEW',_utf8mb4'APPROVED')) then 1 else NULL end)) STORED,
  PRIMARY KEY (`claim_id`),
  UNIQUE KEY `uq_claim_active` (`found_id`,`claimant_id`,`active_key`),
  KEY `fk_claim_lost` (`lost_id`),
  KEY `fk_claim_claimant` (`claimant_id`),
  KEY `fk_claim_reviewed_by` (`reviewed_by`),
  KEY `fk_claim_handed_over_by` (`handed_over_by`),
  KEY `idx_claims_search` (`campus_id`,`claim_status`,`submitted_at`),
  CONSTRAINT `fk_claim_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claim_claimant` FOREIGN KEY (`claimant_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claim_found` FOREIGN KEY (`found_id`) REFERENCES `found_items` (`found_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claim_handed_over_by` FOREIGN KEY (`handed_over_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_claim_lost` FOREIGN KEY (`lost_id`) REFERENCES `lost_items` (`lost_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_claim_reviewed_by` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=120 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp850 */ ;
/*!50003 SET character_set_results = cp850 */ ;
/*!50003 SET collation_connection  = cp850_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `trg_claims_status_audit` AFTER UPDATE ON `claims` FOR EACH ROW BEGIN
    IF OLD.claim_status <> NEW.claim_status THEN
        INSERT INTO audit_logs (
            user_id,
            action,
            entity_type,
            entity_id,
            details,
            ip_address,
            created_at
        ) VALUES (
            COALESCE(NEW.handed_over_by, NEW.reviewed_by, NEW.claimant_id),
            CONCAT('CLAIM_STATUS_', NEW.claim_status),
            'CLAIM',
            CAST(NEW.claim_id AS CHAR),
            JSON_OBJECT(
                'claim_id', NEW.claim_id,
                'found_id', NEW.found_id,
                'lost_id', NEW.lost_id,
                'claimant_id', NEW.claimant_id,
                'campus_id', NEW.campus_id,
                'old_status', OLD.claim_status,
                'new_status', NEW.claim_status,
                'reject_reason', NEW.reject_reason
            ),
            '127.0.0.1',
            NOW()
        );
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `found_items`
--

DROP TABLE IF EXISTS `found_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `found_items` (
  `found_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `category_id` smallint NOT NULL,
  `location_id` int NOT NULL,
  `room_no` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `specific_spot` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `item_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `brand` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `color` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `private_details` text COLLATE utf8mb4_unicode_ci,
  `date_found` date NOT NULL,
  `time_found` time DEFAULT NULL,
  `image_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `custody` enum('WITH_FINDER','AT_DESK') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'WITH_FINDER',
  `storage_location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('ACTIVE','MATCHED','CLAIMED','HANDED_OVER','CLOSED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`found_id`),
  KEY `fk_found_user` (`user_id`),
  KEY `fk_found_location_campus` (`location_id`,`campus_id`),
  KEY `idx_found_query` (`campus_id`,`status`,`category_id`,`date_found`),
  KEY `idx_found_date` (`date_found`,`created_at`),
  KEY `idx_found_cat_date` (`category_id`,`date_found`),
  FULLTEXT KEY `ft_found_search` (`item_name`,`description`,`brand`),
  CONSTRAINT `fk_found_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_found_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_found_location_campus` FOREIGN KEY (`location_id`, `campus_id`) REFERENCES `locations` (`location_id`, `campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_found_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=79 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp850 */ ;
/*!50003 SET character_set_results = cp850 */ ;
/*!50003 SET collation_connection  = cp850_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `trg_found_status_event` AFTER UPDATE ON `found_items` FOR EACH ROW BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO item_events (
            item_type,
            item_id,
            campus_id,
            event_type,
            title,
            description,
            actor_id,
            is_public,
            created_at
        ) VALUES (
            'FOUND',
            NEW.found_id,
            NEW.campus_id,
            CONCAT('STATUS_', NEW.status),
            CONCAT('Found item status changed to ', NEW.status),
            CONCAT('Status updated from ', OLD.status, ' to ', NEW.status),
            NEW.user_id,
            CASE WHEN NEW.status IN ('ACTIVE','MATCHED','HANDED_OVER','CLOSED') THEN 1 ELSE 0 END,
            NOW(3)
        );
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `item_events`
--

DROP TABLE IF EXISTS `item_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_events` (
  `event_id` bigint NOT NULL AUTO_INCREMENT,
  `item_type` enum('LOST','FOUND','CLAIM') COLLATE utf8mb4_unicode_ci NOT NULL,
  `item_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `event_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `actor_id` int DEFAULT NULL,
  `is_public` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`event_id`),
  KEY `fk_event_campus` (`campus_id`),
  KEY `fk_event_actor` (`actor_id`),
  KEY `idx_timeline` (`item_type`,`item_id`,`created_at`),
  CONSTRAINT `fk_event_actor` FOREIGN KEY (`actor_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_event_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=601 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `locations`
--

DROP TABLE IF EXISTS `locations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `locations` (
  `location_id` int NOT NULL AUTO_INCREMENT,
  `campus_id` tinyint NOT NULL,
  `location_name` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `room_or_spot` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `building` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `floor` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sort_order` smallint NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`location_id`),
  UNIQUE KEY `uq_loc_campus` (`location_id`,`campus_id`),
  UNIQUE KEY `uq_campus_loc_name` (`campus_id`,`location_name`),
  CONSTRAINT `fk_loc_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=245 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `login_attempts`
--

DROP TABLE IF EXISTS `login_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_attempts` (
  `attempt_id` bigint NOT NULL AUTO_INCREMENT,
  `identifier` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL,
  `success` tinyint(1) NOT NULL,
  `attempted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attempt_id`),
  KEY `idx_login_attempts` (`identifier`,`attempted_at`)
) ENGINE=InnoDB AUTO_INCREMENT=117 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `lost_items`
--

DROP TABLE IF EXISTS `lost_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `lost_items` (
  `lost_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `category_id` smallint NOT NULL,
  `location_id` int NOT NULL,
  `room_no` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `specific_spot` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `item_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `brand` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `color` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `date_lost` date NOT NULL,
  `time_lost` time DEFAULT NULL,
  `image_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('ACTIVE','MATCHED','CLAIMED','RETURNED','CLOSED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`lost_id`),
  KEY `fk_lost_user` (`user_id`),
  KEY `fk_lost_category` (`category_id`),
  KEY `fk_lost_location_campus` (`location_id`,`campus_id`),
  KEY `idx_lost_query` (`campus_id`,`status`,`category_id`,`date_lost`),
  FULLTEXT KEY `ft_lost_search` (`item_name`,`description`,`brand`),
  CONSTRAINT `fk_lost_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lost_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lost_location_campus` FOREIGN KEY (`location_id`, `campus_id`) REFERENCES `locations` (`location_id`, `campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_lost_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=57 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp850 */ ;
/*!50003 SET character_set_results = cp850 */ ;
/*!50003 SET collation_connection  = cp850_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `trg_lost_status_event` AFTER UPDATE ON `lost_items` FOR EACH ROW BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO item_events (
            item_type,
            item_id,
            campus_id,
            event_type,
            title,
            description,
            actor_id,
            is_public,
            created_at
        ) VALUES (
            'LOST',
            NEW.lost_id,
            NEW.campus_id,
            CONCAT('STATUS_', NEW.status),
            CONCAT('Item status changed to ', NEW.status),
            CONCAT('Status updated from ', OLD.status, ' to ', NEW.status),
            NEW.user_id,
            CASE WHEN NEW.status IN ('ACTIVE','MATCHED','RETURNED','CLOSED') THEN 1 ELSE 0 END,
            NOW(3)
        );
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Table structure for table `match_suggestions`
--

DROP TABLE IF EXISTS `match_suggestions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `match_suggestions` (
  `match_id` int NOT NULL AUTO_INCREMENT,
  `lost_id` int NOT NULL,
  `found_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `score` tinyint NOT NULL,
  `breakdown` json NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`match_id`),
  UNIQUE KEY `uq_match_pair` (`lost_id`,`found_id`),
  KEY `fk_match_found` (`found_id`),
  KEY `fk_match_campus` (`campus_id`),
  CONSTRAINT `fk_match_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_match_found` FOREIGN KEY (`found_id`) REFERENCES `found_items` (`found_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_match_lost` FOREIGN KEY (`lost_id`) REFERENCES `lost_items` (`lost_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=177 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `message_outbox`
--

DROP TABLE IF EXISTS `message_outbox`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `message_outbox` (
  `message_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `campus_id` tinyint NOT NULL,
  `channel` enum('SMS','WHATSAPP','EMAIL') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SMS',
  `template_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `body` varchar(480) COLLATE utf8mb4_unicode_ci NOT NULL,
  `to_phone_masked` varchar(35) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_id` int DEFAULT NULL,
  `status` enum('SIMULATED','READ') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SIMULATED',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  KEY `idx_outbox_user_created` (`user_id`,`created_at`),
  KEY `idx_outbox_campus_created` (`campus_id`,`created_at`),
  CONSTRAINT `fk_outbox_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_outbox_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=191 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications` (
  `notification_id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `message` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `notification_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_type` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_id` int DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  KEY `idx_notif_user_read` (`user_id`,`is_read`,`created_at`),
  CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=246 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `prn_registry`
--

DROP TABLE IF EXISTS `prn_registry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `prn_registry` (
  `prn` char(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `campus_id` tinyint NOT NULL,
  `imported_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `imported_by` int DEFAULT NULL,
  PRIMARY KEY (`prn`),
  KEY `fk_prn_campus` (`campus_id`),
  KEY `fk_prn_imported_by` (`imported_by`),
  CONSTRAINT `fk_prn_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_prn_imported_by` FOREIGN KEY (`imported_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `role_id` tinyint NOT NULL,
  `role_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `prn` char(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `staff_username` varchar(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(15) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `password_hash` varchar(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `must_change_password` tinyint(1) NOT NULL DEFAULT '1',
  `role_id` tinyint NOT NULL,
  `campus_id` tinyint DEFAULT NULL,
  `status` enum('ACTIVE','SUSPENDED','DEACTIVATED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'ACTIVE',
  `last_password_change` datetime DEFAULT NULL,
  `profile_completed` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `prn` (`prn`),
  UNIQUE KEY `staff_username` (`staff_username`),
  UNIQUE KEY `email` (`email`),
  KEY `fk_user_role` (`role_id`),
  KEY `fk_user_campus` (`campus_id`),
  CONSTRAINT `fk_user_campus` FOREIGN KEY (`campus_id`) REFERENCES `campuses` (`campus_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_user_prn` FOREIGN KEY (`prn`) REFERENCES `prn_registry` (`prn`) ON DELETE RESTRICT,
  CONSTRAINT `fk_user_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_staff_campus` CHECK ((((`role_id` = 4) and (`campus_id` is null)) or ((`role_id` <> 4) and (`campus_id` is not null)))),
  CONSTRAINT `chk_user_identity` CHECK (((`prn` is not null) <> (`staff_username` is not null)))
) ENGINE=InnoDB AUTO_INCREMENT=5213 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp850 */ ;
/*!50003 SET character_set_results = cp850 */ ;
/*!50003 SET collation_connection  = cp850_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `trg_users_pwd_change` AFTER UPDATE ON `users` FOR EACH ROW BEGIN
    IF (OLD.password_hash IS NULL AND NEW.password_hash IS NOT NULL)
       OR (OLD.password_hash <> NEW.password_hash) THEN
        INSERT INTO audit_logs (
            user_id,
            action,
            entity_type,
            entity_id,
            details,
            ip_address,
            created_at
        ) VALUES (
            NEW.user_id,
            'PASSWORD_CHANGED',
            'USER',
            CAST(NEW.user_id AS CHAR),
            JSON_OBJECT(
                'user_id', NEW.user_id,
                'prn', NEW.prn,
                'staff_username', NEW.staff_username,
                'was_initial_setup', (OLD.password_hash IS NULL)
            ),
            '127.0.0.1',
            NOW()
        );
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Temporary view structure for view `v_active_found`
--

DROP TABLE IF EXISTS `v_active_found`;
/*!50001 DROP VIEW IF EXISTS `v_active_found`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_active_found` AS SELECT 
 1 AS `found_id`,
 1 AS `item_name`,
 1 AS `category_id`,
 1 AS `category_name`,
 1 AS `category_icon`,
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `campus_code`,
 1 AS `location_id`,
 1 AS `location_name`,
 1 AS `building`,
 1 AS `floor`,
 1 AS `brand`,
 1 AS `color`,
 1 AS `description`,
 1 AS `date_found`,
 1 AS `time_found`,
 1 AS `image_url`,
 1 AS `custody`,
 1 AS `status`,
 1 AS `created_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_active_lost`
--

DROP TABLE IF EXISTS `v_active_lost`;
/*!50001 DROP VIEW IF EXISTS `v_active_lost`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_active_lost` AS SELECT 
 1 AS `lost_id`,
 1 AS `item_name`,
 1 AS `category_id`,
 1 AS `category_name`,
 1 AS `category_icon`,
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `campus_code`,
 1 AS `location_id`,
 1 AS `location_name`,
 1 AS `building`,
 1 AS `floor`,
 1 AS `brand`,
 1 AS `color`,
 1 AS `description`,
 1 AS `date_lost`,
 1 AS `time_lost`,
 1 AS `image_url`,
 1 AS `status`,
 1 AS `created_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_campus_comparison`
--

DROP TABLE IF EXISTS `v_campus_comparison`;
/*!50001 DROP VIEW IF EXISTS `v_campus_comparison`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_campus_comparison` AS SELECT 
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `code`,
 1 AS `total_enrolled_students`,
 1 AS `active_accounts`,
 1 AS `total_lost_reports`,
 1 AS `total_found_reports`,
 1 AS `total_claims_filed`,
 1 AS `total_successful_handovers`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_dashboard_stats`
--

DROP TABLE IF EXISTS `v_dashboard_stats`;
/*!50001 DROP VIEW IF EXISTS `v_dashboard_stats`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_dashboard_stats` AS SELECT 
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `campus_code`,
 1 AS `active_lost_count`,
 1 AS `active_found_count`,
 1 AS `pending_claims_count`,
 1 AS `returned_items_count`,
 1 AS `registered_students_count`,
 1 AS `recovery_rate_pct`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_monthly_trend`
--

DROP TABLE IF EXISTS `v_monthly_trend`;
/*!50001 DROP VIEW IF EXISTS `v_monthly_trend`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_monthly_trend` AS SELECT 
 1 AS `month`,
 1 AS `campus_id`,
 1 AS `lost_reported`,
 1 AS `found_reported`,
 1 AS `resolved_count`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_pending_claims`
--

DROP TABLE IF EXISTS `v_pending_claims`;
/*!50001 DROP VIEW IF EXISTS `v_pending_claims`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_pending_claims` AS SELECT 
 1 AS `claim_id`,
 1 AS `found_id`,
 1 AS `found_item_name`,
 1 AS `found_image_url`,
 1 AS `lost_id`,
 1 AS `claimant_id`,
 1 AS `claimant_prn`,
 1 AS `claimant_name`,
 1 AS `claimant_phone`,
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `claim_description`,
 1 AS `claim_status`,
 1 AS `submitted_at`,
 1 AS `reviewed_at`,
 1 AS `reviewed_by`,
 1 AS `total_questions`,
 1 AS `answered_questions`,
 1 AS `verified_questions`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_top_categories`
--

DROP TABLE IF EXISTS `v_top_categories`;
/*!50001 DROP VIEW IF EXISTS `v_top_categories`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_top_categories` AS SELECT 
 1 AS `category_id`,
 1 AS `category_name`,
 1 AS `icon`,
 1 AS `lost_count`,
 1 AS `found_count`,
 1 AS `total_items`*/;
SET character_set_client = @saved_cs_client;

--
-- Temporary view structure for view `v_top_locations`
--

DROP TABLE IF EXISTS `v_top_locations`;
/*!50001 DROP VIEW IF EXISTS `v_top_locations`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `v_top_locations` AS SELECT 
 1 AS `campus_id`,
 1 AS `campus_name`,
 1 AS `location_id`,
 1 AS `location_name`,
 1 AS `building`,
 1 AS `lost_count`,
 1 AS `found_count`,
 1 AS `total_incidents`*/;
SET character_set_client = @saved_cs_client;

--
-- Dumping routines for database 'campuskhoj_zero'
--
/*!50003 DROP PROCEDURE IF EXISTS `sp_approve_claim` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = cp850 */ ;
/*!50003 SET character_set_results = cp850 */ ;
/*!50003 SET collation_connection  = cp850_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_approve_claim`(
    IN p_claim_id INT,
    IN p_staff_id INT,
    OUT p_success BOOLEAN,
    OUT p_message VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_found_id INT;
    DECLARE v_lost_id INT;
    DECLARE v_claimant_id INT;
    DECLARE v_campus_id TINYINT;
    DECLARE v_current_status VARCHAR(20);
    DECLARE v_claimant_phone VARCHAR(15);
    DECLARE v_masked_phone VARCHAR(15);

    
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_message = 'Database error occurred during claim approval transaction';
    END;

    
    SELECT found_id, lost_id, claimant_id, campus_id, claim_status
      INTO v_found_id, v_lost_id, v_claimant_id, v_campus_id, v_current_status
      FROM claims
     WHERE claim_id = p_claim_id;

    IF v_found_id IS NULL THEN
        SET p_success = FALSE;
        SET p_message = 'Claim not found';
        LEAVE proc_label;
    END IF;

    IF v_current_status NOT IN ('PENDING', 'UNDER_REVIEW') THEN
        SET p_success = FALSE;
        SET p_message = CONCAT('Cannot approve claim with status ', v_current_status);
        LEAVE proc_label;
    END IF;

    START TRANSACTION;

    
    UPDATE claims
       SET claim_status = 'APPROVED',
           reviewed_by = p_staff_id,
           reviewed_at = NOW()
     WHERE claim_id = p_claim_id;

    
    UPDATE found_items
       SET status = 'CLAIMED'
     WHERE found_id = v_found_id;

    
    IF v_lost_id IS NOT NULL THEN
        UPDATE lost_items
           SET status = 'CLAIMED'
         WHERE lost_id = v_lost_id;
    END IF;

    
    UPDATE claims
       SET claim_status = 'REJECTED',
           reject_reason = 'Another claim on this item was approved',
           reviewed_by = p_staff_id,
           reviewed_at = NOW()
     WHERE found_id = v_found_id
       AND claim_id <> p_claim_id
       AND claim_status IN ('PENDING', 'UNDER_REVIEW');

    
    INSERT INTO item_events (
        item_type, item_id, campus_id, event_type, title, description, actor_id, is_public, created_at
    ) VALUES (
        'CLAIM', p_claim_id, v_campus_id, 'CLAIM_APPROVED', 'Claim Approved by Staff',
        'Verification confirmed. Ready for physical handover at campus security desk.',
        p_staff_id, 0, NOW(3)
    );

    INSERT INTO item_events (
        item_type, item_id, campus_id, event_type, title, description, actor_id, is_public, created_at
    ) VALUES (
        'FOUND', v_found_id, v_campus_id, 'CLAIM_APPROVED', 'Item Claim Approved',
        'Ownership verified. Item awaiting collection at campus security desk.',
        p_staff_id, 1, NOW(3)
    );

    
    INSERT INTO notifications (
        user_id, message, notification_type, ref_type, ref_id, is_read, created_at
    ) VALUES (
        v_claimant_id,
        'Good news! Your claim has been approved. Please visit your campus security desk with your college ID card for handover.',
        'CLAIM_APPROVED', 'CLAIM', p_claim_id, 0, NOW()
    );

    
    SELECT phone INTO v_claimant_phone FROM users WHERE user_id = v_claimant_id;
    IF v_claimant_phone IS NOT NULL AND CHAR_LENGTH(v_claimant_phone) >= 4 THEN
        SET v_masked_phone = CONCAT(LEFT(v_claimant_phone, 2), '****', RIGHT(v_claimant_phone, 4));
    ELSE
        SET v_masked_phone = 'No phone saved (preview only)';
    END IF;

    INSERT INTO message_outbox (
        user_id, campus_id, channel, template_code, body, to_phone_masked, ref_type, ref_id, status, created_at
    ) VALUES (
        v_claimant_id,
        v_campus_id,
        'SMS',
        'CLAIM_APPROVED',
        CONCAT('CampusKhoj: Good news! Your claim #', p_claim_id, ' was APPROVED by Campus Security. Bring your student ID to the Security Desk for handover. Do not share your PRN.'),
        v_masked_phone,
        'CLAIM',
        p_claim_id,
        'SIMULATED',
        NOW()
    );

    
    INSERT INTO audit_logs (
        user_id, action, entity_type, entity_id, details, ip_address, created_at
    ) VALUES (
        p_staff_id,
        'CLAIM_APPROVED',
        'CLAIM',
        CAST(p_claim_id AS CHAR),
        JSON_OBJECT(
            'claim_id', p_claim_id,
            'found_id', v_found_id,
            'lost_id', v_lost_id,
            'claimant_id', v_claimant_id,
            'campus_id', v_campus_id
        ),
        '127.0.0.1',
        NOW()
    );

    COMMIT;

    SET p_success = TRUE;
    SET p_message = 'Claim approved successfully';
END proc_label ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;

--
-- Final view structure for view `v_active_found`
--

/*!50001 DROP VIEW IF EXISTS `v_active_found`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_active_found` AS select `f`.`found_id` AS `found_id`,`f`.`item_name` AS `item_name`,`f`.`category_id` AS `category_id`,`c`.`category_name` AS `category_name`,`c`.`icon` AS `category_icon`,`f`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`cp`.`code` AS `campus_code`,`f`.`location_id` AS `location_id`,`loc`.`location_name` AS `location_name`,`loc`.`building` AS `building`,`loc`.`floor` AS `floor`,`f`.`brand` AS `brand`,`f`.`color` AS `color`,`f`.`description` AS `description`,`f`.`date_found` AS `date_found`,`f`.`time_found` AS `time_found`,`f`.`image_url` AS `image_url`,`f`.`custody` AS `custody`,`f`.`status` AS `status`,`f`.`created_at` AS `created_at` from (((`found_items` `f` join `categories` `c` on((`f`.`category_id` = `c`.`category_id`))) join `campuses` `cp` on((`f`.`campus_id` = `cp`.`campus_id`))) join `locations` `loc` on(((`f`.`location_id` = `loc`.`location_id`) and (`f`.`campus_id` = `loc`.`campus_id`)))) where (`f`.`status` in ('ACTIVE','MATCHED')) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_active_lost`
--

/*!50001 DROP VIEW IF EXISTS `v_active_lost`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_active_lost` AS select `l`.`lost_id` AS `lost_id`,`l`.`item_name` AS `item_name`,`l`.`category_id` AS `category_id`,`c`.`category_name` AS `category_name`,`c`.`icon` AS `category_icon`,`l`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`cp`.`code` AS `campus_code`,`l`.`location_id` AS `location_id`,`loc`.`location_name` AS `location_name`,`loc`.`building` AS `building`,`loc`.`floor` AS `floor`,`l`.`brand` AS `brand`,`l`.`color` AS `color`,`l`.`description` AS `description`,`l`.`date_lost` AS `date_lost`,`l`.`time_lost` AS `time_lost`,`l`.`image_url` AS `image_url`,`l`.`status` AS `status`,`l`.`created_at` AS `created_at` from (((`lost_items` `l` join `categories` `c` on((`l`.`category_id` = `c`.`category_id`))) join `campuses` `cp` on((`l`.`campus_id` = `cp`.`campus_id`))) join `locations` `loc` on(((`l`.`location_id` = `loc`.`location_id`) and (`l`.`campus_id` = `loc`.`campus_id`)))) where (`l`.`status` in ('ACTIVE','MATCHED')) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_campus_comparison`
--

/*!50001 DROP VIEW IF EXISTS `v_campus_comparison`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_campus_comparison` AS select `cp`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`cp`.`code` AS `code`,count(distinct `pr`.`prn`) AS `total_enrolled_students`,count(distinct `u`.`user_id`) AS `active_accounts`,count(distinct `l`.`lost_id`) AS `total_lost_reports`,count(distinct `f`.`found_id`) AS `total_found_reports`,count(distinct `cl`.`claim_id`) AS `total_claims_filed`,count(distinct (case when (`f`.`status` = 'HANDED_OVER') then `f`.`found_id` end)) AS `total_successful_handovers` from (((((`campuses` `cp` left join `prn_registry` `pr` on((`cp`.`campus_id` = `pr`.`campus_id`))) left join `users` `u` on((`cp`.`campus_id` = `u`.`campus_id`))) left join `lost_items` `l` on((`cp`.`campus_id` = `l`.`campus_id`))) left join `found_items` `f` on((`cp`.`campus_id` = `f`.`campus_id`))) left join `claims` `cl` on((`cp`.`campus_id` = `cl`.`campus_id`))) group by `cp`.`campus_id`,`cp`.`campus_name`,`cp`.`code` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_dashboard_stats`
--

/*!50001 DROP VIEW IF EXISTS `v_dashboard_stats`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_dashboard_stats` AS select `cp`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`cp`.`code` AS `campus_code`,(select count(0) from `lost_items` `l` where ((`l`.`campus_id` = `cp`.`campus_id`) and (`l`.`status` in ('ACTIVE','MATCHED')))) AS `active_lost_count`,(select count(0) from `found_items` `f` where ((`f`.`campus_id` = `cp`.`campus_id`) and (`f`.`status` in ('ACTIVE','MATCHED')))) AS `active_found_count`,(select count(0) from `claims` `cl` where ((`cl`.`campus_id` = `cp`.`campus_id`) and (`cl`.`claim_status` in ('PENDING','UNDER_REVIEW')))) AS `pending_claims_count`,(select count(0) from `found_items` `f` where ((`f`.`campus_id` = `cp`.`campus_id`) and (`f`.`status` = 'HANDED_OVER'))) AS `returned_items_count`,(select count(0) from `users` `u` where ((`u`.`campus_id` = `cp`.`campus_id`) and (`u`.`status` = 'ACTIVE'))) AS `registered_students_count`,round((case when ((select count(0) from `lost_items` `l` where (`l`.`campus_id` = `cp`.`campus_id`)) = 0) then 0 else (((select count(0) from `lost_items` `l` where ((`l`.`campus_id` = `cp`.`campus_id`) and (`l`.`status` = 'RETURNED'))) * 100.0) / (select count(0) from `lost_items` `l` where (`l`.`campus_id` = `cp`.`campus_id`))) end),1) AS `recovery_rate_pct` from `campuses` `cp` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_monthly_trend`
--

/*!50001 DROP VIEW IF EXISTS `v_monthly_trend`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_monthly_trend` AS select date_format(`combined_reports`.`report_date`,'%Y-%m') AS `month`,`combined_reports`.`campus_id` AS `campus_id`,sum((case when (`combined_reports`.`item_type` = 'LOST') then 1 else 0 end)) AS `lost_reported`,sum((case when (`combined_reports`.`item_type` = 'FOUND') then 1 else 0 end)) AS `found_reported`,sum((case when (`combined_reports`.`status` in ('RETURNED','HANDED_OVER')) then 1 else 0 end)) AS `resolved_count` from (select 'LOST' AS `item_type`,`lost_items`.`date_lost` AS `report_date`,`lost_items`.`campus_id` AS `campus_id`,`lost_items`.`status` AS `status` from `lost_items` union all select 'FOUND' AS `item_type`,`found_items`.`date_found` AS `report_date`,`found_items`.`campus_id` AS `campus_id`,`found_items`.`status` AS `status` from `found_items`) `combined_reports` group by date_format(`combined_reports`.`report_date`,'%Y-%m'),`combined_reports`.`campus_id` order by `month` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_pending_claims`
--

/*!50001 DROP VIEW IF EXISTS `v_pending_claims`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_pending_claims` AS select `cl`.`claim_id` AS `claim_id`,`cl`.`found_id` AS `found_id`,`fi`.`item_name` AS `found_item_name`,`fi`.`image_url` AS `found_image_url`,`cl`.`lost_id` AS `lost_id`,`cl`.`claimant_id` AS `claimant_id`,`u`.`prn` AS `claimant_prn`,`u`.`name` AS `claimant_name`,`u`.`phone` AS `claimant_phone`,`cl`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`cl`.`claim_description` AS `claim_description`,`cl`.`claim_status` AS `claim_status`,`cl`.`submitted_at` AS `submitted_at`,`cl`.`reviewed_at` AS `reviewed_at`,`cl`.`reviewed_by` AS `reviewed_by`,(select count(0) from `claim_verifications` `cv` where (`cv`.`claim_id` = `cl`.`claim_id`)) AS `total_questions`,(select count(0) from `claim_verifications` `cv` where ((`cv`.`claim_id` = `cl`.`claim_id`) and (`cv`.`verification_status` = 'ANSWERED'))) AS `answered_questions`,(select count(0) from `claim_verifications` `cv` where ((`cv`.`claim_id` = `cl`.`claim_id`) and (`cv`.`verification_status` = 'VERIFIED'))) AS `verified_questions` from (((`claims` `cl` join `found_items` `fi` on((`cl`.`found_id` = `fi`.`found_id`))) join `users` `u` on((`cl`.`claimant_id` = `u`.`user_id`))) join `campuses` `cp` on((`cl`.`campus_id` = `cp`.`campus_id`))) where (`cl`.`claim_status` in ('PENDING','UNDER_REVIEW','APPROVED')) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_top_categories`
--

/*!50001 DROP VIEW IF EXISTS `v_top_categories`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_top_categories` AS select `c`.`category_id` AS `category_id`,`c`.`category_name` AS `category_name`,`c`.`icon` AS `icon`,count(distinct `l`.`lost_id`) AS `lost_count`,count(distinct `f`.`found_id`) AS `found_count`,(count(distinct `l`.`lost_id`) + count(distinct `f`.`found_id`)) AS `total_items` from ((`categories` `c` left join `lost_items` `l` on((`c`.`category_id` = `l`.`category_id`))) left join `found_items` `f` on((`c`.`category_id` = `f`.`category_id`))) group by `c`.`category_id`,`c`.`category_name`,`c`.`icon` order by `total_items` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;

--
-- Final view structure for view `v_top_locations`
--

/*!50001 DROP VIEW IF EXISTS `v_top_locations`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = cp850 */;
/*!50001 SET character_set_results     = cp850 */;
/*!50001 SET collation_connection      = cp850_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_top_locations` AS select `loc`.`campus_id` AS `campus_id`,`cp`.`campus_name` AS `campus_name`,`loc`.`location_id` AS `location_id`,`loc`.`location_name` AS `location_name`,`loc`.`building` AS `building`,count(distinct `l`.`lost_id`) AS `lost_count`,count(distinct `f`.`found_id`) AS `found_count`,(count(distinct `l`.`lost_id`) + count(distinct `f`.`found_id`)) AS `total_incidents` from (((`locations` `loc` join `campuses` `cp` on((`loc`.`campus_id` = `cp`.`campus_id`))) left join `lost_items` `l` on(((`loc`.`location_id` = `l`.`location_id`) and (`loc`.`campus_id` = `l`.`campus_id`)))) left join `found_items` `f` on(((`loc`.`location_id` = `f`.`location_id`) and (`loc`.`campus_id` = `f`.`campus_id`)))) group by `loc`.`campus_id`,`cp`.`campus_name`,`loc`.`location_id`,`loc`.`location_name`,`loc`.`building` order by `total_incidents` desc */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-03 15:14:47
