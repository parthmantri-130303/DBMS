import os
import sys
import secrets
import mysql.connector

DB_HOST = "127.0.0.1"
DB_PORT = 3307
DB_USER = "root"
DB_PASSWORD = ""
NEW_DB = "campuskhoj_zero"

def setup_clean_database():
    print(f"Connecting to MySQL server at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()

    print(f"Dropping database if exists `{NEW_DB}`...")
    cursor.execute(f"DROP DATABASE IF EXISTS `{NEW_DB}`;")
    print(f"Creating fresh database `{NEW_DB}` with utf8mb4_unicode_ci...")
    cursor.execute(f"CREATE DATABASE `{NEW_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.close()
    conn.close()

    # Apply all SQL files via mysql.exe
    import subprocess
    mysql_bin = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
    sql_files = [
        "database/schema.sql",
        "database/seed.sql",
        "database/views.sql",
        "database/triggers.sql",
        "database/procedures.sql"
    ]

    for fpath in sql_files:
        print(f"Applying {fpath} via mysql.exe...")
        res = subprocess.run([
            mysql_bin,
            "-h", DB_HOST,
            "-P", str(DB_PORT),
            "-u", DB_USER,
            NEW_DB,
            "-e", f"source {fpath}"
        ], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error applying {fpath}! Stderr: {res.stderr}")
            sys.exit(1)

    print(f"Database `{NEW_DB}` successfully created and initialized with zero errors!")

def update_env():
    secret = secrets.token_urlsafe(36) # 48 chars
    env_content = f"""FLASK_ENV=development
DEBUG=True
PORT=5000
DB_HOST={DB_HOST}
DB_PORT={DB_PORT}
DB_USER={DB_USER}
DB_PASSWORD={DB_PASSWORD}
DB_NAME={NEW_DB}
DB_POOL_SIZE=10
JWT_SECRET={secret}
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5000,http://127.0.0.1:5000
MAX_CONTENT_LENGTH_MB=3
MEDIA_ROOT=media
"""
    with open("backend/.env", "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"Updated backend/.env for {NEW_DB} with new JWT_SECRET ({len(secret)} chars).")

def clean_media():
    for sub in ["lost", "found"]:
        p = os.path.join("backend", "media", sub)
        if os.path.exists(p):
            for f in os.listdir(p):
                fp = os.path.join(p, f)
                if os.path.isfile(fp) and f != ".gitkeep":
                    os.remove(fp)
    print("Cleaned backend/media/ uploaded files.")

if __name__ == "__main__":
    setup_clean_database()
    update_env()
    clean_media()
