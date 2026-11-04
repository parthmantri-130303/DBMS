import datetime
import io
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.security import create_jwt


class TestItemsAndPrivacy(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_t12_report_validation_future_date_rejected(self):
        """T-12: Future date in lost complaint -> 400 VALIDATION_ERROR"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        future_date = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()

        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            res = self.client.post(
                "/api/v1/lost",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "item_name": "Calculator",
                    "category_id": 1,
                    "location_id": 101,
                    "description": "Lost yesterday",
                    "date_lost": future_date
                }
            )
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
            self.assertIn("cannot be in the future", data["error"]["message"])

    def test_t13_upload_validation_rejected(self):
        """T-13: Invalid file upload (.exe or bad format) -> 415 UNSUPPORTED_MEDIA"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Upload a disguised executable
            fake_exe = (io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00This is an executable"), "malware.exe")
            res = self.client.post(
                "/api/v1/lost",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "item_name": "Watch",
                    "category_id": 1,
                    "location_id": 101,
                    "description": "Silver analog watch",
                    "date_lost": "2026-11-01",
                    "image": fake_exe
                },
                content_type="multipart/form-data"
            )
            self.assertEqual(res.status_code, 415)
            self.assertEqual(res.get_json()["error"]["code"], "UNSUPPORTED_MEDIA")

    def test_t14_privacy_leak_prevention(self):
        """T-14: Public GET /found/<id> NEVER exposes private_details or storage_location to general public"""
        sample_item = {
            "found_id": 42,
            "user_id": 99, # Finder user ID
            "item_name": "Brown Leather Wallet",
            "category_id": 3,
            "category_name": "Wallets & Purses",
            "icon": "wallet",
            "campus_id": 1,
            "campus_name": "Kondhwa Campus",
            "code": "KON",
            "location_id": 101,
            "location_name": "Kondhwa Security Desk",
            "building": "Main Building",
            "floor": "Ground",
            "brand": "Wildhorn",
            "color": "Brown",
            "description": "Found on cafeteria bench near entrance",
            "date_found": "2026-11-01",
            "time_found": "14:30:00",
            "image_url": "/media/2026/11/abc.webp",
            "custody": "AT_DESK",
            "status": "ACTIVE",
            "created_at": "2026-11-01 14:35:00",
            # SENSITIVE FIELDS:
            "private_details": "Contains Rs 500 note and SBI debit card ending in 4123",
            "storage_location": "Security Locker Box #4"
        }
        with patch("backend.security.query_one") as mock_sec, \
             patch("backend.routes.items.query_one") as mock_found:
            mock_found.side_effect = lambda sql, *args: dict(sample_item)

            # 1. Unauthenticated public request -> 401 (Finding 2 auth enforcement)
            res_anon = self.client.get("/api/v1/found/42")
            self.assertEqual(res_anon.status_code, 401)

            # 2. Authenticated third-party student request (user 88, finder is 99) -> 200 with sensitive fields redacted (Finding 1 & 2)
            other_student_token = create_jwt(user_id=88, role="STUDENT", campus_id=1, scope="full", portal="student")
            mock_sec.return_value = {
                "user_id": 88, "prn": "1251150088", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            res = self.client.get("/api/v1/found/42", headers={"Authorization": f"Bearer {other_student_token}"})
            self.assertEqual(res.status_code, 200)
            item = res.get_json()["item"]

            # Must be redacted / None for third-party student
            self.assertIsNone(item["private_details"])
            self.assertIsNone(item["storage_location"])
            self.assertIsNone(item["user_id"])
            self.assertEqual(item["item_name"], "Brown Leather Wallet")

            # 3. Authenticated finder request (user 99) -> 200 with own private_details visible (Finding 3)
            finder_token = create_jwt(user_id=99, role="STUDENT", campus_id=1, scope="full", portal="student")
            mock_sec.return_value = {
                "user_id": 99, "prn": "1251150099", "staff_username": None,
                "role_id": 1, "role": "STUDENT", "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            res_finder = self.client.get("/api/v1/found/42", headers={"Authorization": f"Bearer {finder_token}"})
            self.assertEqual(res_finder.status_code, 200)
            finder_item = res_finder.get_json()["item"]
            self.assertEqual(finder_item["private_details"], "Contains Rs 500 note and SBI debit card ending in 4123")
            self.assertIsNone(finder_item["storage_location"], "Finder must NOT see storage_location (staff only)")

    def test_t15_duplicate_active_claim_rejected(self):
        """T-15: A student submitting a second claim on an item while first is PENDING -> 409 CONFLICT"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.claims.query_one") as mock_query:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # 1st call: found item; 2nd call: existing active claim
            mock_query.side_effect = [
                {"found_id": 10, "campus_id": 1, "status": "ACTIVE", "user_id": 99},
                {"claim_id": 5} # Active claim already exists!
            ]

            res = self.client.post(
                "/api/v1/found/10/claims",
                headers={"Authorization": f"Bearer {token}"},
                json={"claim_description": "Second claim attempt"}
            )
            self.assertEqual(res.status_code, 409)
            self.assertEqual(res.get_json()["error"]["code"], "CONFLICT")
            self.assertIn("already have an active claim", res.get_json()["error"]["message"])

    def test_t16_claim_own_found_report_rejected(self):
        """T-16: Student cannot file claim on an item they reported as found -> 409 CONFLICT"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.claims.query_one") as mock_query:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Found item user_id equals current user_id (3)
            mock_query.return_value = {
                "found_id": 10,
                "campus_id": 1,
                "status": "ACTIVE",
                "user_id": 3 # Current user is the finder!
            }

            res = self.client.post(
                "/api/v1/found/10/claims",
                headers={"Authorization": f"Bearer {token}"},
                json={"claim_description": "Trying to claim my own report"}
            )
            self.assertEqual(res.status_code, 409)
            self.assertIn("cannot claim an item you reported", res.get_json()["error"]["message"])

    def test_t17_student_cannot_see_expected_evidence(self):
        """T-17: When student fetches claim detail, expected_evidence is strictly omitted"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.claims.query_one") as mock_claim, \
             patch("backend.routes.claims.query_all") as mock_q:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            mock_claim.return_value = {
                "claim_id": 1, "found_id": 10, "claimant_id": 3,
                "claim_status": "UNDER_REVIEW", "claim_description": "My earphones"
            }
            # Verification questions for student
            mock_q.return_value = [
                {
                    "verification_id": 1,
                    "question": "What colour was the carrying case zipper?",
                    "answer": None,
                    "verification_status": "ASKED"
                    # expected_evidence is NOT present in student query projection
                }
            ]

            res = self.client.get(
                "/api/v1/claims/1",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(res.status_code, 200)
            claim = res.get_json()["claim"]
            self.assertEqual(len(claim["questions"]), 1)
            self.assertNotIn("expected_evidence", claim["questions"][0])

    def test_t26_found_recent_feed(self):
        """T-26: GET /found/recent returns recent items with availability badge"""
        with patch("backend.routes.items.query_all") as mock_items:
            mock_items.return_value = [
                {
                    "found_id": 101,
                    "item_name": "Scientific Calculator",
                    "category_name": "Electronics",
                    "status": "ACTIVE",
                    "availability_badge": "Available"
                },
                {
                    "found_id": 102,
                    "item_name": "Blue Fastrack Backpack",
                    "category_name": "Bags & Backpacks",
                    "status": "CLAIMED",
                    "availability_badge": "Claimed"
                }
            ]
            res = self.client.get("/api/v1/found/recent")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("items", data)
            self.assertEqual(len(data["items"]), 2)
            self.assertEqual(data["items"][0]["availability_badge"], "Available")
            self.assertEqual(data["items"][1]["availability_badge"], "Claimed")

    def test_t27_found_historical_search_includes_claimed_items(self):
        """T-27: GET /found/search returns ALL items by default including claimed items"""
        with patch("backend.routes.items.query_one") as mock_count, \
             patch("backend.routes.items.query_all") as mock_data:
            mock_count.return_value = {
                "total": 2,
                "available_count": 1,
                "claimed_count": 1
            }
            mock_data.return_value = [
                {
                    "found_id": 201,
                    "item_name": "Sony Headphones",
                    "status": "ACTIVE",
                    "availability_badge": "Available"
                },
                {
                    "found_id": 202,
                    "item_name": "Titan Watch",
                    "status": "CLAIMED",
                    "availability_badge": "Claimed"
                }
            ]
            res = self.client.get("/api/v1/found/search?q=Titan")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["total"], 2)
            self.assertEqual(data["available_count"], 1)
            self.assertEqual(data["claimed_count"], 1)
            self.assertEqual(len(data["items"]), 2)

    def test_t28_double_verification_request_flow(self):
        """T-28: POST /found/<id>/double-verify creates dispute event and alerts security"""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.items.query_one") as mock_item, \
             patch("backend.routes.items.get_db") as mock_db:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "name": "Student",
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1, "phone": "9876543210"
            }
            mock_item.side_effect = [
                {
                    "found_id": 55, "item_name": "Gold Ring", "campus_id": 1,
                    "status": "CLAIMED", "category_name": "Clothing & Accessories", "location_name": "Library"
                },
                None # No previous dispute exists
            ]
            # Mock DB connection
            mock_conn = mock_db.return_value.__enter__.return_value
            mock_cursor = mock_conn.cursor.return_value
            mock_cursor.lastrowid = 77
            mock_cursor.fetchall.return_value = [{"user_id": 1}]

            res = self.client.post(
                "/api/v1/found/55/double-verify",
                headers={"Authorization": f"Bearer {token}"},
                json={"dispute_reason": "This is definitely my engraved ring with initial PK."}
            )
            self.assertEqual(res.status_code, 201)
            data = res.get_json()
            self.assertIn("Double verification inquiry registered", data["message"])
            self.assertEqual(data["dispute_id"], 77)

    def test_t29_test_sms_endpoint_removed(self):
        """T-29: POST /me/notifications/test-sms was removed (404) in favor of database-backed message_outbox."""
        token = create_jwt(user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student")
        res = self.client.post(
            "/api/v1/me/notifications/test-sms",
            headers={"Authorization": f"Bearer {token}"},
            json={"event_type": "CLAIM_APPROVED"}
        )
        self.assertEqual(res.status_code, 404)

if __name__ == "__main__":
    unittest.main()

