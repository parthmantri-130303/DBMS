"""
Regression Test Suite for Independent Code Review & Prompt 5 Hardening Fixes
Covers:
- Finding 1: Cross-campus staff privacy leak blocked (opposite campus staff gets private_details=None, storage_location=None)
- Finding 2: Token required on GET /found/<id>, rejecting anonymous access (401) and pwd_change scope (403)
- Finding 3: Legitimate finder can see own private_details (int comparison fix)
- Finding 4: Staff creation requires strong password, rejects weak/default passwords (400), forces password change on first login
- Finding 5: Staff campus assignment validation (CAMPUS_ADMIN/SECURITY require campus_id; SUPER_ADMIN must be NULL)
- Finding 8: FULLTEXT search with Boolean mode for 3+ chars, safe escaped LIKE for %, _, and short queries
- Finding 9: Non-numeric pagination (?page=abc, ?page_size=-5) returns 400 ValidationError, never 500
"""

import unittest
from unittest.mock import MagicMock, patch
from backend.app import create_app
from backend.security import create_jwt


class TestCodeReviewFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    # -------------------------------------------------------------------------
    # Finding 1 & 2: Cross-campus staff privacy leak & Token requirement
    # -------------------------------------------------------------------------
    def test_finding_1_and_2_cross_campus_staff_privacy_leak_blocked(self):
        """Opposite-campus staff cannot view private_details or storage_location; anonymous access rejected (401)."""
        # 1. Anonymous request rejected
        res_anon = self.client.get("/api/v1/found/37")
        self.assertEqual(res_anon.status_code, 401)

        # 2. Opposite-campus staff: admin_kon (campus 1) requesting Bibwewadi item (campus 2)
        admin_kon_token = create_jwt(user_id=2, role="CAMPUS_ADMIN", campus_id=1, scope="full", portal="admin")
        item_bib = {
            "found_id": 37,
            "user_id": 99,
            "item_name": "Titan Watch",
            "category_id": 7,
            "category_name": "Clothing & Accessories",
            "icon": "watch",
            "campus_id": 2, # Bibwewadi campus
            "campus_name": "Bibwewadi Campus",
            "code": "BIB",
            "location_id": 203,
            "location_name": "AI/DS Lab 301",
            "building": "Building 3",
            "floor": "3rd",
            "brand": "Titan",
            "color": "Black",
            "description": "Found on practical terminal",
            "date_found": "2026-11-01",
            "time_found": "11:00:00",
            "image_url": None,
            "custody": "AT_DESK",
            "status": "CLAIMED",
            "created_at": "2026-11-01 11:30:00",
            "private_details": "Engraved with initials AK on strap buckle",
            "storage_location": "Desk Drawer 2"
        }
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.items.query_one") as mock_item:
            mock_user.return_value = {
                "user_id": 2, "prn": None, "staff_username": "admin_kon",
                "role_id": 3, "role": "CAMPUS_ADMIN", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_item.return_value = dict(item_bib)

            res = self.client.get("/api/v1/found/37", headers={"Authorization": f"Bearer {admin_kon_token}"})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()["item"]

            # Must be redacted for opposite campus staff
            self.assertIsNone(data["private_details"], "Cross-campus staff must not see private_details")
            self.assertIsNone(data["storage_location"], "Cross-campus staff must not see storage_location")
            self.assertIsNone(data["user_id"], "Cross-campus staff must not see finder user_id")

    # -------------------------------------------------------------------------
    # Finding 2: Token with pwd_change scope rejected with 403
    # -------------------------------------------------------------------------
    def test_finding_2_pwd_change_scope_blocked(self):
        """A user with pwd_change scope token cannot access GET /found/<id>."""
        pwd_token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="pwd_change", portal="student")
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 1, "profile_completed": 0
            }
            res = self.client.get("/api/v1/found/37", headers={"Authorization": f"Bearer {pwd_token}"})
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.get_json()["error"]["code"], "PASSWORD_CHANGE_REQUIRED")

    # -------------------------------------------------------------------------
    # Finding 2: Suspended account rejected with 403
    # -------------------------------------------------------------------------
    def test_finding_2_suspended_account_rejected(self):
        """A suspended user account is immediately rejected with 403."""
        token = create_jwt(user_id=5, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 5, "prn": "1251150005", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "SUSPENDED",
                "must_change_password": 0, "profile_completed": 1
            }
            res = self.client.get("/api/v1/found/37", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(res.status_code, 403)
            self.assertIn("suspended", res.get_json()["error"]["message"].lower())

    # -------------------------------------------------------------------------
    # Finding 3: Legitimate finder sees own private_details
    # -------------------------------------------------------------------------
    def test_finding_3_finder_sees_own_private_details(self):
        """Legitimate finder (user 3) can see their own private_details."""
        finder_token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        sample_item = {
            "found_id": 42,
            "user_id": 3, # Matches caller user_id
            "item_name": "Calculator",
            "category_id": 1,
            "category_name": "Electronics",
            "icon": "calculator",
            "campus_id": 1,
            "campus_name": "Kondhwa Campus",
            "code": "KON",
            "location_id": 101,
            "location_name": "Security Desk",
            "building": "Main",
            "floor": "Ground",
            "brand": "Casio",
            "color": "Black",
            "description": "Left on desk",
            "date_found": "2026-11-01",
            "time_found": "10:00:00",
            "image_url": None,
            "custody": "AT_DESK",
            "status": "ACTIVE",
            "created_at": "2026-11-01 10:15:00",
            "private_details": "My custom sticker inside cover",
            "storage_location": "Desk Drawer 1"
        }
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.items.query_one") as mock_item:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_item.return_value = dict(sample_item)

            res = self.client.get("/api/v1/found/42", headers={"Authorization": f"Bearer {finder_token}"})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()["item"]
            self.assertEqual(data["private_details"], "My custom sticker inside cover")
            self.assertIsNone(data["storage_location"], "Finder must NOT see storage_location (staff only)")

    # -------------------------------------------------------------------------
    # Finding 2 Extension: Admin password reset invalidates old full-scope token
    # -------------------------------------------------------------------------
    def test_admin_reset_password_invalidates_old_full_token(self):
        """When an admin resets a password (setting must_change_password=1), old full-scope tokens are rejected with 403."""
        old_full_token = create_jwt(user_id=7, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 7, "prn": "1251150007", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 1, "profile_completed": 1
            }
            res = self.client.get("/api/v1/found/37", headers={"Authorization": f"Bearer {old_full_token}"})
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.get_json()["error"]["code"], "PASSWORD_CHANGE_REQUIRED")

    # -------------------------------------------------------------------------
    # Finding 4 & 5: Staff creation validation & forced password change
    # -------------------------------------------------------------------------
    def test_finding_4_and_5_staff_creation_validation(self):
        """Staff creation rejects missing password, weak/common password, or invalid campus assignment."""
        super_token = create_jwt(user_id=1, role="SUPER_ADMIN", campus_id=None, scope="full", portal="admin")
        super_user = {
            "user_id": 1, "prn": None, "staff_username": "admin",
            "role_id": 4, "role": "SUPER_ADMIN", "campus_id": None, "status": "ACTIVE",
            "must_change_password": 0, "profile_completed": 1
        }

        def mock_admin_qone(sql, *args):
            if "campuses" in sql:
                return {"campus_id": 1}
            if "roles" in sql:
                return {"role_id": 2}
            if "staff_username" in sql:
                return None
            return None

        with patch("backend.security.query_one") as mock_sec, \
             patch("backend.routes.admin.query_one", side_effect=mock_admin_qone):
            mock_sec.return_value = super_user

            # 1. Missing password -> 400
            res = self.client.post("/api/v1/admin/staff", headers={"Authorization": f"Bearer {super_token}"}, json={
                "username": "new_sec",
                "name": "New Security Guard",
                "role": "SECURITY",
                "campus_id": 1
                # password omitted!
            })
            self.assertEqual(res.status_code, 400)

            # 2. Common password 'admin123' -> 400
            res = self.client.post("/api/v1/admin/staff", headers={"Authorization": f"Bearer {super_token}"}, json={
                "username": "new_sec",
                "name": "New Security Guard",
                "role": "SECURITY",
                "campus_id": 1,
                "password": "admin123"
            })
            self.assertEqual(res.status_code, 400)
            self.assertIn("too common", res.get_json()["error"]["message"].lower())

            # 3. Short password (< 8 chars) -> 400
            res = self.client.post("/api/v1/admin/staff", headers={"Authorization": f"Bearer {super_token}"}, json={
                "username": "new_sec",
                "name": "New Security Guard",
                "role": "SECURITY",
                "campus_id": 1,
                "password": "short"
            })
            self.assertEqual(res.status_code, 400)

            # 4. CAMPUS_ADMIN without campus_id -> 400
            res = self.client.post("/api/v1/admin/staff", headers={"Authorization": f"Bearer {super_token}"}, json={
                "username": "new_admin",
                "name": "New Campus Admin",
                "role": "CAMPUS_ADMIN",
                "campus_id": None,
                "password": "StrongStaff#2026!"
            })
            self.assertEqual(res.status_code, 400)

            # 5. SUPER_ADMIN with campus_id -> 400
            res = self.client.post("/api/v1/admin/staff", headers={"Authorization": f"Bearer {super_token}"}, json={
                "username": "new_super",
                "name": "New Super Admin",
                "role": "SUPER_ADMIN",
                "campus_id": 1,
                "password": "StrongStaff#2026!"
            })
            self.assertEqual(res.status_code, 400)

    # -------------------------------------------------------------------------
    # Finding 4: Staff first-login forces password change
    # -------------------------------------------------------------------------
    def test_finding_4_staff_first_login_forces_pwd_change(self):
        """Staff member with must_change_password=1 receives pwd_change scope on login."""
        staff_row = {
            "user_id": 10,
            "prn": None,
            "staff_username": "new_officer",
            "name": "Officer Sharma",
            "password_hash": "$2b$12$LjfH8vwXeTiAWbNie3cxZehvHtQY6Q1jhEBxHs6YznE6mYMGHjAF.", # admin123
            "must_change_password": 1,
            "role_id": 2,
            "role_name": "SECURITY",
            "campus_id": 1,
            "campus_name": "Kondhwa Campus",
            "campus_code": "KON",
            "status": "ACTIVE"
        }
        with patch("backend.routes.auth.check_account_lockout"), \
             patch("backend.routes.auth.query_one") as mock_query, \
             patch("backend.routes.auth.verify_password") as mock_verify, \
             patch("backend.routes.auth.record_login_attempt"):
            mock_query.return_value = staff_row
            mock_verify.return_value = True

            res = self.client.post("/api/v1/auth/login", json={
                "username": "new_officer",
                "password": "InitialStaffPassword#1",
                "portal": "admin"
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["scope"], "pwd_change")
            self.assertTrue(data["must_change_password"])

    # -------------------------------------------------------------------------
    # Finding 9: Pagination input validation
    # -------------------------------------------------------------------------
    def test_finding_9_pagination_validation(self):
        """Non-numeric or negative pagination parameters return HTTP 400, never 500."""
        # Non-numeric page
        res = self.client.get("/api/v1/found/search?page=abc")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["error"]["code"], "VALIDATION_ERROR")

        # Negative page_size
        res = self.client.get("/api/v1/found/search?page_size=-5")
        self.assertEqual(res.status_code, 400)

        # Huge page returns empty list with 200, never 500
        with patch("backend.routes.items.query_one") as mock_count, \
             patch("backend.routes.items.query_all") as mock_items:
            mock_count.return_value = {"total": 5, "available_count": 3, "claimed_count": 2}
            mock_items.return_value = []
            res = self.client.get("/api/v1/found/search?page=999999")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()["items"], [])

    # -------------------------------------------------------------------------
    # Finding 8: Search with % and _ wildcard sanitization
    # -------------------------------------------------------------------------
    def test_finding_8_search_wildcard_sanitization(self):
        """Queries containing % and _ are escaped literally, avoiding wildcard injection."""
        from backend.search import build_search_clause

        # % wildcard escaped
        clause_pct, params_pct = build_search_clause("f", "%")
        self.assertIn("ESCAPE '\\\\'", clause_pct)
        self.assertIn("%\\%%", params_pct)

        # _ wildcard escaped
        clause_und, params_und = build_search_clause("f", "_")
        self.assertIn("ESCAPE '\\\\'", clause_und)
        self.assertIn("%\\_%", params_und)

        # Multi-word query uses FULLTEXT boolean mode
        clause_ft, params_ft = build_search_clause("f", "Casio Calculator")
        self.assertIn("MATCH(f.item_name, f.description, f.brand) AGAINST(%s IN BOOLEAN MODE)", clause_ft)
        self.assertEqual(params_ft, ["+Casio* +Calculator*"])

    # -------------------------------------------------------------------------
    # QR Claim Passport Security & HMAC Verification
    # -------------------------------------------------------------------------
    def test_passport_tamper_proofing_and_forgery_rejection(self):
        """Passport verification requires valid HMAC signature, rejects plain numbers, wrong status, and other campuses."""
        from backend.security import generate_passport_signature
        admin_kon_token = create_jwt(user_id=2, role="CAMPUS_ADMIN", campus_id=1, scope="full", portal="admin")

        approved_claim = {
            "claim_id": 15,
            "found_id": 42,
            "lost_id": 10,
            "claimant_id": 3,
            "campus_id": 1,
            "claim_status": "APPROVED",
            "claim_description": "My watch",
            "found_item_name": "Titan Watch",
            "found_image_url": None,
            "found_description": "Watch found",
            "private_details": "Initials AK",
            "claimant_prn": "1251150001",
            "claimant_name": "Riya Sharma",
            "claimant_phone": "9822114455",
            "campus_name": "Kondhwa Campus"
        }

        valid_sig = generate_passport_signature(15, "1251150001", 42)

        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.admin.query_one") as mock_claim:
            mock_user.return_value = {
                "user_id": 2, "prn": None, "staff_username": "admin_kon",
                "role_id": 3, "role": "CAMPUS_ADMIN", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_claim.return_value = dict(approved_claim)

            # 1. Valid signed QR payload -> 200
            res = self.client.post("/api/v1/admin/claims/verify-passport",
                headers={"Authorization": f"Bearer {admin_kon_token}"},
                json={"code": f"CK-VERIFY:15:1251150001:{valid_sig}"}
            )
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json()["verified"])

            # 2. Forged signature -> 400 VALIDATION_ERROR
            res_forged = self.client.post("/api/v1/admin/claims/verify-passport",
                headers={"Authorization": f"Bearer {admin_kon_token}"},
                json={"code": "CK-VERIFY:15:1251150001:BADSIGNATURE1234"}
            )
            self.assertEqual(res_forged.status_code, 400)
            self.assertIn("forged", res_forged.get_json()["error"]["message"].lower())

            # 3. Plain numeric input -> 400 VALIDATION_ERROR
            res_num = self.client.post("/api/v1/admin/claims/verify-passport",
                headers={"Authorization": f"Bearer {admin_kon_token}"},
                json={"code": "15"}
            )
            self.assertEqual(res_num.status_code, 400)
            self.assertIn("plain numbers are rejected", res_num.get_json()["error"]["message"].lower())

            # 4. Wrong claim status (PENDING instead of APPROVED) -> 409 CONFLICT
            pending_claim = dict(approved_claim)
            pending_claim["claim_status"] = "PENDING"
            mock_claim.return_value = pending_claim
            res_pending = self.client.post("/api/v1/admin/claims/verify-passport",
                headers={"Authorization": f"Bearer {admin_kon_token}"},
                json={"code": f"CK-VERIFY:15:1251150001:{valid_sig}"}
            )
            self.assertEqual(res_pending.status_code, 409)
            self.assertIn("approved", res_pending.get_json()["error"]["message"].lower())

            # 5. Wrong campus desk staff (Bibwewadi staff attempting Kondhwa claim) -> 403 FORBIDDEN
            mock_claim.return_value = dict(approved_claim)
            mock_user.return_value = {
                "user_id": 4, "prn": None, "staff_username": "admin_bib",
                "role_id": 3, "role": "CAMPUS_ADMIN", "campus_id": 2, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            admin_bib_token = create_jwt(user_id=4, role="CAMPUS_ADMIN", campus_id=2, scope="full", portal="admin")
            res_wrong_campus = self.client.post("/api/v1/admin/claims/verify-passport",
                headers={"Authorization": f"Bearer {admin_bib_token}"},
                json={"code": f"CK-VERIFY:15:1251150001:{valid_sig}"}
            )
            self.assertEqual(res_wrong_campus.status_code, 403)

    def test_get_claim_passport_requires_approved_status(self):
        """Student cannot generate a pickup passport for an unapproved (PENDING) claim."""
        student_token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        pending_claim = {
            "claim_id": 15, "found_id": 42, "claimant_id": 3, "campus_id": 1,
            "claim_status": "PENDING", "claimant_prn": "1251150001", "claimant_name": "Riya"
        }
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.claims.query_one") as mock_claim:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "role_id": 1, "role": "STUDENT",
                "campus_id": 1, "status": "ACTIVE", "must_change_password": 0, "profile_completed": 1
            }
            mock_claim.return_value = pending_claim
            res = self.client.get("/api/v1/claims/15/passport", headers={"Authorization": f"Bearer {student_token}"})
            self.assertEqual(res.status_code, 409)
            self.assertIn("approved", res.get_json()["error"]["message"].lower())


if __name__ == "__main__":
    unittest.main()
