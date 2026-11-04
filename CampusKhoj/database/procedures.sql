-- CampusKhoj Stored Procedures
-- Source of truth: Docs/05_backend_schema.md §2.5

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_approve_claim$$
CREATE PROCEDURE sp_approve_claim(
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

    -- Rollback handler on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_message = 'Database error occurred during claim approval transaction';
    END;

    -- Fetch claim details
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

    -- 1. Update target claim to APPROVED
    UPDATE claims
       SET claim_status = 'APPROVED',
           reviewed_by = p_staff_id,
           reviewed_at = NOW()
     WHERE claim_id = p_claim_id;

    -- 2. Mark found item as CLAIMED
    UPDATE found_items
       SET status = 'CLAIMED'
     WHERE found_id = v_found_id;

    -- 3. If linked to a lost item report, mark that report CLAIMED
    IF v_lost_id IS NOT NULL THEN
        UPDATE lost_items
           SET status = 'CLAIMED'
         WHERE lost_id = v_lost_id;
    END IF;

    -- 4. Automatically reject any other pending claims on this found item
    UPDATE claims
       SET claim_status = 'REJECTED',
           reject_reason = 'Another claim on this item was approved',
           reviewed_by = p_staff_id,
           reviewed_at = NOW()
     WHERE found_id = v_found_id
       AND claim_id <> p_claim_id
       AND claim_status IN ('PENDING', 'UNDER_REVIEW');

    -- 5. Record timeline events
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

    -- 6. Issue in-app notification to claimant
    INSERT INTO notifications (
        user_id, message, notification_type, ref_type, ref_id, is_read, created_at
    ) VALUES (
        v_claimant_id,
        'Good news! Your claim has been approved. Please visit your campus security desk with your college ID card for handover.',
        'CLAIM_APPROVED', 'CLAIM', p_claim_id, 0, NOW()
    );

    -- 6b. Insert simulated SMS outbox inside the same atomic transaction
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

    -- 7. Audit log row
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
END proc_label$$

DELIMITER ;

