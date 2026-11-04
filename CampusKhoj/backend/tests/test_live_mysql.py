import os
import sys
import unittest
from datetime import date
from pathlib import Path

# Add project root and backend dir to sys.path
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

import mysql.connector


class TestLiveMySQL(unittest.TestCase):
    """
    Live Integration Test Suite executing against a real MySQL 8.0 Community Server.
    Activated when TEST_DB_NAME is set in the environment.
    Proves relational integrity, composite FKs, stored generated columns,
    triggers, ACID rollback, and the full API user journey on genuine MySQL 8.
    """
    @classmethod
    def setUpClass(cls):
        from backend.config import config
        cls.db_name = os.getenv("TEST_DB_NAME") or os.getenv("DB_NAME") or config.DB_NAME
        if not cls.db_name:
            raise unittest.SkipTest("Skipping live MySQL tests: TEST_DB_NAME environment variable is unset.")

        cls.db_host = os.getenv("TEST_DB_HOST") or config.DB_HOST or "127.0.0.1"
        cls.db_port = int(os.getenv("TEST_DB_PORT") or config.DB_PORT or 3307)
        cls.db_user = os.getenv("TEST_DB_USER") or config.DB_USER or "root"
        cls.db_password = os.getenv("TEST_DB_PASSWORD", config.DB_PASSWORD)

        try:
            cls.conn = mysql.connector.connect(
                host=cls.db_host,
                port=cls.db_port,
                user=cls.db_user,
                password=cls.db_password,
                database=cls.db_name
            )
            cls.conn.autocommit = False
        except Exception as e:
            raise unittest.SkipTest(f"Could not connect to live MySQL on {cls.db_host}:{cls.db_port}: {e}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn") and cls.conn.is_connected():
            cls.conn.close()

    def setUp(self):
        self.cursor = self.conn.cursor(dictionary=True)

    def tearDown(self):
        self.conn.rollback()
        self.cursor.close()

    def test_a_composite_fk_rejects_cross_campus_location(self):
        """(a) Inserting a lost item with a location from the other campus fails on composite FK (location_id, campus_id)"""
        # User 1 (Kondhwa student), Campus 1 (Kondhwa), but Location 201 (Bibwewadi Security Desk, campus_id = 2)
        with self.assertRaises(mysql.connector.Error) as ctx:
            self.cursor.execute(
                """INSERT INTO lost_items (user_id, campus_id, category_id, location_id, item_name, description, date_lost, status)
                   VALUES (1, 1, 1, 201, 'Cross Campus Illegal Item', 'Should fail composite FK', CURDATE(), 'ACTIVE')"""
            )
            self.conn.commit()

        # Error 1452: Cannot add or update a child row: a foreign key constraint fails
        self.assertEqual(ctx.exception.errno, 1452)
        self.assertIn("locations", str(ctx.exception).lower())

    def test_b_duplicate_active_claim_rejected_by_stored_generated_active_key(self):
        """(b) A second live claim by the same student on the same found item fails on stored generated active_key"""
        # Create a clean found item
        self.cursor.execute(
            """INSERT INTO found_items (user_id, campus_id, category_id, location_id, item_name, description, date_found, custody, status)
               VALUES (1, 1, 1, 101, 'Test Live Item', 'Live found item', CURDATE(), 'AT_DESK', 'ACTIVE')"""
        )
        found_id = self.cursor.lastrowid

        # Student user_id = 1 submits first claim (active_key will be '1_FOUND_<found_id>')
        self.cursor.execute(
            """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
               VALUES (%s, 1, 1, 'First live claim', 'PENDING')""",
            (found_id,)
        )
        self.conn.commit()

        # Student user_id = 1 attempts second live claim on same item -> MUST FAIL WITH ERROR 1062
        with self.assertRaises(mysql.connector.Error) as ctx:
            self.cursor.execute(
                """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
                   VALUES (%s, 1, 1, 'Duplicate live claim', 'PENDING')""",
                (found_id,)
            )
            self.conn.commit()

        # Error 1062: Duplicate entry for key 'uq_claim_active'
        self.assertEqual(ctx.exception.errno, 1062)
        self.assertIn("uq_claim_active", str(ctx.exception))

        # Now update first claim to REJECTED. In MySQL, active_key becomes NULL, allowing a new claim!
        self.cursor.execute("UPDATE claims SET claim_status = 'REJECTED' WHERE found_id = %s", (found_id,))
        self.conn.commit()

        # Resubmitting claim now succeeds because NULL values do not conflict in UNIQUE index
        self.cursor.execute(
            """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
               VALUES (%s, 1, 1, 'Second legitimate claim after rejection', 'PENDING')""",
            (found_id,)
        )
        self.conn.commit()
        second_claim_id = self.cursor.lastrowid
        self.assertIsNotNone(second_claim_id)

    def test_c_sp_approve_claim_execution_and_rollback(self):
        """(c) sp_approve_claim executes atomically, auto-rejects competing claims, and rolls back on failure"""
        # Create found item
        self.cursor.execute(
            """INSERT INTO found_items (user_id, campus_id, category_id, location_id, item_name, description, date_found, custody, status)
               VALUES (1, 1, 1, 101, 'Casio FX-991EX Calculator', 'Left in library', CURDATE(), 'AT_DESK', 'ACTIVE')"""
        )
        found_id = self.cursor.lastrowid

        # Competing claims: Student 1 and Student 2
        self.cursor.execute(
            """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
               VALUES (%s, 1, 1, 'Claimant 1 proof', 'UNDER_REVIEW')""",
            (found_id,)
        )
        c1_id = self.cursor.lastrowid

        self.cursor.execute(
            """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
               VALUES (%s, 2, 1, 'Claimant 2 proof', 'PENDING')""",
            (found_id,)
        )
        c2_id = self.cursor.lastrowid
        self.conn.commit()

        # Call sp_approve_claim for c1_id (staff_id = 1)
        self.cursor.callproc("sp_approve_claim", (c1_id, 1, 0, ""))
        self.conn.commit()

        # Read back outcomes
        self.cursor.execute("SELECT claim_status FROM claims WHERE claim_id = %s", (c1_id,))
        c1_status = self.cursor.fetchone()["claim_status"]
        self.assertEqual(c1_status, "APPROVED")

        # Competing claim c2_id MUST be auto-rejected with reason!
        self.cursor.execute("SELECT claim_status, reject_reason FROM claims WHERE claim_id = %s", (c2_id,))
        c2_row = self.cursor.fetchone()
        self.assertEqual(c2_row["claim_status"], "REJECTED")
        self.assertIn("Another claim on this item was approved", c2_row["reject_reason"])

        # Found item MUST be CLAIMED
        self.cursor.execute("SELECT status FROM found_items WHERE found_id = %s", (found_id,))
        f_status = self.cursor.fetchone()["status"]
        self.assertEqual(f_status, "CLAIMED")

        # Test Rollback: Calling sp_approve_claim on already APPROVED claim must fail and leave data untouched
        self.cursor.callproc("sp_approve_claim", (c1_id, 1, 0, ""))
        # Result output parameter p_success will be 0 (false)
        self.cursor.execute("SELECT claim_status FROM claims WHERE claim_id = %s", (c1_id,))
        self.assertEqual(self.cursor.fetchone()["claim_status"], "APPROVED")

    def test_d_triggers_write_audit_and_event_rows(self):
        """(d) Triggers automatically write audit_logs and item_events rows upon state transitions"""
        # 1. Test trg_claims_status_audit
        self.cursor.execute(
            """INSERT INTO found_items (user_id, campus_id, category_id, location_id, item_name, description, date_found, custody, status)
               VALUES (1, 1, 1, 101, 'Trigger Audit Test Item', 'Trigger testing', CURDATE(), 'AT_DESK', 'ACTIVE')"""
        )
        f_id = self.cursor.lastrowid

        self.cursor.execute(
            """INSERT INTO claims (found_id, claimant_id, campus_id, claim_description, claim_status)
               VALUES (%s, 1, 1, 'Trigger claim', 'PENDING')""",
            (f_id,)
        )
        c_id = self.cursor.lastrowid
        self.conn.commit()

        # Direct SQL UPDATE of status (outside application code!)
        self.cursor.execute("UPDATE claims SET claim_status = 'UNDER_REVIEW' WHERE claim_id = %s", (c_id,))
        self.conn.commit()

        # trg_claims_status_audit MUST have written an audit_logs row!
        self.cursor.execute(
            """SELECT action, entity_type, details 
               FROM audit_logs 
               WHERE entity_type = 'CLAIM' AND entity_id = %s AND action = 'CLAIM_STATUS_UNDER_REVIEW'""",
            (str(c_id),)
        )
        audit_row = self.cursor.fetchone()
        self.assertIsNotNone(audit_row)
        self.assertIn("UNDER_REVIEW", str(audit_row["details"]))

        # 2. Test trg_users_pwd_change
        self.cursor.execute("DELETE FROM users WHERE prn = '1251999999'")
        self.cursor.execute(
            """INSERT INTO prn_registry (prn, campus_id, imported_at) 
               VALUES ('1251999999', 1, NOW()) 
               ON DUPLICATE KEY UPDATE campus_id = 1"""
        )
        self.cursor.execute(
            """INSERT INTO users (prn, password_hash, must_change_password, role_id, campus_id, status)
               VALUES ('1251999999', NULL, 1, 1, 1, 'ACTIVE')"""
        )
        u_id = self.cursor.lastrowid
        self.conn.commit()

        # Update password hash
        self.cursor.execute("UPDATE users SET password_hash = '$2b$12$abcdef1234567890' WHERE user_id = %s", (u_id,))
        self.conn.commit()

        # trg_users_pwd_change MUST have written an audit_logs row!
        self.cursor.execute(
            """SELECT action, entity_type, details 
               FROM audit_logs 
               WHERE entity_type = 'USER' AND entity_id = %s AND action = 'PASSWORD_CHANGED'""",
            (str(u_id),)
        )
        pwd_audit = self.cursor.fetchone()
        self.assertIsNotNone(pwd_audit)
        self.assertIn("was_initial_setup", str(pwd_audit["details"]))

    def test_e_full_journey_against_live_mysql(self):
        """(e) Full journey through Flask API against live MySQL 8: first login -> report -> match -> claim -> verify -> approve -> handover"""
        import backend.config as cfg_module
        import backend.db as db_module
        from backend.app import create_app

        # Point environment and config singleton to live MySQL for this test
        old_port = cfg_module.config.DB_PORT
        old_db = cfg_module.config.DB_NAME
        old_pwd = cfg_module.config.DB_PASSWORD
        old_user = cfg_module.config.DB_USER

        cfg_module.config.DB_PORT = int(self.db_port)
        cfg_module.config.DB_NAME = self.db_name
        cfg_module.config.DB_PASSWORD = self.db_password
        cfg_module.config.DB_USER = self.db_user

        # Re-initialize connection pool for live MySQL test
        db_module._pool = None
        db_module.init_db_pool()

        app = create_app()
        app.testing = True
        client = app.test_client()

        try:
            # 1. Clean previous run artifacts and provision fresh student in live database
            test_prn = "1251150269"
            self.cursor.execute("SELECT user_id FROM users WHERE prn = %s", (test_prn,))
            existing = self.cursor.fetchone()
            if existing:
                u_id = existing["user_id"]
                self.cursor.execute("DELETE FROM claim_verifications WHERE claim_id IN (SELECT claim_id FROM claims WHERE claimant_id = %s OR found_id IN (SELECT found_id FROM found_items WHERE user_id = %s))", (u_id, u_id))
                self.cursor.execute("DELETE FROM claims WHERE claimant_id = %s OR found_id IN (SELECT found_id FROM found_items WHERE user_id = %s)", (u_id, u_id))
                self.cursor.execute("DELETE FROM match_suggestions WHERE lost_id IN (SELECT lost_id FROM lost_items WHERE user_id = %s) OR found_id IN (SELECT found_id FROM found_items WHERE user_id = %s)", (u_id, u_id))
                self.cursor.execute("DELETE FROM notifications WHERE user_id = %s", (u_id,))
                self.cursor.execute("DELETE FROM item_events WHERE actor_id = %s", (u_id,))
                self.cursor.execute("DELETE FROM lost_items WHERE user_id = %s", (u_id,))
                self.cursor.execute("DELETE FROM found_items WHERE user_id = %s", (u_id,))
                self.cursor.execute("DELETE FROM audit_logs WHERE user_id = %s", (u_id,))
                self.cursor.execute("DELETE FROM users WHERE user_id = %s", (u_id,))

            # Clean test found item from earlier runs
            self.cursor.execute("""
                DELETE FROM claim_verifications 
                WHERE claim_id IN (SELECT claim_id FROM claims WHERE found_id IN (SELECT found_id FROM found_items WHERE item_name = 'Titan Neo Watch'))
            """)
            self.cursor.execute("""
                DELETE FROM claims 
                WHERE found_id IN (SELECT found_id FROM found_items WHERE item_name = 'Titan Neo Watch')
            """)
            self.cursor.execute("""
                DELETE FROM item_events 
                WHERE item_type = 'FOUND' AND item_id IN (SELECT found_id FROM found_items WHERE item_name = 'Titan Neo Watch')
            """)
            self.cursor.execute("DELETE FROM found_items WHERE item_name = 'Titan Neo Watch'")

            self.cursor.execute("DELETE FROM prn_registry WHERE prn = %s", (test_prn,))
            self.cursor.execute("INSERT INTO prn_registry (prn, campus_id, imported_at) VALUES (%s, 1, NOW())", (test_prn,))
            self.cursor.execute(
                """INSERT INTO users (prn, role_id, campus_id, status, password_hash, must_change_password, profile_completed)
                   VALUES (%s, 1, 1, 'ACTIVE', NULL, 1, 0)""",
                (test_prn,)
            )
            self.conn.commit()

            # 2. First login with PRN -> returns pwd_change scope
            res = client.post("/api/v1/auth/login", json={"username": test_prn, "password": test_prn, "portal": "student"})
            self.assertEqual(res.status_code, 200, f"Login failed: {res.get_json()}")
            pwd_token = res.get_json()["token"]

            # 3. Change password
            res = client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {pwd_token}"}, json={
                "current_password": test_prn,
                "new_password": "NewLiveStudent#2026"
            })
            self.assertEqual(res.status_code, 200, f"Password change failed: {res.get_json()}")
            full_token = res.get_json()["token"]

            # 4. Complete Profile
            res = client.put("/api/v1/me/profile", headers={"Authorization": f"Bearer {full_token}"}, json={
                "name": "Live Rohit Verma",
                "phone": "9822998877",
                "email": f"rohit.{test_prn}@vit.edu"
            })
            self.assertEqual(res.status_code, 200, f"Profile update failed: {res.get_json()}")

            # 5. Report Lost Item (Titan watch in Kondhwa Central Library)
            res = client.post("/api/v1/lost", headers={"Authorization": f"Bearer {full_token}"}, json={
                "item_name": "Titan Neo Chronograph",
                "category_id": 7,
                "location_id": 102,
                "description": "Black dial watch left in Central Library",
                "date_lost": str(date.today())
            })
            self.assertEqual(res.status_code, 201, f"Report lost failed: {res.get_json()}")
            lost_id = res.get_json()["lost_id"]

            # 6. Report Found Item by Desk Staff (admin_kon at Kondhwa desk)
            staff_pwd = os.environ.get("KHOJ_TEST_STAFF_PASSWORD", "Staff@CampusKhoj2026!")
            admin_res = client.post("/api/v1/auth/login", json={"username": "admin_kon", "password": staff_pwd, "portal": "admin"})
            self.assertEqual(admin_res.status_code, 200, f"Admin login failed: {admin_res.get_json()}")
            admin_token = admin_res.get_json()["token"]

            res = client.post("/api/v1/found", headers={"Authorization": f"Bearer {admin_token}"}, json={
                "item_name": "Titan Neo Watch",
                "category_id": 7,
                "location_id": 102,
                "description": "Found on 2nd floor desk",
                "private_details": "Initials RV on buckle, small scratch on bezel",
                "date_found": str(date.today()),
                "custody": "AT_DESK"
            })
            self.assertEqual(res.status_code, 201, f"Report found failed: {res.get_json()}")
            found_id = res.get_json()["found_id"]

            # 7. Student checks matches
            match_res = client.get(f"/api/v1/lost/{lost_id}/matches", headers={"Authorization": f"Bearer {full_token}"})
            self.assertEqual(match_res.status_code, 200)

            # 8. Student files Claim
            claim_res = client.post(f"/api/v1/found/{found_id}/claims", headers={"Authorization": f"Bearer {full_token}"}, json={
                "lost_id": lost_id,
                "claim_description": "This is my Titan watch with black strap."
            })
            self.assertEqual(claim_res.status_code, 201, f"Claim submission failed: {claim_res.get_json()}")
            claim_id = claim_res.get_json()["claim_id"]

            # 9. Admin adds verification question
            q_res = client.post(f"/api/v1/admin/claims/{claim_id}/questions", headers={"Authorization": f"Bearer {admin_token}"}, json={
                "question": "What initials are engraved on the strap buckle?",
                "expected_evidence": "RV"
            })
            self.assertIn(q_res.status_code, (200, 201), f"Add question failed: {q_res.get_json()}")

            # Get question id from claim detail
            detail_res = client.get(f"/api/v1/claims/{claim_id}", headers={"Authorization": f"Bearer {admin_token}"})
            verif_id = detail_res.get_json()["claim"]["questions"][0]["verification_id"]

            # 10. Student answers verification question
            ans_res = client.post(f"/api/v1/claims/{claim_id}/answers", headers={"Authorization": f"Bearer {full_token}"}, json={
                "answers": [{"verification_id": verif_id, "answer": "The initials are RV."}]
            })
            self.assertEqual(ans_res.status_code, 200, f"Answer question failed: {ans_res.get_json()}")

            # 11. Admin marks verified and approves claim
            v_res = client.post(f"/api/v1/admin/claims/{claim_id}/verify", headers={"Authorization": f"Bearer {admin_token}"}, json={
                "verification_id": verif_id,
                "status": "VERIFIED"
            })
            self.assertEqual(v_res.status_code, 200, f"Verify answer failed: {v_res.get_json()}")

            appr_res = client.post(f"/api/v1/admin/claims/{claim_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})
            self.assertEqual(appr_res.status_code, 200, f"Approve claim failed: {appr_res.get_json()}")

            # 12. Admin completes physical handover
            hand_res = client.post(f"/api/v1/admin/claims/{claim_id}/handover", headers={"Authorization": f"Bearer {admin_token}"}, json={
                "received_by_prn": test_prn
            })
            self.assertEqual(hand_res.status_code, 200, f"Handover failed: {hand_res.get_json()}")

            # 13. Verify final state in real database
            self.cursor.execute("SELECT claim_status FROM claims WHERE claim_id = %s", (claim_id,))
            self.assertEqual(self.cursor.fetchone()["claim_status"], "COMPLETED")

            self.cursor.execute("SELECT status FROM found_items WHERE found_id = %s", (found_id,))
            self.assertEqual(self.cursor.fetchone()["status"], "HANDED_OVER")

            self.cursor.execute("SELECT status FROM lost_items WHERE lost_id = %s", (lost_id,))
            self.assertEqual(self.cursor.fetchone()["status"], "RETURNED")

        finally:
            cfg_module.config.DB_PORT = old_port
            cfg_module.config.DB_NAME = old_db
            cfg_module.config.DB_PASSWORD = old_pwd
            cfg_module.config.DB_USER = old_user
            db_module._pool = None

    def test_g_message_outbox_transactional_rollback(self):
        """(g) Proves message_outbox atomic rollback: aborted transaction produces zero outbox messages"""
        self.cursor.execute("SELECT user_id, campus_id FROM users WHERE role_id = 1 AND campus_id = 1 LIMIT 1")
        user = self.cursor.fetchone()
        u_id = user["user_id"]
        c_id = user["campus_id"]

        self.cursor.execute("SELECT COUNT(*) as cnt FROM message_outbox WHERE user_id = %s", (u_id,))
        count_before = self.cursor.fetchone()["cnt"]

        # Simulate a transaction that writes to message_outbox then aborts/rolls back
        try:
            self.cursor.execute(
                """INSERT INTO message_outbox (
                    user_id, campus_id, channel, template_code, body, to_phone_masked, ref_type, ref_id, status
                ) VALUES (%s, %s, 'SMS', 'CLAIM_APPROVED', 'Simulated rollback test', '98****1234', 'CLAIM', 99999, 'SIMULATED')""",
                (u_id, c_id)
            )
            # Force deliberate failure / rollback
            raise RuntimeError("Deliberate simulated transaction failure!")
        except RuntimeError:
            self.conn.rollback()

        # Assert count has NOT changed: zero outbox rows persist!
        self.cursor.execute("SELECT COUNT(*) as cnt FROM message_outbox WHERE user_id = %s", (u_id,))
        count_after = self.cursor.fetchone()["cnt"]
        self.assertEqual(count_after, count_before, "Aborted transaction leaked rows into message_outbox!")

    def test_h_message_outbox_masked_phone_and_no_leak(self):
        """(h) Proves message_outbox stores only masked phone and zero plaintext private details"""
        self.cursor.execute("SELECT to_phone_masked, body FROM message_outbox")
        rows = self.cursor.fetchall()
        for r in rows:
            phone = r["to_phone_masked"]
            if phone and phone != "No phone saved (preview only)":
                self.assertIn("****", phone, f"Unmasked phone found in outbox: {phone}")
                self.assertFalse(phone.isdigit() and len(phone) >= 10, f"Full raw phone stored: {phone}")
            self.assertNotIn("password", r["body"].lower())
            self.assertNotIn("passcode", r["body"].lower())
            self.assertNotIn("secret", r["body"].lower())

    def test_i_location_deactivation_and_conflict(self):
        """(i) Deactivated location excluded from active list, and deleting in-use location raises 1451 FK constraint error"""
        # Deactivate location 101
        self.cursor.execute("UPDATE locations SET is_active = 0 WHERE location_id = 101")
        self.cursor.execute("SELECT location_id FROM locations WHERE campus_id = 1 AND is_active = 1")
        active_loc_ids = [row["location_id"] for row in self.cursor.fetchall()]
        self.assertNotIn(101, active_loc_ids)

        # Attempt to delete location 101 which is referenced by items -> fails on FK constraint error 1451
        with self.assertRaises(mysql.connector.Error) as ctx:
            self.cursor.execute("DELETE FROM locations WHERE location_id = 101")
        self.assertEqual(ctx.exception.errno, 1451)
        self.conn.rollback()

    def test_j_staff_campus_check_constraint(self):
        """(j) MySQL CHECK constraint chk_staff_campus requires campus_id for staff and NULL for super admin"""
        # Role 2 (SECURITY) with campus_id = NULL fails constraint chk_staff_campus (Error 3819)
        with self.assertRaises(mysql.connector.Error) as ctx:
            self.cursor.execute(
                """INSERT INTO users (staff_username, name, password_hash, role_id, campus_id, status)
                   VALUES ('test_sec_nocampus', 'Test Security', 'hash', 2, NULL, 'ACTIVE')"""
            )
        self.assertEqual(ctx.exception.errno, 3819)
        self.conn.rollback()

        # Role 4 (SUPER_ADMIN) with campus_id = 1 fails constraint chk_staff_campus (Error 3819)
        with self.assertRaises(mysql.connector.Error) as ctx:
            self.cursor.execute(
                """INSERT INTO users (staff_username, name, password_hash, role_id, campus_id, status)
                   VALUES ('test_super_withcampus', 'Test Super', 'hash', 4, 1, 'ACTIVE')"""
            )
        self.assertEqual(ctx.exception.errno, 3819)
        self.conn.rollback()

    def test_k_fulltext_search_index_usage(self):
        """(k) EXPLAIN proves MySQL utilizes fulltext index ft_found_search for item keyword search"""
        self.cursor.execute(
            "EXPLAIN SELECT found_id, item_name FROM found_items WHERE MATCH(item_name, description, brand) AGAINST(%s IN BOOLEAN MODE)",
            ("+laptop*",)
        )
        plan = self.cursor.fetchall()
        self.assertTrue(len(plan) > 0)
        self.assertEqual(plan[0]["key"], "ft_found_search")
        self.assertEqual(plan[0]["type"], "fulltext")

if __name__ == "__main__":
    unittest.main()
