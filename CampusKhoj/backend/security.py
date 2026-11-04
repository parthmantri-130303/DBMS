import datetime
import hashlib
import hmac
from functools import wraps
from typing import Any

import bcrypt
import jwt
from flask import request

from .config import config
from .db import query_one
from .errors import (
    AuthRequiredError,
    ForbiddenError,
    PasswordChangeRequiredError,
    ValidationError,
)

# Weak/common passwords blocklist
COMMON_PASSWORDS = {
    "password", "password123", "12345678", "123456789", "qwerty123",
    "admin123", "welcome1", "college123", "vitpune123", "student123"
}

def hash_password(password: str) -> str:
    """Hashes a password with bcrypt at cost 12."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against its bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def validate_password_rules(new_password: str, prn: str | None = None) -> None:
    """
    Validates password complexity per NIST SP 800-63B and project rules:
    - Minimum 8 characters
    - Not equal to PRN
    - Does not contain PRN
    - Not a common password
    """
    if not new_password or len(new_password) < 8:
        raise ValidationError("Password must be at least 8 characters long", {"field": "new_password"})

    if prn:
        if new_password.strip() == prn.strip():
            raise ValidationError("New password cannot be your PRN", {"field": "new_password"})
        if prn.strip() in new_password:
            raise ValidationError("New password cannot contain your PRN", {"field": "new_password"})

    if new_password.lower() in COMMON_PASSWORDS:
        raise ValidationError("Password is too common. Please choose a stronger password", {"field": "new_password"})

def create_jwt(
    user_id: int,
    role: str,
    campus_id: int | None,
    scope: str = "full",
    portal: str = "student",
    must_change_password: bool = False,
    expires_in_minutes: int | None = None
) -> str:
    """Generates a signed JWT token with claims."""
    if expires_in_minutes is None:
        expires_in_minutes = config.JWT_PWD_CHANGE_MINUTES if scope == "pwd_change" else config.JWT_ACCESS_MINUTES

    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "campus_id": campus_id,
        "scope": scope,
        "portal": portal,
        "must_change_password": bool(must_change_password),
        "iat": now,
        "exp": now + datetime.timedelta(minutes=expires_in_minutes)
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token."""
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthRequiredError("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise AuthRequiredError("Invalid authentication token.")

def token_required(f):
    """Decorator to require and validate Bearer JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise AuthRequiredError("Authorization header missing or not Bearer token")

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_jwt(token)
        user_id = int(payload["sub"])

        user = query_one(
            """SELECT u.user_id, u.prn, u.staff_username, u.name, u.email, u.phone,
                      u.role_id, r.role_name AS role, u.campus_id, u.status,
                      u.must_change_password, u.profile_completed
               FROM users u
               JOIN roles r ON u.role_id = r.role_id
               WHERE u.user_id = %s""",
            (user_id,)
        )
        if not user:
            raise AuthRequiredError("User account not found")

        if user["status"] != "ACTIVE":
            raise ForbiddenError(f"Account is {user['status'].lower()}. Please contact administrator.")

        token_scope = payload.get("scope", "full")
        if bool(user.get("must_change_password", 0)) and token_scope == "full":
            raise PasswordChangeRequiredError("Password change required before accessing other resources.")

        role_map = {1: "STUDENT", 2: "SECURITY", 3: "CAMPUS_ADMIN", 4: "SUPER_ADMIN"}
        role_name = user.get("role") or user.get("role_name") or role_map.get(user.get("role_id"))

        request.current_user = {
            "user_id": int(user["user_id"]),
            "prn": user.get("prn"),
            "staff_username": user.get("staff_username"),
            "name": user.get("name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "role": role_name,
            "campus_id": int(user["campus_id"]) if user.get("campus_id") is not None else None,
            "must_change_password": bool(user.get("must_change_password", 0)),
            "profile_completed": bool(user.get("profile_completed", 0)),
            "token_scope": token_scope,
            "token_portal": payload.get("portal", "student")
        }
        return f(*args, **kwargs)
    return decorated

def require_scope(required_scope: str = "full"):
    """Enforces that the token scope matches the required scope."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_scope = getattr(request, "current_user", {}).get("token_scope")
            if current_scope != required_scope:
                if current_scope == "pwd_change":
                    raise PasswordChangeRequiredError()
                raise ForbiddenError("Insufficient token scope")
            return f(*args, **kwargs)
        return decorated
    return decorator

def require_role(*allowed_roles: str):
    """Enforces role-based access control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(request, "current_user", {}).get("role")
            if user_role not in allowed_roles:
                raise ForbiddenError(f"Action requires one of roles: {', '.join(allowed_roles)}")
            return f(*args, **kwargs)
        return decorated
    return decorator

def require_portal(portal_name: str):
    """Enforces token portal affinity (student vs admin)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token_portal = getattr(request, "current_user", {}).get("token_portal")
            if token_portal != portal_name:
                raise ForbiddenError(f"This endpoint is only accessible from the {portal_name} portal")
            return f(*args, **kwargs)
        return decorated
    return decorator

def generate_passport_signature(claim_id: int, claimant_prn: str, found_id: int) -> str:
    """Generates a tamper-evident HMAC-SHA256 signature for physical pickup verification."""
    message = f"CK-PASSPORT:{claim_id}:{claimant_prn}:{found_id}".encode("utf-8")
    return hmac.new(config.JWT_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()[:16].upper()

def verify_passport_signature(claim_id: int, claimant_prn: str, found_id: int, signature: str) -> bool:
    """Verifies HMAC-SHA256 signature against forged passport presentation."""
    if not signature:
        return False
    expected = generate_passport_signature(claim_id, claimant_prn, found_id)
    return hmac.compare_digest(signature.strip().upper(), expected)
