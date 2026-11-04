import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.matcher import calculate_match_score
from backend.security import create_jwt


class TestCampusRules(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_t08_cross_campus_location_rejected(self):
        """T-08: Kondhwa student (campus 1) reporting item with Bibwewadi location (campus 2) -> 403 WRONG_CAMPUS"""
        token = create_jwt(
            user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.items.query_one") as mock_loc:
            # Current user is Kondhwa student
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Location 201 belongs to Bibwewadi (campus 2)
            mock_loc.return_value = {
                "location_id": 201,
                "campus_id": 2,
                "location_name": "Bibwewadi Security Desk"
            }

            res = self.client.post(
                "/api/v1/lost",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "item_name": "Casio fx-991CW",
                    "category_id": 1,
                    "location_id": 201, # Wrong campus location!
                    "description": "Black scientific calculator left in lab",
                    "date_lost": "2026-11-01"
                }
            )
            self.assertEqual(res.status_code, 403)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "WRONG_CAMPUS")

    def test_t09_cross_campus_claim_rejected(self):
        """T-09: Kondhwa student (campus 1) claiming Bibwewadi item (campus 2) -> 403 WRONG_CAMPUS"""
        token = create_jwt(
            user_id=3, role="STUDENT", campus_id=1, scope="full", portal="student"
        )
        with patch("backend.security.query_one") as mock_user, \
             patch("backend.routes.claims.query_one") as mock_found:
            mock_user.return_value = {
                "user_id": 3, "prn": "1251150001", "staff_username": None,
                "role_id": 1, "campus_id": 1, "status": "ACTIVE",
                "must_change_password": 0, "profile_completed": 1
            }
            # Found item physically located at Bibwewadi (campus 2)
            mock_found.return_value = {
                "found_id": 50,
                "campus_id": 2,
                "user_id": 4, # Finder
                "status": "ACTIVE"
            }

            res = self.client.post(
                "/api/v1/found/50/claims",
                headers={"Authorization": f"Bearer {token}"},
                json={"claim_description": "I lost my calculator there"}
            )
            self.assertEqual(res.status_code, 403)
            data = res.get_json()
            self.assertEqual(data["error"]["code"], "WRONG_CAMPUS")

    def test_t10_matcher_strictly_isolates_campuses(self):
        """T-10: Matcher calculates 0 score if items belong to different campuses"""
        lost_item = {
            "lost_id": 10,
            "campus_id": 1, # Kondhwa
            "category_id": 1,
            "item_name": "Casio fx-991EX Calculator",
            "color": "Black",
            "date_lost": "2026-11-01",
            "location_id": 101
        }
        found_item = {
            "found_id": 20,
            "campus_id": 2, # Bibwewadi
            "category_id": 1,
            "item_name": "Casio fx-991EX Calculator",
            "color": "Black",
            "date_found": "2026-11-01",
            "location_id": 201
        }

        # Even with 100% identical name, color, and date, cross-campus score MUST be 0!
        result = calculate_match_score(lost_item, found_item)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["breakdown"], {})

    def test_t11_cross_campus_browsing_allowed(self):
        """T-11: A student can browse public listings of the other campus"""
        with patch("backend.routes.reference.query_one") as mock_cp, \
             patch("backend.routes.reference.query_all") as mock_items:
            # 1st call for campus existence, 2nd call for total count
            mock_cp.side_effect = [{"campus_id": 2}, {"total": 1}]
            mock_items.return_value = [
                {
                    "found_id": 1,
                    "item_name": "Blue Umbrella",
                    "category_name": "Clothing & Accessories",
                    "campus_name": "Bibwewadi Campus",
                    "location_name": "Bibwewadi Security Desk",
                    "date_found": "2026-11-01",
                    "status": "ACTIVE"
                }
            ]

            res = self.client.get("/api/v1/campuses/2/found")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(len(data["items"]), 1)
            self.assertEqual(data["items"][0]["item_name"], "Blue Umbrella")

if __name__ == "__main__":
    unittest.main()
