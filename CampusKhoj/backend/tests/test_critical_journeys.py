import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app
from backend.security import create_jwt


class TestCriticalJourneys(unittest.TestCase):
    """
    Automated verification of the 6 core end-to-end user journeys
    spanning students, security desk staff, and administrative operations.
    """
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_journey_1_first_login_password_change_profile_setup(self):
        """Journey 1: Student first login with PRN -> Forced password change -> Profile setup"""
        with patch("backend.routes.auth.query_one") as mock_auth_q, \
             patch("backend.routes.auth.execute"), \
             patch("backend.routes.auth.check_account_lockout"), \
             patch("backend.security.query_one") as mock_sec_q, \
             patch("backend.routes.profile.query_one") as mock_prof_q, \
             patch("backend.routes.profile.execute"):

            # Step 1: Login with initial PRN credential (password_hash is NULL in DB)
            mock_auth_q.return_value = {
                "user_id": 42,
                "prn": "1251150269",
                "staff_username": None,
                "name": None,
                "role_id": 1,
                "role_name": "STUDENT",
                "campus_id": 1,
                "campus_name": "Kondhwa Campus",
                "campus_code": "KON",
                "status": "ACTIVE",
                "password_hash": None,
                "must_change_password": 1,
                "profile_completed": 0
            }
            res_login = self.client.post("/api/v1/auth/login", json={
                "username": "1251150269",
                "password": "1251150269",
                "portal": "student"
            })
            self.assertEqual(res_login.status_code, 200)
            login_data = res_login.get_json()
            self.assertEqual(login_data["scope"], "pwd_change")
            self.assertTrue(login_data["must_change_password"])
            pwd_token = login_data["token"]

            mock_sec_q.return_value = {
                "user_id": 42, "prn": "1251150269", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "password_hash": None, "must_change_password": 1, "profile_completed": 0
            }

            # Step 2: Attempting to call full-scope protected endpoint (/lost) with pwd_change token is BLOCKED
            res_blocked = self.client.post("/api/v1/lost", headers={"Authorization": f"Bearer {pwd_token}"}, json={})
            self.assertEqual(res_blocked.status_code, 403)
            self.assertEqual(res_blocked.get_json()["error"]["code"], "PASSWORD_CHANGE_REQUIRED")

            # Step 3: Change Password with valid credentials
            res_change = self.client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {pwd_token}"}, json={
                "current_password": "1251150269",
                "new_password": "StrongStudent@2026"
            })
            self.assertEqual(res_change.status_code, 200)
            full_token = res_change.get_json()["token"]

            # Step 4: Complete Profile Setup
            mock_sec_q.return_value = {
                "user_id": 42, "prn": "1251150269", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 0
            }
            mock_prof_q.return_value = None  # No conflicting phone/email
            res_prof = self.client.put("/api/v1/me/profile", headers={"Authorization": f"Bearer {full_token}"}, json={
                "name": "Rohit Verma",
                "phone": "9822114455",
                "email": "rohit.1251150269@vit.edu"
            })
            self.assertEqual(res_prof.status_code, 200)
            self.assertTrue(res_prof.get_json()["user"]["profile_completed"])

    def test_journey_2_and_3_report_lost_and_found_trigger_matcher(self):
        """Journey 2 & 3: Report lost item, report found item, verify match generation"""
        student_token = create_jwt(user_id=10, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_sec_q, \
             patch("backend.routes.items.query_one") as mock_loc_q, \
             patch("backend.routes.items.get_db") as mock_get_db, \
             patch("backend.routes.items.run_matcher_for_lost_item") as mock_match_lost, \
             patch("backend.routes.items.run_matcher_for_found_item") as mock_match_found:

            mock_sec_q.return_value = {
                "user_id": 10, "prn": "1251150353", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_loc_q.return_value = {"location_id": 1, "campus_id": 1}

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 101
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            # Report Lost Item
            res_lost = self.client.post("/api/v1/lost", headers={"Authorization": f"Bearer {student_token}"}, json={
                "item_name": "HP Pavilion Laptop",
                "category_id": 1,
                "location_id": 1,
                "description": "Silver laptop left in Computer Lab",
                "date_lost": "2026-10-30"
            })
            self.assertEqual(res_lost.status_code, 201)
            mock_match_lost.assert_called_once_with(101)

            # Report Found Item
            mock_cursor.lastrowid = 202
            res_found = self.client.post("/api/v1/found", headers={"Authorization": f"Bearer {student_token}"}, json={
                "item_name": "HP Silver Laptop",
                "category_id": 1,
                "location_id": 1,
                "description": "Found on lab table 4",
                "private_details": "Serial ending 8812, Intel sticker",
                "date_found": "2026-10-30",
                "custody": "AT_DESK"
            })
            self.assertEqual(res_found.status_code, 201)
            mock_match_found.assert_called_once_with(202)

    def test_journey_4_claim_submission_and_question_answers(self):
        """Journey 4: Student files claim, staff issues verification questions, student answers"""
        student_token = create_jwt(user_id=15, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_sec_q, \
             patch("backend.routes.claims.query_one") as mock_claims_q, \
             patch("backend.routes.claims.get_db") as mock_get_db, \
             patch("backend.routes.claims.execute"):

            mock_sec_q.return_value = {
                "user_id": 15, "prn": "1251150353", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 30
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            # 1. Found item exists in same campus and active
            mock_claims_q.side_effect = [
                {"found_id": 202, "campus_id": 1, "status": "ACTIVE", "user_id": 99}, # Found item check
                None, # Existing claim check (None = no duplicate)
                {"claim_id": 30, "claimant_id": 15, "campus_id": 1, "claim_status": "UNDER_REVIEW"} # For submit answers
            ]

            # Submit Claim on found item 202
            res_claim = self.client.post("/api/v1/found/202/claims", headers={"Authorization": f"Bearer {student_token}"}, json={
                "claim_description": "I forgot this laptop during practicals. It belongs to me."
            })
            self.assertEqual(res_claim.status_code, 201)

            # Answer verification question
            res_answer = self.client.post("/api/v1/claims/30/answers", headers={"Authorization": f"Bearer {student_token}"}, json={
                "answers": [{"verification_id": 5, "answer": "Serial number is HP-8812 and wallpaper is an astronaut."}]
            })
            self.assertEqual(res_answer.status_code, 200)

    def test_journey_5_and_6_claim_approval_and_physical_handover(self):
        """Journey 5 & 6: Staff reviews/approves claim and records physical handover at desk"""
        admin_token = create_jwt(user_id=2, role="CAMPUS_ADMIN", campus_id=1, scope="full", portal="admin")
        with patch("backend.security.query_one") as mock_sec_q, \
             patch("backend.routes.admin.query_one") as mock_admin_q, \
             patch("backend.routes.admin.get_db") as mock_get_db:

            mock_sec_q.return_value = {
                "user_id": 2, "prn": None, "staff_username": "admin_kon",
                "role_id": 3, "role": "CAMPUS_ADMIN", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            # Approve Claim
            mock_admin_q.return_value = {
                "claim_id": 30, "found_id": 202, "lost_id": 101, "claimant_id": 15,
                "campus_id": 1, "claim_status": "UNDER_REVIEW"
            }
            res_approve = self.client.post("/api/v1/admin/claims/30/approve", headers={"Authorization": f"Bearer {admin_token}"})
            self.assertEqual(res_approve.status_code, 200)
            mock_conn.commit.assert_called()

            # Record Handover (requires claim in APPROVED status)
            mock_admin_q.return_value = {
                "claim_id": 30, "found_id": 202, "lost_id": 101, "claimant_id": 15,
                "campus_id": 1, "claim_status": "APPROVED"
            }
            res_handover = self.client.post("/api/v1/admin/claims/30/handover", headers={"Authorization": f"Bearer {admin_token}"}, json={
                "received_by_prn": "1024010015"
            })
            self.assertEqual(res_handover.status_code, 200)
            self.assertIn("Handover recorded successfully", res_handover.get_json()["message"])

    def test_journey_7_cross_campus_violation_rejection(self):
        """Journey 7: Cross-campus isolation strictly rejects unauthorized reports/claims"""
        kondhwa_token = create_jwt(user_id=88, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_sec_q, \
             patch("backend.routes.items.query_one") as mock_loc_q:

            mock_sec_q.return_value = {
                "user_id": 88, "prn": "1251150418", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Location belongs to Bibwewadi (campus 2)
            mock_loc_q.return_value = {"location_id": 12, "campus_id": 2}

            # Attempt to report lost item with Bibwewadi location
            res = self.client.post("/api/v1/lost", headers={"Authorization": f"Bearer {kondhwa_token}"}, json={
                "item_name": "Intruder Item",
                "category_id": 1,
                "location_id": 12,
                "description": "Cross campus breach",
                "date_lost": "2026-10-30"
            })
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.get_json()["error"]["code"], "WRONG_CAMPUS")

if __name__ == "__main__":
    unittest.main()
