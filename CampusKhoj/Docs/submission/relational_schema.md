# CampusKhoj Relational Database Schema Specification

**Database**: `campuskhoj_zero`  
**RDBMS**: MySQL Community Server 8.0.46  
**Engine**: InnoDB (ACID compliant)  
**Default Charset**: `utf8mb4`  
**Default Collation**: `utf8mb4_unicode_ci`  
**Extracted From Live Instance**: Verified  

---

## Table of Contents

- [audit_logs](#audit_logs)
- [campuses](#campuses)
- [categories](#categories)
- [claim_messages](#claim_messages)
- [claim_verifications](#claim_verifications)
- [claims](#claims)
- [found_items](#found_items)
- [item_events](#item_events)
- [locations](#locations)
- [login_attempts](#login_attempts)
- [lost_items](#lost_items)
- [match_suggestions](#match_suggestions)
- [message_outbox](#message_outbox)
- [notifications](#notifications)
- [prn_registry](#prn_registry)
- [roles](#roles)
- [users](#users)

---

### `audit_logs`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `log_id` | `bigint` | NO | PRI | `-` | auto_increment |
| `user_id` | `int` | YES | MUL | `-` | - |
| `action` | `varchar(40)` | NO | - | `-` | - |
| `entity_type` | `varchar(20)` | NO | MUL | `-` | - |
| `entity_id` | `varchar(20)` | NO | - | `-` | - |
| `details` | `json` | YES | - | `-` | - |
| `ip_address` | `varchar(45)` | YES | - | `-` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=120 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `campuses`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `campus_id` | `tinyint` | NO | PRI | `-` | - |
| `campus_name` | `varchar(40)` | NO | UNI | `-` | - |
| `code` | `varchar(10)` | NO | UNI | `-` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
CREATE TABLE `campuses` (
  `campus_id` tinyint NOT NULL,
  `campus_name` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`campus_id`),
  UNIQUE KEY `campus_name` (`campus_name`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `categories`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `category_id` | `smallint` | NO | PRI | `-` | auto_increment |
| `category_name` | `varchar(50)` | NO | UNI | `-` | - |
| `description` | `varchar(200)` | YES | - | `-` | - |
| `icon` | `varchar(30)` | YES | - | `package` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
CREATE TABLE `categories` (
  `category_id` smallint NOT NULL AUTO_INCREMENT,
  `category_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `icon` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT 'package',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `claim_messages`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `message_id` | `bigint` | NO | PRI | `-` | auto_increment |
| `claim_id` | `int` | NO | MUL | `-` | - |
| `sender_id` | `int` | NO | MUL | `-` | - |
| `sender_role` | `enum('STUDENT','STAFF')` | NO | - | `-` | - |
| `message_text` | `text` | NO | - | `-` | - |
| `sent_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `read_at` | `datetime` | YES | - | `-` | - |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `claim_verifications`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `verification_id` | `int` | NO | PRI | `-` | auto_increment |
| `claim_id` | `int` | NO | MUL | `-` | - |
| `question` | `varchar(255)` | NO | - | `-` | - |
| `expected_evidence` | `varchar(255)` | YES | - | `-` | - |
| `answer` | `text` | YES | - | `-` | - |
| `verification_status` | `enum('ASKED','ANSWERED','VERIFIED','FAILED')` | NO | - | `ASKED` | - |
| `asked_by` | `int` | NO | MUL | `-` | - |
| `verified_by` | `int` | YES | MUL | `-` | - |
| `verified_at` | `datetime` | YES | - | `-` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `claims`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `claim_id` | `int` | NO | PRI | `-` | auto_increment |
| `found_id` | `int` | NO | MUL | `-` | - |
| `lost_id` | `int` | YES | MUL | `-` | - |
| `claimant_id` | `int` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `claim_description` | `text` | NO | - | `-` | - |
| `proof_url` | `varchar(255)` | YES | - | `-` | - |
| `proof_type` | `varchar(50)` | YES | - | `-` | - |
| `claim_status` | `enum('PENDING','UNDER_REVIEW','APPROVED','REJECTED','COMPLETED','CANCELLED')` | NO | - | `PENDING` | - |
| `reject_reason` | `varchar(255)` | YES | - | `-` | - |
| `submitted_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `reviewed_at` | `datetime` | YES | - | `-` | - |
| `reviewed_by` | `int` | YES | MUL | `-` | - |
| `handed_over_at` | `datetime` | YES | - | `-` | - |
| `handed_over_by` | `int` | YES | MUL | `-` | - |
| `active_key` | `tinyint` | YES | - | `-` | STORED GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=59 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `found_items`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `found_id` | `int` | NO | PRI | `-` | auto_increment |
| `user_id` | `int` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `category_id` | `smallint` | NO | MUL | `-` | - |
| `location_id` | `int` | NO | MUL | `-` | - |
| `room_no` | `varchar(50)` | YES | - | `-` | - |
| `specific_spot` | `varchar(120)` | YES | - | `-` | - |
| `item_name` | `varchar(100)` | NO | MUL | `-` | - |
| `brand` | `varchar(60)` | YES | - | `-` | - |
| `color` | `varchar(30)` | YES | - | `-` | - |
| `description` | `text` | NO | - | `-` | - |
| `private_details` | `text` | YES | - | `-` | - |
| `date_found` | `date` | NO | MUL | `-` | - |
| `time_found` | `time` | YES | - | `-` | - |
| `image_url` | `varchar(255)` | YES | - | `-` | - |
| `custody` | `enum('WITH_FINDER','AT_DESK')` | NO | - | `WITH_FINDER` | - |
| `storage_location` | `varchar(100)` | YES | - | `-` | - |
| `status` | `enum('ACTIVE','MATCHED','CLAIMED','HANDED_OVER','CLOSED')` | NO | - | `ACTIVE` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `updated_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `item_events`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `event_id` | `bigint` | NO | PRI | `-` | auto_increment |
| `item_type` | `enum('LOST','FOUND','CLAIM')` | NO | MUL | `-` | - |
| `item_id` | `int` | NO | - | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `event_type` | `varchar(30)` | NO | - | `-` | - |
| `title` | `varchar(100)` | NO | - | `-` | - |
| `description` | `varchar(255)` | YES | - | `-` | - |
| `actor_id` | `int` | YES | MUL | `-` | - |
| `is_public` | `tinyint(1)` | NO | - | `0` | - |
| `created_at` | `datetime(3)` | NO | - | `CURRENT_TIMESTAMP(3)` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=213 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `locations`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `location_id` | `int` | NO | PRI | `-` | auto_increment |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `location_name` | `varchar(80)` | NO | - | `-` | - |
| `room_or_spot` | `varchar(100)` | YES | - | `-` | - |
| `building` | `varchar(60)` | YES | - | `-` | - |
| `floor` | `varchar(20)` | YES | - | `-` | - |
| `description` | `varchar(200)` | YES | - | `-` | - |
| `sort_order` | `smallint` | NO | - | `0` | - |
| `is_active` | `tinyint(1)` | NO | - | `1` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=245 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `login_attempts`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `attempt_id` | `bigint` | NO | PRI | `-` | auto_increment |
| `identifier` | `varchar(40)` | NO | MUL | `-` | - |
| `ip_address` | `varchar(45)` | NO | - | `-` | - |
| `success` | `tinyint(1)` | NO | - | `-` | - |
| `attempted_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
CREATE TABLE `login_attempts` (
  `attempt_id` bigint NOT NULL AUTO_INCREMENT,
  `identifier` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL,
  `success` tinyint(1) NOT NULL,
  `attempted_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attempt_id`),
  KEY `idx_login_attempts` (`identifier`,`attempted_at`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `lost_items`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `lost_id` | `int` | NO | PRI | `-` | auto_increment |
| `user_id` | `int` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `category_id` | `smallint` | NO | MUL | `-` | - |
| `location_id` | `int` | NO | MUL | `-` | - |
| `room_no` | `varchar(50)` | YES | - | `-` | - |
| `specific_spot` | `varchar(120)` | YES | - | `-` | - |
| `item_name` | `varchar(100)` | NO | MUL | `-` | - |
| `description` | `text` | NO | - | `-` | - |
| `brand` | `varchar(60)` | YES | - | `-` | - |
| `color` | `varchar(30)` | YES | - | `-` | - |
| `date_lost` | `date` | NO | - | `-` | - |
| `time_lost` | `time` | YES | - | `-` | - |
| `image_url` | `varchar(255)` | YES | - | `-` | - |
| `status` | `enum('ACTIVE','MATCHED','CLAIMED','RETURNED','CLOSED')` | NO | - | `ACTIVE` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `updated_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `match_suggestions`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `match_id` | `int` | NO | PRI | `-` | auto_increment |
| `lost_id` | `int` | NO | MUL | `-` | - |
| `found_id` | `int` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `score` | `tinyint` | NO | - | `-` | - |
| `breakdown` | `json` | NO | - | `-` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `message_outbox`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `message_id` | `int` | NO | PRI | `-` | auto_increment |
| `user_id` | `int` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `channel` | `enum('SMS','WHATSAPP','EMAIL')` | NO | - | `SMS` | - |
| `template_code` | `varchar(50)` | NO | - | `-` | - |
| `body` | `varchar(480)` | NO | - | `-` | - |
| `to_phone_masked` | `varchar(35)` | YES | - | `-` | - |
| `ref_type` | `varchar(20)` | YES | - | `-` | - |
| `ref_id` | `int` | YES | - | `-` | - |
| `status` | `enum('SIMULATED','READ')` | NO | - | `SIMULATED` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `notifications`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `notification_id` | `bigint` | NO | PRI | `-` | auto_increment |
| `user_id` | `int` | NO | MUL | `-` | - |
| `message` | `varchar(255)` | NO | - | `-` | - |
| `notification_type` | `varchar(30)` | NO | - | `-` | - |
| `ref_type` | `varchar(10)` | YES | - | `-` | - |
| `ref_id` | `int` | YES | - | `-` | - |
| `is_read` | `tinyint(1)` | NO | - | `0` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `prn_registry`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `prn` | `char(10)` | NO | PRI | `-` | - |
| `campus_id` | `tinyint` | NO | MUL | `-` | - |
| `imported_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `imported_by` | `int` | YES | MUL | `-` | - |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `roles`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `role_id` | `tinyint` | NO | PRI | `-` | - |
| `role_name` | `varchar(20)` | NO | UNI | `-` | - |

#### Raw DDL Definition

```sql
CREATE TABLE `roles` (
  `role_id` tinyint NOT NULL,
  `role_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

### `users`

| Column | Type | Nullable | Key | Default | Extra |
|---|---|---|---|---|---|
| `user_id` | `int` | NO | PRI | `-` | auto_increment |
| `prn` | `char(10)` | YES | UNI | `-` | - |
| `staff_username` | `varchar(40)` | YES | UNI | `-` | - |
| `name` | `varchar(100)` | YES | - | `-` | - |
| `email` | `varchar(120)` | YES | UNI | `-` | - |
| `phone` | `varchar(15)` | YES | - | `-` | - |
| `password_hash` | `varchar(60)` | YES | - | `-` | - |
| `must_change_password` | `tinyint(1)` | NO | - | `1` | - |
| `role_id` | `tinyint` | NO | MUL | `-` | - |
| `campus_id` | `tinyint` | YES | MUL | `-` | - |
| `status` | `enum('ACTIVE','SUSPENDED','DEACTIVATED')` | NO | - | `ACTIVE` | - |
| `last_password_change` | `datetime` | YES | - | `-` | - |
| `profile_completed` | `tinyint(1)` | NO | - | `0` | - |
| `created_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED |
| `updated_at` | `datetime` | YES | - | `CURRENT_TIMESTAMP` | DEFAULT_GENERATED on update CURRENT_TIMESTAMP |

#### Raw DDL Definition

```sql
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
) ENGINE=InnoDB AUTO_INCREMENT=5184 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
```

---

