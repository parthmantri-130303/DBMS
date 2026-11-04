-- CampusKhoj Database Schema (MySQL 8.0 InnoDB)
-- Two-Campus Lost & Found Management System (Kondhwa & Bibwewadi)
-- Source of truth: Docs/05_backend_schema.md

-- ----------------------------------------------------------------------------
-- 1. Reference: Campuses
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campuses (
    campus_id TINYINT NOT NULL PRIMARY KEY,
    campus_name VARCHAR(40) NOT NULL UNIQUE,
    code VARCHAR(10) NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. Reference: Roles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id TINYINT NOT NULL PRIMARY KEY,
    role_name VARCHAR(20) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. Student PRN Registry (imported from university PRN sheets)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prn_registry (
    prn CHAR(10) NOT NULL PRIMARY KEY,
    campus_id TINYINT NOT NULL,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    imported_by INT NULL,
    CONSTRAINT fk_prn_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. Users (Students & Staff)
-- Exactly one identity: PRN for student, staff_username for staff.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    prn CHAR(10) NULL UNIQUE,
    staff_username VARCHAR(40) NULL UNIQUE,
    name VARCHAR(100) NULL,
    email VARCHAR(120) NULL UNIQUE,
    phone VARCHAR(15) NULL,
    password_hash VARCHAR(60) NULL,             -- NULL means first-login state (PRN is password)
    must_change_password BOOLEAN NOT NULL DEFAULT 1,
    role_id TINYINT NOT NULL,
    campus_id TINYINT NULL,                     -- NULL only for SUPER_ADMIN
    status ENUM('ACTIVE','SUSPENDED','DEACTIVATED') NOT NULL DEFAULT 'ACTIVE',
    last_password_change DATETIME NULL,
    profile_completed BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_prn FOREIGN KEY (prn) REFERENCES prn_registry(prn) ON DELETE RESTRICT,
    CONSTRAINT fk_user_role FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT,
    CONSTRAINT fk_user_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    CONSTRAINT chk_user_identity CHECK ((prn IS NOT NULL) <> (staff_username IS NOT NULL)),
    CONSTRAINT chk_staff_campus CHECK ((role_id = 4 AND campus_id IS NULL) OR (role_id != 4 AND campus_id IS NOT NULL))
) ENGINE=InnoDB;

-- Set prn_registry foreign key to users table
ALTER TABLE prn_registry
    ADD CONSTRAINT fk_prn_imported_by FOREIGN KEY (imported_by) REFERENCES users(user_id) ON DELETE SET NULL;

-- ----------------------------------------------------------------------------
-- 5. Login Attempts (for rate limiting, lockouts and audit)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(40) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    success BOOLEAN NOT NULL,
    attempted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_attempts (identifier, attempted_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 6. Reference: Categories
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    category_id SMALLINT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200) NULL,
    icon VARCHAR(30) NULL DEFAULT 'package',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 7. Reference: Locations (Campus specific with Composite Key)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    campus_id TINYINT NOT NULL,
    location_name VARCHAR(80) NOT NULL,
    room_or_spot VARCHAR(100) NULL,
    building VARCHAR(60) NULL,
    floor VARCHAR(20) NULL,
    description VARCHAR(200) NULL,
    sort_order SMALLINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_loc_campus UNIQUE (location_id, campus_id),
    CONSTRAINT uq_campus_loc_name UNIQUE (campus_id, location_name),
    CONSTRAINT fk_loc_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 8. Lost Items
-- Composite FK (location_id, campus_id) strictly prevents cross-campus mismatch!
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lost_items (
    lost_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    category_id SMALLINT NOT NULL,
    location_id INT NOT NULL,
    room_no VARCHAR(50) NULL,
    specific_spot VARCHAR(120) NULL,
    item_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    brand VARCHAR(60) NULL,
    color VARCHAR(30) NULL,
    date_lost DATE NOT NULL,
    time_lost TIME NULL,
    image_url VARCHAR(255) NULL,
    status ENUM('ACTIVE','MATCHED','CLAIMED','RETURNED','CLOSED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_lost_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_lost_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    CONSTRAINT fk_lost_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT,
    CONSTRAINT fk_lost_location_campus FOREIGN KEY (location_id, campus_id)
        REFERENCES locations(location_id, campus_id) ON DELETE RESTRICT,
    INDEX idx_lost_query (campus_id, status, category_id, date_lost),
    FULLTEXT INDEX ft_lost_search (item_name, description, brand)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 9. Found Items
-- Public fields + private details (staff verification only) + custody + composite FK
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS found_items (
    found_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    category_id SMALLINT NOT NULL,
    location_id INT NOT NULL,
    room_no VARCHAR(50) NULL,
    specific_spot VARCHAR(120) NULL,
    item_name VARCHAR(100) NOT NULL,
    brand VARCHAR(60) NULL,
    color VARCHAR(30) NULL,
    description TEXT NOT NULL,
    private_details TEXT NULL,
    date_found DATE NOT NULL,
    time_found TIME NULL,
    image_url VARCHAR(255) NULL,
    custody ENUM('WITH_FINDER','AT_DESK') NOT NULL DEFAULT 'WITH_FINDER',
    storage_location VARCHAR(100) NULL,
    status ENUM('ACTIVE','MATCHED','CLAIMED','HANDED_OVER','CLOSED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_found_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_found_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    CONSTRAINT fk_found_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT,
    CONSTRAINT fk_found_location_campus FOREIGN KEY (location_id, campus_id)
        REFERENCES locations(location_id, campus_id) ON DELETE RESTRICT,
    INDEX idx_found_query (campus_id, status, category_id, date_found),
    INDEX idx_found_date (date_found, created_at),
    INDEX idx_found_cat_date (category_id, date_found),
    FULLTEXT INDEX ft_found_search (item_name, description, brand)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 10. Match Suggestions
-- Stores calculated matches between lost & found reports within same campus
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_suggestions (
    match_id INT AUTO_INCREMENT PRIMARY KEY,
    lost_id INT NOT NULL,
    found_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    score TINYINT NOT NULL,
    breakdown JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_match_pair UNIQUE (lost_id, found_id),
    CONSTRAINT fk_match_lost FOREIGN KEY (lost_id) REFERENCES lost_items(lost_id) ON DELETE CASCADE,
    CONSTRAINT fk_match_found FOREIGN KEY (found_id) REFERENCES found_items(found_id) ON DELETE CASCADE,
    CONSTRAINT fk_match_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 11. Claims
-- Uses generated active_key to enforce exactly one active claim per student per item!
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    claim_id INT AUTO_INCREMENT PRIMARY KEY,
    found_id INT NOT NULL,
    lost_id INT NULL,
    claimant_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    claim_description TEXT NOT NULL,
    proof_url VARCHAR(255) NULL,
    proof_type VARCHAR(50) NULL,
    claim_status ENUM('PENDING','UNDER_REVIEW','APPROVED','REJECTED','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    reject_reason VARCHAR(255) NULL,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    reviewed_by INT NULL,
    handed_over_at DATETIME NULL,
    handed_over_by INT NULL,
    active_key TINYINT GENERATED ALWAYS AS (
        CASE WHEN claim_status IN ('PENDING','UNDER_REVIEW','APPROVED') THEN 1 ELSE NULL END
    ) STORED,
    CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key),
    CONSTRAINT fk_claim_found FOREIGN KEY (found_id) REFERENCES found_items(found_id) ON DELETE RESTRICT,
    CONSTRAINT fk_claim_lost FOREIGN KEY (lost_id) REFERENCES lost_items(lost_id) ON DELETE SET NULL,
    CONSTRAINT fk_claim_claimant FOREIGN KEY (claimant_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_claim_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    CONSTRAINT fk_claim_reviewed_by FOREIGN KEY (reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_claim_handed_over_by FOREIGN KEY (handed_over_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_claims_search (campus_id, claim_status, submitted_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 12. Claim Verifications (Private staff Q&A)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_verifications (
    verification_id INT AUTO_INCREMENT PRIMARY KEY,
    claim_id INT NOT NULL,
    question VARCHAR(255) NOT NULL,
    expected_evidence VARCHAR(255) NULL,
    answer TEXT NULL,
    verification_status ENUM('ASKED','ANSWERED','VERIFIED','FAILED') NOT NULL DEFAULT 'ASKED',
    asked_by INT NOT NULL,
    verified_by INT NULL,
    verified_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_verif_claim FOREIGN KEY (claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
    CONSTRAINT fk_verif_asked_by FOREIGN KEY (asked_by) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_verif_verified_by FOREIGN KEY (verified_by) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 12b. Claim Messages (Secure anonymous messaging claimant <-> staff)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_messages (
    message_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    claim_id INT NOT NULL,
    sender_id INT NOT NULL,
    sender_role ENUM('STUDENT','STAFF') NOT NULL,
    message_text TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    CONSTRAINT fk_msg_claim FOREIGN KEY (claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
    CONSTRAINT fk_msg_sender FOREIGN KEY (sender_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    INDEX idx_claim_messages (claim_id, sent_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 13. Item Events (The animated timeline)
-- Polymorphic by design: item_type ('LOST','FOUND','CLAIM') + item_id
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS item_events (
    event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_type ENUM('LOST','FOUND','CLAIM') NOT NULL,
    item_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    actor_id INT NULL,
    is_public BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    CONSTRAINT fk_event_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_actor FOREIGN KEY (actor_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_timeline (item_type, item_id, created_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 14. Notifications (In-app notifications for students)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message VARCHAR(255) NOT NULL,
    notification_type VARCHAR(30) NOT NULL,
    ref_type VARCHAR(10) NULL,
    ref_id INT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notif_user_read (user_id, is_read, created_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 15. Audit Logs (Immutable security and state-change trail)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(40) NOT NULL,
    entity_type VARCHAR(20) NOT NULL,
    entity_id VARCHAR(20) NOT NULL,
    details JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_audit_query (entity_type, entity_id, created_at)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 16. Message Outbox (Simulated SMS / WhatsApp Notification Simulator)
-- Zero real SMS/WhatsApp sent. Masked numbers only. Transactionally integrated.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS message_outbox (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    campus_id TINYINT NOT NULL,
    channel ENUM('SMS','WHATSAPP','EMAIL') NOT NULL DEFAULT 'SMS',
    template_code VARCHAR(50) NOT NULL,
    body VARCHAR(480) NOT NULL,
    to_phone_masked VARCHAR(35) NULL,
    ref_type VARCHAR(20) NULL,
    ref_id INT NULL,
    status ENUM('SIMULATED','READ') NOT NULL DEFAULT 'SIMULATED',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_outbox_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_outbox_campus FOREIGN KEY (campus_id) REFERENCES campuses(campus_id) ON DELETE RESTRICT,
    INDEX idx_outbox_user_created (user_id, created_at),
    INDEX idx_outbox_campus_created (campus_id, created_at)
) ENGINE=InnoDB;

