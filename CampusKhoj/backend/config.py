import os
from pathlib import Path

# Load .env file manually without requiring python-dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    PORT = int(os.getenv("PORT", "5000"))

    # Database
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "rootpassword")
    DB_NAME = os.getenv("DB_NAME", "campuskhoj")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))

    # Security
    JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_campuskhoj_jwt_key_32_characters_minimum_prod!")
    if len(JWT_SECRET) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters long")

    JWT_ACCESS_MINUTES = int(os.getenv("JWT_ACCESS_MINUTES", "60"))
    JWT_PWD_CHANGE_MINUTES = int(os.getenv("JWT_PWD_CHANGE_MINUTES", "15"))

    # Rate limiting & Lockout
    LOCKOUT_THRESHOLD = int(os.getenv("LOCKOUT_THRESHOLD", "5"))
    LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))
    MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "50"))
    STALE_ITEM_DAYS = int(os.getenv("STALE_ITEM_DAYS", "90"))

    # Media
    MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(Path(__file__).parent / "media")))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "3")) * 1024 * 1024

    # CORS
    cors_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3001,http://127.0.0.1:3002")
    CORS_ORIGINS: list[str] = [origin.strip() for origin in cors_str.split(",") if origin.strip()]

config = Config()

