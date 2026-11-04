import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.security import create_jwt, hash_password
from backend.tests.mock_db import mock_db


class TestAuth(unittest.TestCase):
    def setUp(self):
        mock_db.reset()
        self.app = create_app()
        self.client = self.app.test_client()

    def test_t01_unknown_prn_login_fails(self):
        """T-01: Login with PRN not in registry -> 401 generic error"""
        with patch("backend.routes.auth.query_one") as mock_query, \
             patch("backend.routes.auth.execute") as mock_exec, \
             patch("backend.routes.auth.check_account_lockout") as mock_lock:
            # PRN not in users or prn_registry
            mock_query.return_value = None
            res = self.client.post("/api/v1/auth/login", json={
                "username": "9999999999",
                "password": "somepassword",
                "portal": "student"
            })
            self.assertEqual(res.status_code, 401)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "INVALID_CREDENTIALS")
            self.assertIn("Invalid PRN or password", data["error"]["message"])

    def test_t02_first_login_with_prn_credential(self):
        """T-02: Valid PRN with PRN as password -> 200, scope=pwd_change, must_change_password=True"""
        with patch("backend.routes.auth.query_one") as mock_query, \
             patch("backend.routes.auth.execute") as mock_exec, \
             patch("backend.routes.auth.check_account_lockout"):
            # Mock student user whose password_hash is NULL
            mock_query.return_value = {
                "user_id": 3,
                "prn": "1251150001",
                "name": "Riya",
                "password_hash": None,
                "must_change_password": 1,
                "role_id": 1,
                "role_name": "STUDENT",
                "campus_id": 1,
                "campus_name": "Kondhwa Campus",
                "campus_code": "KON",
                "status": "ACTIVE",
                "profile_completed": 0
            }
            res = self.client.post("/api/v1/auth/login", json={
                "username": "1251150001",
                "password": "1251150001",
                "portal": "student"
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["scope"], "pwd_change")
            self.assertTrue(data["must_change_password"])
            self.assertIn("token", data)

    def test_t03_scope_enforcement_pwd_change_blocked(self):
        """T-03: Token with scope=pwd_change calling /lost is blocked with 403 PASSWORD_CHANGE_REQUIRED"""
        token = create_jwt(
            user_id=3,
            role="STUDENT",
            campus_id=1,
            scope="pwd_change",
            portal="student",
            must_change_password=True
        )
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "name": "Riya", "email": None, "phone": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 1, "profile_completed": 0
            }
            res = self.client.post(
                "/api/v1/lost",
                headers={"Authorization": f"Bearer {token}"},
                json={"item_name": "Calculator"}
            )
            self.assertEqual(res.status_code, 403)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "PASSWORD_CHANGE_REQUIRED")

    def test_t04_password_validation_rules(self):
        """T-04: New password equals PRN / contains PRN / < 8 chars -> 400 VALIDATION_ERROR"""
        token = create_jwt(
            user_id=3, role="STUDENT", campus_id=1, scope="pwd_change", portal="student"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.auth.query_one") as mock_auth_query:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "name": "Riya", "email": None, "phone": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 1, "profile_completed": 0
            }
            mock_auth_query.return_value = {
                "password_hash": None,
                "prn": "1251150001",
                "staff_username": None
            }

            # Too short (< 8 chars)
            res1 = self.client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": "1251150001", "new_password": "short"}
            )
            self.assertEqual(res1.status_code, 400)
            self.assertEqual(res1.get_json()["error"]["code"], "VALIDATION_ERROR")

            # Equals PRN
            res2 = self.client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": "1251150001", "new_password": "1251150001"}
            )
            self.assertEqual(res2.status_code, 400)
            self.assertIn("cannot be your PRN", res2.get_json()["error"]["message"])

            # Contains PRN
            res3 = self.client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {token}"},
                json={"current_password": "1251150001", "new_password": "pass1251150001word"}
            )
            self.assertEqual(res3.status_code, 400)
            self.assertIn("cannot contain your PRN", res3.get_json()["error"]["message"])

    def test_t05_prn_credential_disabled_after_change(self):
        """T-05: After password is changed, PRN as password no longer works"""
        new_hash = hash_password("MyNewSecurePass2026!")
        with patch("backend.routes.auth.query_one") as mock_query, \
             patch("backend.routes.auth.execute"), \
             patch("backend.routes.auth.check_account_lockout"):
            mock_query.return_value = {
                "user_id": 3,
                "prn": "1251150001",
                "name": "Riya",
                "password_hash": new_hash, # Now set!
                "must_change_password": 0,
                "role_id": 1,
                "role_name": "STUDENT",
                "campus_id": 1,
                "status": "ACTIVE",
                "profile_completed": 1
            }
            # Attempt login with PRN as password
            res = self.client.post("/api/v1/auth/login", json={
                "username": "1251150001",
                "password": "1251150001",
                "portal": "student"
            })
            self.assertEqual(res.status_code, 401)
            self.assertEqual(res.get_json()["error"]["code"], "INVALID_CREDENTIALS")

    def test_t06_account_lockout_after_failed_attempts(self):
        """T-06: 5 failed login attempts -> account locked on next attempt"""
        with patch("backend.routes.auth.query_one") as mock_query:
            # Simulate 5 failed attempts in login_attempts table
            mock_query.return_value = {"failed_count": 5}
            res = self.client.post("/api/v1/auth/login", json={
                "username": "1251150001",
                "password": "wrongpassword",
                "portal": "student"
            })
            self.assertEqual(res.status_code, 423)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "ACCOUNT_LOCKED")

    def test_t07_portal_separation_student_blocked_from_admin(self):
        """T-07: Student token calling /admin endpoint -> 403 Forbidden"""
        token = create_jwt(
            user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            res = self.client.get(
                "/api/v1/admin/dashboard",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.get_json()["error"]["code"], "FORBIDDEN")

if __name__ == "__main__":
    unittest.main()

