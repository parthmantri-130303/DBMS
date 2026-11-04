# Entity-Relationship (ER) Diagram

**System**: CampusKhoj — Two-Campus Lost & Found System  
**Database**: MySQL 8.0.46 Community Edition (campuskhoj_zero)  
**Schema Definition**: Live extraction from INFORMATION_SCHEMA (17 Tables)  

---

## 1. Complete System ER Diagram

`mermaid
erDiagram
    users ||--o{ audit_logs : "user_id -> user_id"
    claims ||--o{ claim_messages : "claim_id -> claim_id"
    users ||--o{ claim_messages : "sender_id -> user_id"
    users ||--o{ claim_verifications : "asked_by -> user_id"
    claims ||--o{ claim_verifications : "claim_id -> claim_id"
    users ||--o{ claim_verifications : "verified_by -> user_id"
    campuses ||--o{ claims : "campus_id -> campus_id"
    users ||--o{ claims : "claimant_id -> user_id"
    found_items ||--o{ claims : "found_id -> found_id"
    users ||--o{ claims : "handed_over_by -> user_id"
    lost_items ||--o{ claims : "lost_id -> lost_id"
    users ||--o{ claims : "reviewed_by -> user_id"
    campuses ||--o{ found_items : "campus_id -> campus_id"
    categories ||--o{ found_items : "category_id -> category_id"
    locations ||--o{ found_items : "location_id -> location_id"
    locations ||--o{ found_items : "campus_id -> campus_id"
    users ||--o{ found_items : "user_id -> user_id"
    users ||--o{ item_events : "actor_id -> user_id"
    campuses ||--o{ item_events : "campus_id -> campus_id"
    campuses ||--o{ locations : "campus_id -> campus_id"
    campuses ||--o{ lost_items : "campus_id -> campus_id"
    categories ||--o{ lost_items : "category_id -> category_id"
    locations ||--o{ lost_items : "location_id -> location_id"
    locations ||--o{ lost_items : "campus_id -> campus_id"
    users ||--o{ lost_items : "user_id -> user_id"
    campuses ||--o{ match_suggestions : "campus_id -> campus_id"
    found_items ||--o{ match_suggestions : "found_id -> found_id"
    lost_items ||--o{ match_suggestions : "lost_id -> lost_id"
    campuses ||--o{ message_outbox : "campus_id -> campus_id"
    users ||--o{ message_outbox : "user_id -> user_id"
    users ||--o{ notifications : "user_id -> user_id"
    campuses ||--o{ prn_registry : "campus_id -> campus_id"
    users ||--o{ prn_registry : "imported_by -> user_id"
    campuses ||--o{ users : "campus_id -> campus_id"
    prn_registry ||--o{ users : "prn -> prn"
    roles ||--o{ users : "role_id -> role_id"

    audit_logs {
        bigint log_id
        int user_id
        varchar action
        varchar entity_type
        varchar entity_id
        json details
        varchar ip_address
        datetime created_at
    }

    campuses {
        tinyint campus_id
        varchar campus_name
        varchar code
        datetime created_at
    }

    categories {
        smallint category_id
        varchar category_name
        varchar description
        varchar icon
        datetime created_at
    }

    claim_messages {
        bigint message_id
        int claim_id
        int sender_id
        enum sender_role
        text message_text
        datetime sent_at
        datetime read_at
    }

    claim_verifications {
        int verification_id
        int claim_id
        varchar question
        varchar expected_evidence
        text answer
        enum verification_status
        int asked_by
        int verified_by
        datetime verified_at
        datetime created_at
    }

    claims {
        int claim_id
        int found_id
        int lost_id
        int claimant_id
        tinyint campus_id
        text claim_description
        varchar proof_url
        varchar proof_type
        enum claim_status
        varchar reject_reason
        datetime submitted_at
        datetime reviewed_at
        int reviewed_by
        datetime handed_over_at
        int handed_over_by
        tinyint active_key
    }

    found_items {
        int found_id
        int user_id
        tinyint campus_id
        smallint category_id
        int location_id
        varchar room_no
        varchar specific_spot
        varchar item_name
        varchar brand
        varchar color
        text description
        text private_details
        date date_found
        time time_found
        varchar image_url
        enum custody
        varchar storage_location
        enum status
        datetime created_at
        datetime updated_at
    }

    item_events {
        bigint event_id
        enum item_type
        int item_id
        tinyint campus_id
        varchar event_type
        varchar title
        varchar description
        int actor_id
        tinyint is_public
        datetime created_at
    }

    locations {
        int location_id
        tinyint campus_id
        varchar location_name
        varchar room_or_spot
        varchar building
        varchar floor
        varchar description
        smallint sort_order
        tinyint is_active
        datetime created_at
    }

    login_attempts {
        bigint attempt_id
        varchar identifier
        varchar ip_address
        tinyint success
        datetime attempted_at
    }

    lost_items {
        int lost_id
        int user_id
        tinyint campus_id
        smallint category_id
        int location_id
        varchar room_no
        varchar specific_spot
        varchar item_name
        text description
        varchar brand
        varchar color
        date date_lost
        time time_lost
        varchar image_url
        enum status
        datetime created_at
        datetime updated_at
    }

    match_suggestions {
        int match_id
        int lost_id
        int found_id
        tinyint campus_id
        tinyint score
        json breakdown
        datetime created_at
    }

    message_outbox {
        int message_id
        int user_id
        tinyint campus_id
        enum channel
        varchar template_code
        varchar body
        varchar to_phone_masked
        varchar ref_type
        int ref_id
        enum status
        datetime created_at
    }

    notifications {
        bigint notification_id
        int user_id
        varchar message
        varchar notification_type
        varchar ref_type
        int ref_id
        tinyint is_read
        datetime created_at
    }

    prn_registry {
        char prn
        tinyint campus_id
        datetime imported_at
        int imported_by
    }

    roles {
        tinyint role_id
        varchar role_name
    }

    users {
        int user_id
        char prn
        varchar staff_username
        varchar name
        varchar email
        varchar phone
        varchar password_hash
        tinyint must_change_password
        tinyint role_id
        tinyint campus_id
        enum status
        datetime last_password_change
        tinyint profile_completed
        datetime created_at
        datetime updated_at
    }

'`

---

## 2. Relational Design Highlights

### A. Strict Cross-Campus Isolation via Composite Foreign Keys
Cross-campus data integrity is enforced natively at the MySQL engine layer:
`sql
CONSTRAINT uq_loc_campus UNIQUE (location_id, campus_id)
`
Referenced by both lost_items and ound_items:
`sql
CONSTRAINT fk_lost_location_campus FOREIGN KEY (location_id, campus_id)
    REFERENCES locations(location_id, campus_id) ON DELETE RESTRICT
`
It is mathematically impossible to assign a Kondhwa location to a Bibwewadi item.

### B. Single Active Claim Guarantee via Stored Generated Column
Students may file only one simultaneous active claim per found item:
`sql
active_key TINYINT GENERATED ALWAYS AS (
    CASE WHEN claim_status IN ('PENDING','UNDER_REVIEW','APPROVED') THEN 1 ELSE NULL END
) STORED,
CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)
`
When a claim reaches REJECTED, COMPLETED, or CANCELLED, ctive_key evaluates to NULL. Since MySQL standard allows multiple NULL values in a unique index, history is preserved without blocking future legitimate claims.

### C. Exactly-One Identity Constraint & Staff Campus Scoping
1. Users are strictly partitioned into Students (PRN) and Staff (staff_username):
`sql
CONSTRAINT chk_user_identity CHECK ((prn IS NOT NULL) <> (staff_username IS NOT NULL))
`
2. Staff campus assignments are validated at both the API and database levels:
`sql
CONSTRAINT chk_staff_campus CHECK ((role_id = 4 AND campus_id IS NULL) OR (role_id != 4 AND campus_id IS NOT NULL))
`
Campus Admins and Security officers require a valid campus assignment, while Super Admins operate globally.

### D. Claims Messaging & Simulated Notification Outbox
- claim_messages: Direct bilateral communication between claimant and desk staff during verification review.
- message_outbox: Transactionally logs all outbound SMS/WhatsApp notifications with masked phone numbers (	o_phone_masked), ensuring auditability without leaking student PII.
