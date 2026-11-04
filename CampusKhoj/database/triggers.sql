-- CampusKhoj Database Triggers
-- Source of truth: Docs/05_backend_schema.md §2.5

DELIMITER $$

-- ----------------------------------------------------------------------------
-- 1. Trigger: trg_claims_status_audit
-- Ensures every claim status change (even direct DB edits) is traced into audit_logs
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_claims_status_audit$$
CREATE TRIGGER trg_claims_status_audit
AFTER UPDATE ON claims
FOR EACH ROW
BEGIN
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
END$$

-- ----------------------------------------------------------------------------
-- 2. Trigger: trg_lost_status_event
-- Automatic fallback to capture lost item status transitions into item_events
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_lost_status_event$$
CREATE TRIGGER trg_lost_status_event
AFTER UPDATE ON lost_items
FOR EACH ROW
BEGIN
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
END$$

-- ----------------------------------------------------------------------------
-- 3. Trigger: trg_found_status_event
-- Automatic fallback to capture found item status transitions into item_events
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_found_status_event$$
CREATE TRIGGER trg_found_status_event
AFTER UPDATE ON found_items
FOR EACH ROW
BEGIN
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
END$$

-- ----------------------------------------------------------------------------
-- 4. Trigger: trg_users_pwd_change
-- Audit log recorded whenever password hash is updated
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_users_pwd_change$$
CREATE TRIGGER trg_users_pwd_change
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
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
END$$

DELIMITER ;

