import unittest
from unittest.mock import MagicMock, patch

from backend.app import create_app
from backend.security import create_jwt


class TestWorkflowAndRollback(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_t18_approval_transaction_rollback_on_failure(self):
        """T-18: Forced exception during claim approval triggers full rollback"""
        admin_token = create_jwt(
            user_id=1, role="SUPER_ADMIN", campus_id=None, scope="full", portal="admin"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.admin.query_one") as mock_claim, \
             patch("backend.routes.admin.get_db") as mock_get_db:

            mock_user.return_value = {
                "user_id": 1, "prn": None, "staff_username": "admin",
                "role_id": 4, "campus_id": None, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_claim.return_value = {
                "claim_id": 10,
                "found_id": 20,
                "lost_id": None,
                "claimant_id": 3,
                "campus_id": 1,
                "claim_status": "UNDER_REVIEW"
            }

            # Create mock connection and cursor where an update raises an exception
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            # First execute succeeds, but next execute raises DB error
            mock_cursor.execute.side_effect = [None, RuntimeError("DB Disk Full / Constraint Failure")]
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            res = self.client.post(
                "/api/v1/admin/claims/10/approve",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            # Transaction must call rollback!
            mock_conn.rollback.assert_called_once()
            # Must not commit!
            mock_conn.commit.assert_not_called()
            self.assertEqual(res.status_code, 500)

    def test_t19_handover_before_approval_rejected(self):
        """T-19: Recording handover on a claim that is still PENDING -> 409 CONFLICT"""
        admin_token = create_jwt(
            user_id=2, role="SECURITY", campus_id=1, scope="full", portal="admin"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.admin.query_one") as mock_claim:
            mock_user.return_value = {
                "user_id": 2, "prn": None, "staff_username": "security_kon",
                "role_id": 2, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Claim is still PENDING (not yet APPROVED)
            mock_claim.return_value = {
                "claim_id": 5,
                "campus_id": 1,
                "claim_status": "PENDING"
            }

            res = self.client.post(
                "/api/v1/admin/claims/5/handover",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"received_by_prn": "1251150001"}
            )
            self.assertEqual(res.status_code, 409)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "CONFLICT")
            self.assertIn("requires claim in APPROVED status", data["error"]["message"])

    def test_t20_timeline_visibility_public_vs_private(self):
        """T-20: Non-owner sees only is_public=1 events; owner/staff see all events"""
        # 1. Non-owner authenticated student
        other_token = create_jwt(
            user_id=10, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.timeline.query_one") as mock_row, \
             patch("backend.routes.timeline.query_all") as mock_events:
            mock_user.return_value = {
                "user_id": 10, "prn": "1251150010", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_row.return_value = {"user_id": 99, "campus_id": 1} # Owner is user 99
            mock_events.return_value = [
                {"event_id": 1, "title": "Lost Report Filed", "is_public": 1}
            ]

            res_public = self.client.get(
                "/api/v1/items/lost/1/timeline",
                headers={"Authorization": f"Bearer {other_token}"}
            )
            self.assertEqual(res_public.status_code, 200)
            events_pub = res_public.get_json()["events"]
            self.assertEqual(len(events_pub), 1)
            self.assertEqual(events_pub[0]["is_public"], 1)

        # 2. Owner authenticated
        owner_token = create_jwt(
            user_id=99, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.timeline.query_one") as mock_row, \
             patch("backend.routes.timeline.query_all") as mock_events:
            mock_user.return_value = {
                "user_id": 99, "prn": "1251150099", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_row.return_value = {"user_id": 99, "campus_id": 1} # Caller IS owner!
            mock_events.return_value = [
                {"event_id": 1, "title": "Lost Report Filed", "is_public": 1},
                {"event_id": 2, "title": "Potential Match Found", "is_public": 0} # Private event
            ]

            res_owner = self.client.get(
                "/api/v1/items/lost/1/timeline",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            self.assertEqual(res_owner.status_code, 200)
            events_owner = res_owner.get_json()["events"]
            self.assertEqual(len(events_owner), 2)

    def test_t21_handover_success_flow(self):
        """T-21: Successful handover updates claim to COMPLETED and records audit log"""
        admin_token = create_jwt(
            user_id=2, role="SECURITY", campus_id=1, scope="full", portal="admin"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.admin.query_one") as mock_claim, \
             patch("backend.routes.admin.get_db") as mock_get_db:

            mock_user.return_value = {
                "user_id": 2, "prn": None, "staff_username": "security_kon",
                "role_id": 2, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_claim.return_value = {
                "claim_id": 15,
                "found_id": 25,
                "lost_id": 35,
                "claimant_id": 3,
                "campus_id": 1,
                "claim_status": "APPROVED" # Ready for handover
            }

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            res = self.client.post(
                "/api/v1/admin/claims/15/handover",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"received_by_prn": "1251150001"}
            )
            self.assertEqual(res.status_code, 200)
            mock_conn.commit.assert_called_once()
            self.assertEqual(res.get_json()["message"], "Handover recorded successfully")

    def test_t22_profile_email_prn_mismatch_rejected(self):
        """T-22: Profile update with email digits mismatching PRN -> 400 VALIDATION_ERROR"""
        student_token = create_jwt(
            user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 0
            }

            # Email has digits 1251030999 which do NOT match PRN 1251150001
            res = self.client.put(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {student_token}"},
                json={
                    "name": "Riya Sharma",
                    "phone": "9876543210",
                    "email": "riya.1251030999@vit.edu"
                }
            )
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
            self.assertIn("do not match your PRN", data["error"]["message"])

    def test_t23_rate_limiting_enforcement(self):
        """T-23: Sliding window rate limiter rejects excessive requests with 429 RATE_LIMITED"""
        # Enable rate limiting checks by temporarily disabling testing flag
        self.app.testing = False
        from backend.app import _rate_limits
        _rate_limits.clear()

        with patch("backend.routes.auth.query_one") as mock_auth_q, \
             patch("backend.routes.auth.execute"):
            mock_auth_q.return_value = None
            # Simulate 20 login requests from same IP (limit is 20)
            for i in range(20):
                res = self.client.post("/api/v1/auth/login", json={"username": "1024010001", "password": "bad"})
            
            # 21st request should be blocked by rate limiter with 429
            res = self.client.post("/api/v1/auth/login", json={"username": "1024010001", "password": "bad"})
            self.assertEqual(res.status_code, 429)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "RATE_LIMITED")

        _rate_limits.clear()
        self.app.testing = True

    def test_t24_idor_prevention_on_patch_report(self):
        """T-24: Student cannot edit another student's report (IDOR protection)"""
        student1_token = create_jwt(user_id=101, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.items.query_one") as mock_item:

            mock_user.return_value = {
                "user_id": 101, "prn": "1024010101", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Report belongs to user_id 999 (not 101)
            mock_item.return_value = {
                "lost_id": 55,
                "user_id": 999,
                "campus_id": 1,
                "status": "ACTIVE",
                "item_name": "Calculator",
                "description": "Casio fx-991",
                "brand": "Casio",
                "color": "Black"
            }

            res = self.client.patch(
                "/api/v1/lost/55",
                headers={"Authorization": f"Bearer {student1_token}"},
                json={"item_name": "Hacked Title"}
            )
            self.assertEqual(res.status_code, 403)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "FORBIDDEN")
            self.assertIn("only edit your own reports", data["error"]["message"])

    def test_t25_batch_prn_import_endpoint(self):
        """T-25: Batch PRN registry import validates 10 digits and registers students"""
        admin_token = create_jwt(user_id=1, role="SUPER_ADMIN", campus_id=None, scope="full", portal="admin")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.admin.query_one") as mock_qone, \
             patch("backend.routes.admin.get_db") as mock_get_db, \
             patch("backend.routes.admin.execute"):

            mock_user.return_value = {
                "user_id": 1, "prn": None, "staff_username": "admin",
                "role_id": 4, "role": "SUPER_ADMIN", "campus_id": None, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # PRN not yet existing in registry
            mock_qone.return_value = None

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_get_db.return_value.__enter__.return_value = mock_conn

            res = self.client.post(
                "/api/v1/admin/prn-registry/import",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "campus_id": 1,
                    "prns": ["1024010991", "1024010992", "invalid_prn", "1024010991"]
                }
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["inserted"], 2)
            self.assertEqual(data["invalid"], 1)
            self.assertEqual(data["skipped"], 1)

if __name__ == "__main__":
    unittest.main()
