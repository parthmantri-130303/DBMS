# Test Execution Results & Requirements Traceability Matrix

**Project**: CampusKhoj — Two-Campus Lost & Found System  
**Test Suites**: Unit & Workflow Suite (`run_all.py`) + Live MySQL Integration Suite (`test_live_mysql.py`)  
**Execution Environment**: Python 3.11.9, MySQL 8.0.46 Community Edition (`campuskhoj_zero`), Headless Chromium  
**Date**: November 2026  
**Overall Verdict**: **53 / 53 TESTS PASSED (100% SUCCESS RATE)**  

---

## 1. Executive Summary

| Test Category | Suite File | Total Tests | Passed | Failed | Skipped | Execution Time |
|---|---|---|---|---|---|---|
| **Hermetic Unit & Security** | `backend/tests/run_all.py` | 45 | 45 | 0 | 0 | 1.62s |
| **Live MySQL 8 Integration** | `backend/tests/test_live_mysql.py` | 8 | 8 | 0 | 0 | 1.08s |
| **Comprehensive E2E Audit** | `scripts/comprehensive_feature_audit.js` | 36 Checks | 36 Passed | 0 | 0 | 24.2s |
| **Total** | | **53 Automated** | **53** | **0** | **0** | **26.90s** |

---

## 2. Live MySQL 8.0 Integration Test Output

Executed directly against live MySQL 8.0.46 Community Server instance on port 3307 targeting `campuskhoj_zero`:

```text
test_a_composite_fk_rejects_cross_campus_location (backend.tests.test_live_mysql.TestLiveMySQL.test_a_composite_fk_rejects_cross_campus_location)
(a) Inserting a lost item with a location from the other campus fails on composite FK (location_id, campus_id) ... ok
test_b_duplicate_active_claim_rejected_by_stored_generated_active_key (backend.tests.test_live_mysql.TestLiveMySQL.test_b_duplicate_active_claim_rejected_by_stored_generated_active_key)
(b) A second live claim by the same student on the same found item fails on stored generated active_key ... ok
test_c_sp_approve_claim_execution_and_rollback (backend.tests.test_live_mysql.TestLiveMySQL.test_c_sp_approve_claim_execution_and_rollback)
(c) sp_approve_claim executes atomically, auto-rejects competing claims, and rolls back on failure ... ok
test_d_triggers_write_audit_and_event_rows (backend.tests.test_live_mysql.TestLiveMySQL.test_d_triggers_write_audit_and_event_rows)
(d) Triggers automatically write audit_logs and item_events rows upon state transitions ... ok
test_e_full_journey_against_live_mysql (backend.tests.test_live_mysql.TestLiveMySQL.test_e_full_journey_against_live_mysql)
(e) Full journey through Flask API against live MySQL 8: first login -> report -> match -> claim -> verify -> approve -> handover ... ok
test_f_message_outbox_transactional_insert_and_rollback (backend.tests.test_live_mysql.TestLiveMySQL.test_f_message_outbox_transactional_insert_and_rollback)
(f) Message outbox rows are committed on event success and rolled back atomically on failure ... ok
test_g_staff_campus_check_constraint (backend.tests.test_live_mysql.TestLiveMySQL.test_g_staff_campus_check_constraint)
(g) MySQL CHECK constraint chk_staff_campus requires campus_id for staff and NULL for super admin ... ok
test_h_fulltext_search_index_usage (backend.tests.test_live_mysql.TestLiveMySQL.test_h_fulltext_search_index_usage)
(h) EXPLAIN verifies fulltext index ft_found_search is utilized for item keyword search ... ok

----------------------------------------------------------------------
Ran 8 tests in 1.082s

OK
```

---

## 3. Hermetic Unit, Workflow & Regression Test Output

Executed via `python -m backend.tests.run_all`:

```text
test_t01_unknown_prn_login_fails (test_auth.TestAuth.test_t01_unknown_prn_login_fails) ... ok
test_t02_first_login_with_prn_credential (test_auth.TestAuth.test_t02_first_login_with_prn_credential) ... ok
test_t03_scope_enforcement_pwd_change_blocked (test_auth.TestAuth.test_t03_scope_enforcement_pwd_change_blocked) ... ok
test_t04_password_validation_rules (test_auth.TestAuth.test_t04_password_validation_rules) ... ok
test_t05_prn_credential_disabled_after_change (test_auth.TestAuth.test_t05_prn_credential_disabled_after_change) ... ok
test_t06_account_lockout_after_failed_attempts (test_auth.TestAuth.test_t06_account_lockout_after_failed_attempts) ... ok
test_t07_portal_separation_student_blocked_from_admin (test_auth.TestAuth.test_t07_portal_separation_student_blocked_from_admin) ... ok
test_t08_cross_campus_location_rejected (test_campus_rules.TestCampusRules.test_t08_cross_campus_location_rejected) ... ok
test_t09_cross_campus_claim_rejected (test_campus_rules.TestCampusRules.test_t09_cross_campus_claim_rejected) ... ok
test_t10_matcher_strictly_isolates_campuses (test_campus_rules.TestCampusRules.test_t10_matcher_strictly_isolates_campuses) ... ok
test_t11_cross_campus_browsing_allowed (test_campus_rules.TestCampusRules.test_t11_cross_campus_browsing_allowed) ... ok
test_finding_1_and_2_cross_campus_staff_privacy_leak_blocked (test_code_review_fixes.TestCodeReviewFixes.test_finding_1_and_2_cross_campus_staff_privacy_leak_blocked) ... ok
test_finding_2_pwd_change_scope_blocked (test_code_review_fixes.TestCodeReviewFixes.test_finding_2_pwd_change_scope_blocked) ... ok
test_finding_2_suspended_account_rejected (test_code_review_fixes.TestCodeReviewFixes.test_finding_2_suspended_account_rejected) ... ok
test_finding_3_finder_sees_own_private_details (test_code_review_fixes.TestCodeReviewFixes.test_finding_3_finder_sees_own_private_details) ... ok
test_finding_4_and_5_staff_creation_validation (test_code_review_fixes.TestCodeReviewFixes.test_finding_4_and_5_staff_creation_validation) ... ok
test_finding_4_staff_first_login_forces_pwd_change (test_code_review_fixes.TestCodeReviewFixes.test_finding_4_staff_first_login_forces_pwd_change) ... ok
test_finding_8_search_wildcard_sanitization (test_code_review_fixes.TestCodeReviewFixes.test_finding_8_search_wildcard_sanitization) ... ok
test_finding_9_pagination_validation (test_code_review_fixes.TestCodeReviewFixes.test_finding_9_pagination_validation) ... ok
test_journey_1_first_login_password_change_profile_setup (test_critical_journeys.TestCriticalJourneys.test_journey_1_first_login_password_change_profile_setup) ... ok
test_journey_2_and_3_report_lost_and_found_trigger_matcher (test_critical_journeys.TestCriticalJourneys.test_journey_2_and_3_report_lost_and_found_trigger_matcher) ... ok
test_journey_4_claim_submission_and_question_answers (test_critical_journeys.TestCriticalJourneys.test_journey_4_claim_submission_and_question_answers) ... ok
test_journey_5_and_6_claim_approval_and_physical_handover (test_critical_journeys.TestCriticalJourneys.test_journey_5_and_6_claim_approval_and_physical_handover) ... ok
test_journey_7_cross_campus_violation_rejection (test_critical_journeys.TestCriticalJourneys.test_journey_7_cross_campus_violation_rejection) ... ok
test_t12_report_validation_future_date_rejected (test_items_and_privacy.TestItemsAndPrivacy.test_t12_report_validation_future_date_rejected) ... ok
test_t13_upload_validation_rejected (test_items_and_privacy.TestItemsAndPrivacy.test_t13_upload_validation_rejected) ... ok
test_t14_privacy_leak_prevention (test_items_and_privacy.TestItemsAndPrivacy.test_t14_privacy_leak_prevention) ... ok
test_t15_duplicate_active_claim_rejected (test_items_and_privacy.TestItemsAndPrivacy.test_t15_duplicate_active_claim_rejected) ... ok
test_t16_claim_own_found_report_rejected (test_items_and_privacy.TestItemsAndPrivacy.test_t16_claim_own_found_report_rejected) ... ok
test_t17_student_cannot_see_expected_evidence (test_items_and_privacy.TestItemsAndPrivacy.test_t17_student_cannot_see_expected_evidence) ... ok
test_t26_found_recent_feed (test_items_and_privacy.TestItemsAndPrivacy.test_t26_found_recent_feed) ... ok
test_t27_found_historical_search_includes_claimed_items (test_items_and_privacy.TestItemsAndPrivacy.test_t27_found_historical_search_includes_claimed_items) ... ok
test_t28_double_verification_request_flow (test_items_and_privacy.TestItemsAndPrivacy.test_t28_double_verification_request_flow) ... ok
test_t29_simulated_sms_notification_endpoint (test_items_and_privacy.TestItemsAndPrivacy.test_t29_simulated_sms_notification_endpoint) ... ok
test_mask_phone (test_messages.TestMessageTemplates.test_mask_phone) ... ok
test_template_codes_exist (test_messages.TestMessageTemplates.test_template_codes_exist) ... ok
test_templates_never_leak_private_fields (test_messages.TestMessageTemplates.test_templates_never_leak_private_fields) ... ok
test_t18_approval_transaction_rollback_on_failure (test_workflow_and_rollback.TestWorkflowAndRollback.test_t18_approval_transaction_rollback_on_failure) ... ok
test_t19_handover_before_approval_rejected (test_workflow_and_rollback.TestWorkflowAndRollback.test_t19_handover_before_approval_rejected) ... ok
test_t20_timeline_visibility_public_vs_private (test_workflow_and_rollback.TestWorkflowAndRollback.test_t20_timeline_visibility_public_vs_private) ... ok
test_t21_handover_success_flow (test_workflow_and_rollback.TestWorkflowAndRollback.test_t21_handover_success_flow) ... ok
test_t22_profile_email_prn_mismatch_rejected (test_workflow_and_rollback.TestWorkflowAndRollback.test_t22_profile_email_prn_mismatch_rejected) ... ok
test_t23_rate_limiting_enforcement (test_workflow_and_rollback.TestWorkflowAndRollback.test_t23_rate_limiting_enforcement) ... ok
test_t24_idor_prevention_on_patch_report (test_workflow_and_rollback.TestWorkflowAndRollback.test_t24_idor_prevention_on_patch_report) ... ok
test_t25_batch_prn_import_endpoint (test_workflow_and_rollback.TestWorkflowAndRollback.test_t25_batch_prn_import_endpoint) ... ok

----------------------------------------------------------------------
Ran 45 tests in 1.615s

OK
```

---

## 4. Requirements Traceability Matrix (RTM)

| Requirement / Bug ID | Severity | Verification Test | Result |
|---|---|---|---|
| **R-01**: PRN Whitelist Authentication | Mandatory | `test_t01`, `test_t02`, `test_journey_1` | PASS |
| **R-02**: Forced First Password Change | High | `test_t03`, `test_t04`, `test_t05`, `test_finding_2_pwd_change_scope_blocked` | PASS |
| **R-03**: Cross-Campus Location Shield | High | `test_t08`, `test_a_composite_fk_rejects_cross_campus_location` | PASS |
| **R-04**: Single Active Claim Invariant | High | `test_t15`, `test_b_duplicate_active_claim_rejected_by_stored_generated_active_key` | PASS |
| **R-05**: Privacy Leak Prevention (Findings 1 & 2) | Critical (S1) | `test_t14`, `test_finding_1_and_2_cross_campus_staff_privacy_leak_blocked` | PASS |
| **R-06**: Finder Self-Inspection (Finding 3) | Medium (S2) | `test_finding_3_finder_sees_own_private_details` | PASS |
| **R-07**: Staff Password Strength & Forced Change (Finding 4) | High (S1) | `test_finding_4_and_5_staff_creation_validation`, `test_finding_4_staff_first_login_forces_pwd_change` | PASS |
| **R-08**: Staff Campus Scoping & Constraint (Finding 5) | Medium (S2) | `test_finding_4_and_5_staff_creation_validation`, `test_g_staff_campus_check_constraint` | PASS |
| **R-09**: Fulltext Search & Sanitization (Finding 8) | Medium (S3) | `test_finding_8_search_wildcard_sanitization`, `test_h_fulltext_search_index_usage` | PASS |
| **R-10**: Pagination Input Hardening (Finding 9) | Low (S3) | `test_finding_9_pagination_validation` | PASS |
| **R-11**: Atomic Claim Approval & Rollback | Critical | `test_t18`, `test_c_sp_approve_claim_execution_and_rollback` | PASS |
| **R-12**: Outbox Notification Rollback | High | `test_f_message_outbox_transactional_insert_and_rollback` | PASS |
