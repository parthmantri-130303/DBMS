-- CampusKhoj Database Views
-- Source of truth: Docs/05_backend_schema.md §2.5

-- ----------------------------------------------------------------------------
-- 1. v_active_lost: Public view of active lost items
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_lost AS
SELECT
    l.lost_id,
    l.item_name,
    l.category_id,
    c.category_name,
    c.icon AS category_icon,
    l.campus_id,
    cp.campus_name,
    cp.code AS campus_code,
    l.location_id,
    loc.location_name,
    loc.building,
    loc.floor,
    l.brand,
    l.color,
    l.description,
    l.date_lost,
    l.time_lost,
    l.image_url,
    l.status,
    l.created_at
FROM lost_items l
JOIN categories c ON l.category_id = c.category_id
JOIN campuses cp ON l.campus_id = cp.campus_id
JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
WHERE l.status IN ('ACTIVE', 'MATCHED');

-- ----------------------------------------------------------------------------
-- 2. v_active_found: Public view of active found items
-- CRITICAL PRIVACY: private_details and storage_location are NEVER exposed here!
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_found AS
SELECT
    f.found_id,
    f.item_name,
    f.category_id,
    c.category_name,
    c.icon AS category_icon,
    f.campus_id,
    cp.campus_name,
    cp.code AS campus_code,
    f.location_id,
    loc.location_name,
    loc.building,
    loc.floor,
    f.brand,
    f.color,
    f.description,
    f.date_found,
    f.time_found,
    f.image_url,
    f.custody,
    f.status,
    f.created_at
FROM found_items f
JOIN categories c ON f.category_id = c.category_id
JOIN campuses cp ON f.campus_id = cp.campus_id
JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
WHERE f.status IN ('ACTIVE', 'MATCHED');

-- ----------------------------------------------------------------------------
-- 3. v_pending_claims: Claim queue for admin and security desk
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_pending_claims AS
SELECT
    cl.claim_id,
    cl.found_id,
    fi.item_name AS found_item_name,
    fi.image_url AS found_image_url,
    cl.lost_id,
    cl.claimant_id,
    u.prn AS claimant_prn,
    u.name AS claimant_name,
    u.phone AS claimant_phone,
    cl.campus_id,
    cp.campus_name,
    cl.claim_description,
    cl.claim_status,
    cl.submitted_at,
    cl.reviewed_at,
    cl.reviewed_by,
    (SELECT COUNT(*) FROM claim_verifications cv WHERE cv.claim_id = cl.claim_id) AS total_questions,
    (SELECT COUNT(*) FROM claim_verifications cv WHERE cv.claim_id = cl.claim_id AND cv.verification_status = 'ANSWERED') AS answered_questions,
    (SELECT COUNT(*) FROM claim_verifications cv WHERE cv.claim_id = cl.claim_id AND cv.verification_status = 'VERIFIED') AS verified_questions
FROM claims cl
JOIN found_items fi ON cl.found_id = fi.found_id
JOIN users u ON cl.claimant_id = u.user_id
JOIN campuses cp ON cl.campus_id = cp.campus_id
WHERE cl.claim_status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED');

-- ----------------------------------------------------------------------------
-- 4. v_dashboard_stats: Campus & aggregate KPIs
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_dashboard_stats AS
SELECT
    cp.campus_id,
    cp.campus_name,
    cp.code AS campus_code,
    (SELECT COUNT(*) FROM lost_items l WHERE l.campus_id = cp.campus_id AND l.status IN ('ACTIVE','MATCHED')) AS active_lost_count,
    (SELECT COUNT(*) FROM found_items f WHERE f.campus_id = cp.campus_id AND f.status IN ('ACTIVE','MATCHED')) AS active_found_count,
    (SELECT COUNT(*) FROM claims cl WHERE cl.campus_id = cp.campus_id AND cl.claim_status IN ('PENDING','UNDER_REVIEW')) AS pending_claims_count,
    (SELECT COUNT(*) FROM found_items f WHERE f.campus_id = cp.campus_id AND f.status = 'HANDED_OVER') AS returned_items_count,
    (SELECT COUNT(*) FROM users u WHERE u.campus_id = cp.campus_id AND u.status = 'ACTIVE') AS registered_students_count,
    ROUND(
        CASE
            WHEN (SELECT COUNT(*) FROM lost_items l WHERE l.campus_id = cp.campus_id) = 0 THEN 0
            ELSE ((SELECT COUNT(*) FROM lost_items l WHERE l.campus_id = cp.campus_id AND l.status = 'RETURNED') * 100.0) /
                 (SELECT COUNT(*) FROM lost_items l WHERE l.campus_id = cp.campus_id)
        END, 1
    ) AS recovery_rate_pct
FROM campuses cp;

-- ----------------------------------------------------------------------------
-- 5. v_top_locations: Frequent loss/found hotspots for analytics
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_top_locations AS
SELECT
    loc.campus_id,
    cp.campus_name,
    loc.location_id,
    loc.location_name,
    loc.building,
    COUNT(DISTINCT l.lost_id) AS lost_count,
    COUNT(DISTINCT f.found_id) AS found_count,
    (COUNT(DISTINCT l.lost_id) + COUNT(DISTINCT f.found_id)) AS total_incidents
FROM locations loc
JOIN campuses cp ON loc.campus_id = cp.campus_id
LEFT JOIN lost_items l ON loc.location_id = l.location_id AND loc.campus_id = l.campus_id
LEFT JOIN found_items f ON loc.location_id = f.location_id AND loc.campus_id = f.campus_id
GROUP BY loc.campus_id, cp.campus_name, loc.location_id, loc.location_name, loc.building
ORDER BY total_incidents DESC;

-- ----------------------------------------------------------------------------
-- 6. v_top_categories: Most frequently lost & found categories
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_top_categories AS
SELECT
    c.category_id,
    c.category_name,
    c.icon,
    COUNT(DISTINCT l.lost_id) AS lost_count,
    COUNT(DISTINCT f.found_id) AS found_count,
    (COUNT(DISTINCT l.lost_id) + COUNT(DISTINCT f.found_id)) AS total_items
FROM categories c
LEFT JOIN lost_items l ON c.category_id = l.category_id
LEFT JOIN found_items f ON c.category_id = f.category_id
GROUP BY c.category_id, c.category_name, c.icon
ORDER BY total_items DESC;

-- ----------------------------------------------------------------------------
-- 7. v_monthly_trend: Monthly report trends
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_monthly_trend AS
SELECT
    DATE_FORMAT(report_date, '%Y-%m') AS `month`,
    campus_id,
    SUM(CASE WHEN item_type = 'LOST' THEN 1 ELSE 0 END) AS lost_reported,
    SUM(CASE WHEN item_type = 'FOUND' THEN 1 ELSE 0 END) AS found_reported,
    SUM(CASE WHEN status IN ('RETURNED', 'HANDED_OVER') THEN 1 ELSE 0 END) AS resolved_count
FROM (
    SELECT 'LOST' AS item_type, date_lost AS report_date, campus_id, status FROM lost_items
    UNION ALL
    SELECT 'FOUND' AS item_type, date_found AS report_date, campus_id, status FROM found_items
) combined_reports
GROUP BY DATE_FORMAT(report_date, '%Y-%m'), campus_id
ORDER BY `month` DESC;

-- ----------------------------------------------------------------------------
-- 8. v_campus_comparison: Side-by-side comparison between Kondhwa and Bibwewadi
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_campus_comparison AS
SELECT
    cp.campus_id,
    cp.campus_name,
    cp.code,
    COUNT(DISTINCT pr.prn) AS total_enrolled_students,
    COUNT(DISTINCT u.user_id) AS active_accounts,
    COUNT(DISTINCT l.lost_id) AS total_lost_reports,
    COUNT(DISTINCT f.found_id) AS total_found_reports,
    COUNT(DISTINCT cl.claim_id) AS total_claims_filed,
    COUNT(DISTINCT CASE WHEN f.status = 'HANDED_OVER' THEN f.found_id END) AS total_successful_handovers
FROM campuses cp
LEFT JOIN prn_registry pr ON cp.campus_id = pr.campus_id
LEFT JOIN users u ON cp.campus_id = u.campus_id
LEFT JOIN lost_items l ON cp.campus_id = l.campus_id
LEFT JOIN found_items f ON cp.campus_id = f.campus_id
LEFT JOIN claims cl ON cp.campus_id = cl.campus_id
GROUP BY cp.campus_id, cp.campus_name, cp.code;

