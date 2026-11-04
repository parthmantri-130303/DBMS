import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import config
from backend.db import query_one, query_all

def verify():
    r1 = query_one("SELECT COUNT(*) as c FROM prn_registry")
    r2 = query_one("SELECT COUNT(*) as c FROM users WHERE role_id = 1")
    r3 = query_one("SELECT COUNT(*) as c FROM users WHERE role_id = 1 AND must_change_password = 1 AND password_hash IS NULL")
    
    print(f"Database: {config.DB_NAME}")
    print(f"prn_registry total rows:               {r1['c']}")
    print(f"users total students (role_id=1):      {r2['c']}")
    print(f"students with must_change_password=1:  {r3['c']}")
    
    # Campus counts
    campuses = query_all("SELECT c.campus_name, COUNT(p.prn) as cnt FROM campuses c LEFT JOIN prn_registry p ON c.campus_id = p.campus_id GROUP BY c.campus_id, c.campus_name")
    for cp in campuses:
        print(f"  - {cp['campus_name']}: {cp['cnt']} PRNs")

    # Ensure strong test passwords for all staff accounts
    import bcrypt
    from backend.db import execute
    staff_pwd = os.environ.get("KHOJ_TEST_STAFF_PASSWORD", "Staff@CampusKhoj2026!").encode("utf-8")
    h_staff = bcrypt.hashpw(staff_pwd, bcrypt.gensalt(12)).decode('utf-8')
    execute("UPDATE users SET password_hash = %s, must_change_password = 0 WHERE role_id > 1", (h_staff,))
    # Reset test student accounts to unactivated initial PRN state for audit runs
    execute("UPDATE users SET password_hash = NULL, must_change_password = 1, profile_completed = 0 WHERE prn IN ('1251150269', '1251150202')")
    print("Ensured strong test credentials for all staff and reset audit student accounts.")

if __name__ == '__main__':
    verify()
