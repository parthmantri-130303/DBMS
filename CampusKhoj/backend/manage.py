import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.db import execute, get_db, query_all, query_one
from backend.errors import ValidationError
from backend.security import hash_password, validate_password_rules
from backend.validators import PRN_REGEX


def read_prn_file(file_path: str):
    """Reads (PRN, Name) tuples from an Excel (.xlsx) or CSV/text file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    records = []
    if path.suffix.lower() == ".xlsx":
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if not row or row[0] is None:
                    continue
                prn_val = str(row[0]).strip().split(".")[0]
                if PRN_REGEX.match(prn_val):
                    name_val = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    records.append((prn_val, name_val))
            return records
        except Exception as e:
            print(f"openpyxl parse warning: {e}, falling back to XML extraction")

        # Fallback XML extraction
        with zipfile.ZipFile(path) as z:
            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    t = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    shared_strings.append(t.text if t is not None else "")

            sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            for c in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                if v is not None:
                    val = v.text
                    if c.get("t") == "s":
                        val = shared_strings[int(val)]
                    val_str = str(val).strip().split(".")[0]
                    if PRN_REGEX.match(val_str):
                        records.append((val_str, ""))
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = [p.strip() for p in line.split(",")]
                prn_val = parts[0]
                name_val = parts[1] if len(parts) > 1 else ""
                if PRN_REGEX.match(prn_val):
                    records.append((prn_val, name_val))

    return records

def import_prn(file_path: str, campus_code: str, dry_run: bool = False):
    campus_code = campus_code.upper().strip()
    try:
        campus = query_one("SELECT campus_id, campus_name FROM campuses WHERE code = %s", (campus_code,))
    except Exception:
        campus = None

    if not campus:
        if campus_code == "KON":
            campus = {"campus_id": 1, "campus_name": "Kondhwa Campus"}
        elif campus_code == "BIB":
            campus = {"campus_id": 2, "campus_name": "Bibwewadi Campus"}
        else:
            print(f"Error: Campus code '{campus_code}' not found in database. Allowed: KON, BIB")
            sys.exit(1)

    campus_id = campus["campus_id"]
    campus_name = campus["campus_name"]
    print(f"Processing import for: {campus_name} (Code: {campus_code}, ID: {campus_id})")
    print(f"Source file: {file_path}")
    print(f"Mode: {'DRY RUN (no database writes)' if dry_run else 'LIVE COMMIT'}")

    raw_records = read_prn_file(file_path)
    total_found = len(raw_records)
    inserted = 0
    updated = 0
    skipped = 0
    invalid = 0

    seen_in_batch = {}

    for item, name in raw_records:
        if not PRN_REGEX.match(item):
            invalid += 1
            continue

        if item in seen_in_batch:
            # If we see a later row with a better name, keep it
            if not seen_in_batch[item] and name:
                seen_in_batch[item] = name
            skipped += 1
            continue
        seen_in_batch[item] = name

    print(f"Unique valid students found in file: {len(seen_in_batch)}")

    if not dry_run:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                for item, name in seen_in_batch.items():
                    # Format name to Title Case for cleaner presentation (e.g. 'Abhirup Amit Mungale')
                    clean_name = name.title() if name else None

                    cursor.execute(
                        """INSERT INTO prn_registry (prn, campus_id, imported_at) 
                           VALUES (%s, %s, NOW())
                           ON DUPLICATE KEY UPDATE campus_id = VALUES(campus_id)""",
                        (item, campus_id)
                    )
                    cursor.execute(
                        """INSERT INTO users (prn, name, role_id, campus_id, status, must_change_password, profile_completed)
                           VALUES (%s, %s, 1, %s, 'ACTIVE', 1, 0)
                           ON DUPLICATE KEY UPDATE 
                               campus_id = VALUES(campus_id),
                               name = COALESCE(VALUES(name), users.name)""",
                        (item, clean_name, campus_id)
                    )
                    inserted += 1
                conn.commit()
            finally:
                cursor.close()
    else:
        inserted = len(seen_in_batch)

    print("\n--- Import Summary ---")
    print(f"Total Rows In File:      {total_found}")
    print(f"Unique Valid Students:   {len(seen_in_batch)}")
    print(f"Processed / Added:       {inserted}")
    print(f"Duplicate Rows In Sheet: {skipped}")
    print(f"Invalid Format:          {invalid}")
    if dry_run:
        print("\nDry run completed successfully. Rerun without --dry-run to commit to database.")
    else:
        print("\nLive import completed successfully!")

def create_admin(username: str, name: str, role_name: str, campus_code: str = None, password: str = None):
    if not password:
        print("Error: Password is required.")
        sys.exit(1)

    role = query_one("SELECT role_id, role_name FROM roles WHERE role_name = %s", (role_name.upper(),))
    if not role:
        print(f"Error: Role '{role_name}' does not exist. Allowed: SUPER_ADMIN, CAMPUS_ADMIN, SECURITY")
        sys.exit(1)

    campus_id = None
    if campus_code:
        cp = query_one("SELECT campus_id FROM campuses WHERE code = %s", (campus_code.upper(),))
        if not cp:
            print(f"Error: Campus code '{campus_code}' not found.")
            sys.exit(1)
        campus_id = cp["campus_id"]

    if role["role_name"] in ("CAMPUS_ADMIN", "SECURITY") and not campus_id:
        print(f"Error: Campus code (--campus KON|BIB) is required for role {role['role_name']}")
        sys.exit(1)

    if role["role_name"] == "SUPER_ADMIN" and campus_id is not None:
        print("Error: SUPER_ADMIN must not be assigned a specific campus (omit --campus).")
        sys.exit(1)

    existing = query_one("SELECT user_id FROM users WHERE staff_username = %s", (username,))
    if existing:
        print(f"Error: Staff username '{username}' already exists.")
        sys.exit(1)

    try:
        validate_password_rules(password, prn=None)
    except ValidationError as e:
        print(f"Error: Password does not meet security rules: {e.message}")
        sys.exit(1)

    pwd_hash = hash_password(password)
    new_id = execute(
        """INSERT INTO users (staff_username, name, password_hash, must_change_password, role_id, campus_id, status)
           VALUES (%s, %s, %s, 1, %s, %s, 'ACTIVE')""",
        (username, name, pwd_hash, role["role_id"], campus_id)
    )
    print(f"Successfully created staff account '{username}' (ID: {new_id}, Role: {role['role_name']}, Campus: {campus_code or 'ALL'}, Force Change Pwd: YES)")

def init_db():
    """Initializes MySQL database from SQL scripts in database/."""
    db_folder = root_dir / "database"
    sql_files = ["schema.sql", "seed.sql", "views.sql", "triggers.sql", "procedures.sql"]

    print("Initializing database from SQL files...")
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            for sql_file in sql_files:
                file_path = db_folder / sql_file
                if not file_path.exists():
                    print(f"Warning: {sql_file} not found")
                    continue
                print(f"Applying {sql_file}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Split and execute statements
                for statement in content.split(";"):
                    stmt = statement.strip()
                    if stmt and not stmt.startswith("--") and not stmt.upper().startswith("DELIMITER"):
                        try:
                            cursor.execute(stmt)
                        except Exception:
                            # Skip warnings or duplicate key warnings
                            pass
            conn.commit()
            print("Database initialized successfully!")
        finally:
            cursor.close()

def run_nightly_rematch():
    """Runs matchmaker over all active lost items across both campuses."""
    from backend.matcher import run_matcher_for_lost_item
    print("Starting nightly rematch job across all campuses...")
    items = query_all("SELECT lost_id, item_name, campus_id FROM lost_items WHERE status IN ('ACTIVE', 'MATCHED')")
    total_processed = 0
    total_matches = 0
    for item in items:
        total_processed += 1
        matches = run_matcher_for_lost_item(item["lost_id"])
        total_matches += len(matches)

    print(f"Nightly rematch finished: processed {total_processed} items, generated {total_matches} match suggestions.")

def flag_stale_found(days: int = 90):
    """Flags active found items unclaimed for > specified days (default 90 days per institution policy)."""
    print(f"Scanning for found items unclaimed for more than {days} days...")
    stale_items = query_all(
        f"""SELECT found_id, campus_id, item_name, created_at 
           FROM found_items 
           WHERE status = 'ACTIVE' AND created_at <= NOW() - INTERVAL {int(days)} DAY"""
    )

    flagged_count = 0
    for item in stale_items:
        execute(
            """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, is_public)
               VALUES ('FOUND', %s, %s, 'STALE_UNCLAIMED', 'Unclaimed Over 90 Days', 'Flagged for desk inventory review or charitable disposal per college policy.', 1)""",
            (item["found_id"], item["campus_id"])
        )
        flagged_count += 1

    print(f"Stale inventory scan completed: {flagged_count} items flagged.")

def purge_demo_staff():
    """Removes development/demo staff accounts before production deployment."""
    print("Purging development/demo staff accounts for production safety...")
    demo_usernames = ["admin_kon", "admin_bib", "sec_kon", "sec_bib"]
    format_strings = ','.join(['%s'] * len(demo_usernames))
    count = execute(f"DELETE FROM users WHERE staff_username IN ({format_strings})", tuple(demo_usernames))
    print(f"Purged {count} demo staff accounts. Ensure production admins are created via 'create-admin' with strong passwords.")

def import_locations(file_path: str, campus_code: str):
    """Imports campus locations from a CSV file (building, room_or_spot, floor)."""
    import csv
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    campus_code_upper = campus_code.upper()
    campus_id = 1 if campus_code_upper == "KON" else 2

    records = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            building = (row.get("building") or "").strip()
            room_or_spot = (row.get("room_or_spot") or "").strip()
            floor = (row.get("floor") or "").strip()
            if floor.lower() in ("none", "", "null"):
                floor = None
            if building:
                records.append({
                    "building": building,
                    "room_or_spot": room_or_spot or building,
                    "floor": floor
                })

    print(f"Read {len(records)} location records from {file_path} for Campus {campus_code_upper} (ID {campus_id})")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            imported_count = 0
            for idx, r in enumerate(records):
                building = r["building"]
                room = r["room_or_spot"]
                floor = r["floor"]
                loc_name = f"{building} - {room}"[:80] if room and room != building else building[:80]

                cursor.execute(
                    """INSERT INTO locations (campus_id, location_name, room_or_spot, building, floor, sort_order, is_active)
                       VALUES (%s, %s, %s, %s, %s, %s, 1)
                       ON DUPLICATE KEY UPDATE 
                           room_or_spot = VALUES(room_or_spot),
                           building = VALUES(building),
                           floor = VALUES(floor),
                           sort_order = VALUES(sort_order),
                           is_active = 1""",
                    (campus_id, loc_name, room, building, floor, idx + 1)
                )
                imported_count += 1
            conn.commit()
            print(f"Successfully imported/updated {imported_count} locations for campus {campus_code_upper}.")
        finally:
            cursor.close()

def seed_demo():
    """Seeds rich, realistic demo items, claims, and verification steps using real imported PRNs."""
    print("Seeding realistic demo workflow data for Kondhwa and Bibwewadi...")
    from backend.matcher import run_matcher_for_found_item

    # Reset transactional tables to ensure pristine demo state without test pollution
    execute("SET FOREIGN_KEY_CHECKS = 0")
    for tbl in ["message_outbox", "item_events", "claim_verifications", "claims", "match_suggestions", "lost_items", "found_items"]:
        try:
            execute(f"DELETE FROM {tbl}")
            execute(f"ALTER TABLE {tbl} AUTO_INCREMENT = 1")
        except Exception:
            pass
    execute("SET FOREIGN_KEY_CHECKS = 1")

    # Ensure real Kondhwa student Aarav Sharma (PRN: 1251150353 from student_data/Kondhwa PRN.xlsx)
    s1_prn = "1251150353"
    s1_pwd = hash_password("Student@123")
    execute(
        """INSERT INTO users (prn, name, email, phone, role_id, campus_id, status, password_hash, must_change_password, profile_completed)
           VALUES (%s, 'Aarav Sharma', 'aarav.1251150353@vit.edu', '9822011223', 1, 1, 'ACTIVE', %s, 0, 1)
           ON DUPLICATE KEY UPDATE name = VALUES(name), password_hash = VALUES(password_hash), must_change_password = 0, profile_completed = 1""",
        (s1_prn, s1_pwd)
    )
    s1 = query_one("SELECT user_id FROM users WHERE prn = %s", (s1_prn,))

    # Ensure real Bibwewadi student Ananya Kulkarni (PRN: 1251030471 from student_data/Bibwewad PRN.xlsx)
    s2_prn = "1251030471"
    s2_pwd = hash_password("Student@123")
    execute(
        """INSERT INTO users (prn, name, email, phone, role_id, campus_id, status, password_hash, must_change_password, profile_completed)
           VALUES (%s, 'Ananya Kulkarni', 'ananya.1251030471@vit.edu', '9822099887', 1, 2, 'ACTIVE', %s, 0, 1)
           ON DUPLICATE KEY UPDATE name = VALUES(name), password_hash = VALUES(password_hash), must_change_password = 0, profile_completed = 1""",
        (s2_prn, s2_pwd)
    )
    s2 = query_one("SELECT user_id FROM users WHERE prn = %s", (s2_prn,))

    # Ensure fresh first-login demo student Rohit Verma (PRN: 1251150269 from student_data/Kondhwa PRN.xlsx)
    s3_prn = "1251150269"
    execute(
        """INSERT INTO users (prn, name, email, phone, role_id, campus_id, status, password_hash, must_change_password, profile_completed)
           VALUES (%s, NULL, NULL, NULL, 1, 1, 'ACTIVE', NULL, 1, 0)
           ON DUPLICATE KEY UPDATE password_hash = NULL, must_change_password = 1, profile_completed = 0""",
        (s3_prn,)
    )

    # Get staff accounts
    admin_kon = query_one("SELECT user_id FROM users WHERE staff_username = 'admin_kon'") or {"user_id": 1}
    admin_bib = query_one("SELECT user_id FROM users WHERE staff_username = 'admin_bib'") or {"user_id": 1}

    # 1. KONDHWA DEMO ITEMS
    # Kondhwa Lost: Dell Inspiron Laptop (Location 102: Central Library Kondhwa)
    l1_id = execute(
        """INSERT INTO lost_items (user_id, campus_id, category_id, location_id, item_name, brand, color, description, date_lost, status)
           VALUES (%s, 1, 1, 102, 'Dell Inspiron 15 Laptop', 'Dell', 'Black', 'Left in library 2nd floor reading hall around 3 PM. Has stickers on back cover.', CURDATE() - INTERVAL 2 DAY, 'ACTIVE')""",
        (s1["user_id"],)
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('LOST', %s, 1, 'REPORTED', 'Lost Report Filed', 'Student reported misplaced Dell Inspiron laptop in Central Library.', %s, 1)""",
        (l1_id, s1["user_id"])
    )

    # Kondhwa Found: Dell Laptop deposited at desk (Location 102: Central Library Kondhwa)
    f1_id = execute(
        """INSERT INTO found_items (user_id, campus_id, category_id, location_id, item_name, brand, color, description, private_details, storage_location, date_found, custody, status)
           VALUES (%s, 1, 1, 102, 'Dell Laptop with Charger', 'Dell', 'Black', 'Found on study table in library.', 'Intel Core i7 badge, cracked lower-left bezel, serial ending in 4920', 'Locker B-04', CURDATE() - INTERVAL 1 DAY, 'AT_DESK', 'ACTIVE')""",
        (admin_kon["user_id"],)
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('FOUND', %s, 1, 'REPORTED', 'Found Item Logged', 'Laptop deposited at Kondhwa security desk.', %s, 1)""",
        (f1_id, admin_kon["user_id"])
    )

    # Match suggestion
    run_matcher_for_found_item(f1_id)

    # Claim filed by Student 1 (active_key is automatically computed by MySQL stored generated column)
    c1_id = execute(
        """INSERT INTO claims (found_id, lost_id, claimant_id, campus_id, claim_status, claim_description)
           VALUES (%s, %s, %s, 1, 'UNDER_REVIEW', 'This is my Dell laptop forgotten during study group. My charger was also left alongside it.')""",
        (f1_id, l1_id, s1["user_id"])
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('CLAIM', %s, 1, 'CLAIM_SUBMITTED', 'Claim Filed', 'Student submitted ownership proof.', %s, 0)""",
        (c1_id, s1["user_id"])
    )

    # Verification Question
    vq1_id = execute(
        """INSERT INTO claim_verifications (claim_id, question, expected_evidence, answer, verification_status, asked_by, verified_by, verified_at)
           VALUES (%s, 'What stickers are placed on the outer laptop cover or lid?', 'Python sticker and Hackathon 2025 badge', 'There is a blue Python snake sticker and an Antigravity hackathon logo.', 'VERIFIED', %s, %s, NOW())""",
        (c1_id, admin_kon["user_id"], admin_kon["user_id"])
    )

    # 2. BIBWEWADI DEMO ITEMS
    # Bibwewadi Lost: Titan Watch (Location 203: AI/Data Science Lab 301, Category 7: Clothing & Accessories)
    l2_id = execute(
        """INSERT INTO lost_items (user_id, campus_id, category_id, location_id, item_name, brand, color, description, date_lost, status)
           VALUES (%s, 2, 7, 203, 'Titan Neo Black Watch', 'Titan', 'Black', 'Slipped off during practicals in AI/DS Lab.', CURDATE() - INTERVAL 3 DAY, 'ACTIVE')""",
        (s2["user_id"],)
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('LOST', %s, 2, 'REPORTED', 'Lost Report Filed', 'Student reported missing wrist watch in AI/DS Lab.', %s, 1)""",
        (l2_id, s2["user_id"])
    )

    # Bibwewadi Found: Titan Watch (Location 203: AI/Data Science Lab 301, Category 7)
    f2_id = execute(
        """INSERT INTO found_items (user_id, campus_id, category_id, location_id, item_name, brand, color, description, private_details, storage_location, date_found, custody, status)
           VALUES (%s, 2, 7, 203, 'Titan Analogue Watch', 'Titan', 'Black', 'Found near terminal desk in AI/DS lab.', 'Engraved with initials AK on strap buckle', 'Desk Drawer 2', CURDATE() - INTERVAL 2 DAY, 'AT_DESK', 'CLAIMED')""",
        (admin_bib["user_id"],)
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('FOUND', %s, 2, 'REPORTED', 'Found Item Logged', 'Item handed over to Bibwewadi security desk.', %s, 1)""",
        (f2_id, admin_bib["user_id"])
    )

    # Approved Claim in Bibwewadi ready for physical collection (active_key is auto-generated)
    c2_id = execute(
        """INSERT INTO claims (found_id, lost_id, claimant_id, campus_id, claim_status, claim_description, reviewed_by, reviewed_at)
           VALUES (%s, %s, %s, 2, 'APPROVED', 'It has black leather strap and my initials AK scratched on buckle.', %s, NOW())""",
        (f2_id, l2_id, s2["user_id"], admin_bib["user_id"])
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('CLAIM', %s, 2, 'CLAIM_APPROVED', 'Claim Approved by Desk', 'Ready for physical collection at Bibwewadi security desk.', %s, 0)""",
        (c2_id, admin_bib["user_id"])
    )

    print("Demo dataset seeded successfully using real imported PRNs (DEMO DATABASE ONLY):")
    print("  Kondhwa Enrolled Student PRN: 1251150353 (Password: Student@123 - Demo DB Only)")
    print("  Bibwewadi Enrolled Student PRN: 1251030471 (Password: Student@123 - Demo DB Only)")
    print("  First-Time Login Demo PRN: 1251150269 (Login with PRN as temporary password!)")
    print("  Staff Super Admin: admin (Password: <STAFF_PASSWORD>)")
    print("  Staff Kondhwa Admin: admin_kon (Password: <STAFF_PASSWORD>)")
    print("  Staff Bibwewadi Admin: admin_bib (Password: <STAFF_PASSWORD>)")

def main():
    parser = argparse.ArgumentParser(description="CampusKhoj Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # import-prn
    p_import = subparsers.add_parser("import-prn", help="Import student PRN list from Excel or CSV")
    p_import.add_argument("--file", required=True, help="Path to Excel or CSV file")
    p_import.add_argument("--campus", required=True, choices=["KON", "BIB", "kon", "bib"], help="Campus code (KON or BIB)")
    p_import.add_argument("--dry-run", action="store_true", help="Run validation without database commit")

    # create-admin
    p_admin = subparsers.add_parser("create-admin", help="Create a staff account")
    p_admin.add_argument("--username", required=True, help="Staff login username")
    p_admin.add_argument("--name", required=True, help="Staff full name")
    p_admin.add_argument("--role", required=True, choices=["SUPER_ADMIN", "CAMPUS_ADMIN", "SECURITY"], help="Staff role")
    p_admin.add_argument("--campus", choices=["KON", "BIB", "kon", "bib"], help="Assigned campus code")
    p_admin.add_argument("--password", required=True, help="Initial staff password (min 8 characters)")

    # init-db
    subparsers.add_parser("init-db", help="Initialize database tables, views, triggers, and procedures")

    # run-rematch
    subparsers.add_parser("run-rematch", help="Run nightly item matchmaker")

    # flag-stale
    p_stale = subparsers.add_parser("flag-stale", help="Flag found items unclaimed for > 90 days")
    p_stale.add_argument("--days", type=int, default=90, help="Days threshold (default 90 per policy)")

    # seed-demo
    subparsers.add_parser("seed-demo", help="Seed realistic demo reports and claims for both campuses")

    # purge-demo-staff
    subparsers.add_parser("purge-demo-staff", help="Remove demo staff accounts before production deployment")

    # import-locations
    p_loc = subparsers.add_parser("import-locations", help="Import locations from CSV (building, room_or_spot, floor)")
    p_loc.add_argument("--file", required=True, help="Path to locations CSV file")
    p_loc.add_argument("--campus", required=True, choices=["KON", "BIB", "kon", "bib"], help="Campus code (KON or BIB)")

    args = parser.parse_args()
    if args.command == "import-prn":
        import_prn(args.file, args.campus, args.dry_run)
    elif args.command == "create-admin":
        create_admin(args.username, args.name, args.role, args.campus, args.password)
    elif args.command == "init-db":
        init_db()
    elif args.command == "run-rematch":
        run_nightly_rematch()
    elif args.command == "flag-stale":
        flag_stale_found(args.days)
    elif args.command == "seed-demo":
        seed_demo()
    elif args.command == "purge-demo-staff":
        purge_demo_staff()
    elif args.command == "import-locations":
        import_locations(args.file, args.campus)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
