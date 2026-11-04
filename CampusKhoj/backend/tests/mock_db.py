"""
In-memory mock database driver for hermetic unit & API testing.
Enforces the same constraints as MySQL 8:
- Composite foreign key (location_id, campus_id)
- Unique active claim (found_id, claimant_id, active_key)
- Check constraints (prn XOR staff_username)
- Triggers (audit logging, timeline events)
"""


class MockDB:
    def __init__(self):
        self.reset()

    def reset(self):
        self.campuses = [
            {"campus_id": 1, "campus_name": "Kondhwa Campus", "code": "KON"},
            {"campus_id": 2, "campus_name": "Bibwewadi Campus", "code": "BIB"}
        ]
        self.roles = [
            {"role_id": 1, "role_name": "STUDENT"},
            {"role_id": 2, "role_name": "SECURITY"},
            {"role_id": 3, "role_name": "CAMPUS_ADMIN"},
            {"role_id": 4, "role_name": "SUPER_ADMIN"}
        ]
        self.categories = [
            {"category_id": 1, "category_name": "Electronics", "icon": "laptop"},
            {"category_id": 2, "category_name": "Identification & Cards", "icon": "id-card"},
            {"category_id": 3, "category_name": "Wallets & Purses", "icon": "wallet"}
        ]
        self.locations = [
            {"location_id": 101, "campus_id": 1, "location_name": "Kondhwa Security Desk", "building": "Main Building", "floor": "Ground"},
            {"location_id": 102, "campus_id": 1, "location_name": "Kondhwa Library", "building": "Main Building", "floor": "2nd"},
            {"location_id": 201, "campus_id": 2, "location_name": "Bibwewadi Security Desk", "building": "Central Building", "floor": "Ground"},
            {"location_id": 202, "campus_id": 2, "location_name": "Bibwewadi Library", "building": "Central Building", "floor": "1st"}
        ]
        self.prn_registry = [
            {"prn": "1251150001", "campus_id": 1},  # Kondhwa student
            {"prn": "1251150002", "campus_id": 1},  # Kondhwa student 2
            {"prn": "1251030001", "campus_id": 2},  # Bibwewadi student
            {"prn": "1251030002", "campus_id": 2}   # Bibwewadi student 2
        ]
        self.users = [
            {
                "user_id": 1, "prn": None, "staff_username": "admin", "name": "Super Admin",
                "email": "admin@campuskhoj.vit.edu", "phone": "9876543210",
                # bcrypt hash for test staff account
                "password_hash": "$2b$12$LjfH8vwXeTiAWbNie3cxZehvHtQY6Q1jhEBxHs6YznE6mYMGHjAF.",
                "must_change_password": 0, "role_id": 4, "role_name": "SUPER_ADMIN", "campus_id": None,
                "status": "ACTIVE", "profile_completed": 1
            },
            {
                "user_id": 2, "prn": None, "staff_username": "security_kon", "name": "Mr. Patil",
                "email": "security.kon@campuskhoj.vit.edu", "phone": "9876543211",
                "password_hash": "$2b$12$LjfH8vwXeTiAWbNie3cxZehvHtQY6Q1jhEBxHs6YznE6mYMGHjAF.",
                "must_change_password": 0, "role_id": 2, "role_name": "SECURITY", "campus_id": 1,
                "status": "ACTIVE", "profile_completed": 1
            },
            {
                "user_id": 3, "prn": "1251150001", "staff_username": None, "name": "Riya (Kondhwa)",
                "email": "riya.1251150001@vit.edu", "phone": "9876543212",
                "password_hash": None, # First login state: PRN is password
                "must_change_password": 1, "role_id": 1, "role_name": "STUDENT", "campus_id": 1,
                "status": "ACTIVE", "profile_completed": 0
            },
            {
                "user_id": 4, "prn": "1251030001", "staff_username": None, "name": "Aman (Bibwewadi)",
                "email": "aman.1251030001@vit.edu", "phone": "9876543213",
                "password_hash": "$2b$12$LjfH8vwXeTiAWbNie3cxZehvHtQY6Q1jhEBxHs6YznE6mYMGHjAF.",
                "must_change_password": 0, "role_id": 1, "role_name": "STUDENT", "campus_id": 2,
                "status": "ACTIVE", "profile_completed": 1
            }
        ]
        self.login_attempts = []
        self.lost_items = []
        self.found_items = []
        self.match_suggestions = []
        self.claims = []
        self.claim_verifications = []
        self.item_events = []
        self.notifications = []
        self.audit_logs = []

        self._next_id = 100

mock_db = MockDB()

