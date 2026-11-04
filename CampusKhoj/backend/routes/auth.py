import datetime
import hmac

from flask import Blueprint, jsonify, request

from ..config import config
from ..db import execute, query_one
from ..errors import (
    AccountLockedError,
    InvalidCredentialsError,
    ValidationError,
)
from ..security import (
    create_jwt,
    hash_password,
    token_required,
    validate_password_rules,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

def check_account_lockout(identifier: str) -> None:
    """Checks if identifier has exceeded failed attempts in last 15 minutes."""
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=config.LOCKOUT_MINUTES)
    row = query_one(
        """SELECT COUNT(*) AS failed_count 
           FROM login_attempts 
           WHERE identifier = %s AND success = 0 AND attempted_at >= %s""",
        (identifier, cutoff)
    )
    if row and row["failed_count"] >= config.LOCKOUT_THRESHOLD:
        raise AccountLockedError(
            f"Account locked due to {row['failed_count']} failed login attempts. Please wait {config.LOCKOUT_MINUTES} minutes or contact support.",
            {"lockout_minutes": config.LOCKOUT_MINUTES}
        )

def record_login_attempt(identifier: str, ip_address: str, success: bool) -> None:
    """Records login attempt for audit and rate limiting."""
    execute(
        "INSERT INTO login_attempts (identifier, ip_address, success, attempted_at) VALUES (%s, %s, %s, NOW())",
        (identifier, ip_address, 1 if success else 0)
    )

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    portal = str(data.get("portal", "student")).strip().lower()

    if not username or not password:
        raise ValidationError("Username and password are required")

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()

    # Brute-force lockout check
    check_account_lockout(username)

    if portal == "student":
        # Look up user by PRN
        user = query_one(
            """SELECT u.*, r.role_name, cp.campus_name, cp.code AS campus_code 
               FROM users u 
               JOIN roles r ON u.role_id = r.role_id 
               LEFT JOIN campuses cp ON u.campus_id = cp.campus_id 
               WHERE u.prn = %s""",
            (username,)
        )

        if not user:
            # Check if student exists in prn_registry but hasn't activated user row yet
            reg = query_one("SELECT * FROM prn_registry WHERE prn = %s", (username,))
            if reg:
                # Create initial student user row
                new_id = execute(
                    """INSERT INTO users (prn, role_id, campus_id, status, must_change_password, profile_completed)
                       VALUES (%s, 1, %s, 'ACTIVE', 1, 0)""",
                    (username, reg["campus_id"])
                )
                user = query_one(
                    """SELECT u.*, r.role_name, cp.campus_name, cp.code AS campus_code 
                       FROM users u 
                       JOIN roles r ON u.role_id = r.role_id 
                       LEFT JOIN campuses cp ON u.campus_id = cp.campus_id 
                       WHERE u.user_id = %s""",
                    (new_id,)
                )

        if not user or user["status"] != "ACTIVE":
            record_login_attempt(username, ip_address, False)
            raise InvalidCredentialsError("Invalid PRN or password")

        # First login check: password_hash is NULL -> accept ONLY password == PRN
        if user["password_hash"] is None:
            if not hmac.compare_digest(password, user["prn"]):
                record_login_attempt(username, ip_address, False)
                raise InvalidCredentialsError("Invalid PRN or password")

            # First login successful! Issue pwd_change scope token
            record_login_attempt(username, ip_address, True)
            token = create_jwt(
                user_id=user["user_id"],
                role=user["role_name"],
                campus_id=user["campus_id"],
                scope="pwd_change",
                portal="student",
                must_change_password=True
            )
            return jsonify({
                "token": token,
                "scope": "pwd_change",
                "must_change_password": True,
                "user": {
                    "user_id": user["user_id"],
                    "prn": user["prn"],
                    "name": user["name"],
                    "role": user["role_name"],
                    "campus_id": user["campus_id"],
                    "campus_name": user["campus_name"],
                    "campus_code": user["campus_code"],
                    "profile_completed": bool(user["profile_completed"]),
                    "must_change_password": True
                }
            })

        # Regular login with bcrypt hash verification
        if not verify_password(password, user["password_hash"]):
            record_login_attempt(username, ip_address, False)
            raise InvalidCredentialsError("Invalid PRN or password")

        record_login_attempt(username, ip_address, True)
        must_change = bool(user["must_change_password"])
        scope = "pwd_change" if must_change else "full"
        token = create_jwt(
            user_id=user["user_id"],
            role=user["role_name"],
            campus_id=user["campus_id"],
            scope=scope,
            portal="student",
            must_change_password=must_change
        )
        return jsonify({
            "token": token,
            "scope": scope,
            "must_change_password": must_change,
            "user": {
                "user_id": user["user_id"],
                "prn": user["prn"],
                "name": user["name"],
                "role": user["role_name"],
                "campus_id": user["campus_id"],
                "campus_name": user["campus_name"],
                "campus_code": user["campus_code"],
                "profile_completed": bool(user["profile_completed"]),
                "must_change_password": must_change
            }
        })

    elif portal == "admin":
        # Staff login
        user = query_one(
            """SELECT u.*, r.role_name, cp.campus_name, cp.code AS campus_code 
               FROM users u 
               JOIN roles r ON u.role_id = r.role_id 
               LEFT JOIN campuses cp ON u.campus_id = cp.campus_id 
               WHERE u.staff_username = %s""",
            (username,)
        )
        if not user or user["prn"] is not None or user["status"] != "ACTIVE":
            record_login_attempt(username, ip_address, False)
            raise InvalidCredentialsError("Invalid staff credentials")

        if not user["password_hash"] or not verify_password(password, user["password_hash"]):
            record_login_attempt(username, ip_address, False)
            raise InvalidCredentialsError("Invalid staff credentials")

        record_login_attempt(username, ip_address, True)
        must_change = bool(user["must_change_password"])
        scope = "pwd_change" if must_change else "full"
        token = create_jwt(
            user_id=user["user_id"],
            role=user["role_name"],
            campus_id=user["campus_id"],
            scope=scope,
            portal="admin",
            must_change_password=must_change
        )
        return jsonify({
            "token": token,
            "scope": scope,
            "must_change_password": must_change,
            "user": {
                "user_id": user["user_id"],
                "staff_username": user["staff_username"],
                "name": user["name"],
                "role": user["role_name"],
                "campus_id": user["campus_id"],
                "campus_name": user["campus_name"],
                "campus_code": user["campus_code"],
                "must_change_password": must_change
            }
        })

    raise ValidationError("Invalid portal specified")

@auth_bp.route("/change-password", methods=["POST"])
@token_required
def change_password():
    user = request.current_user
    data = request.get_json(silent=True) or {}
    current_password = str(data.get("current_password", "")).strip()
    new_password = str(data.get("new_password", "")).strip()

    if not current_password or not new_password:
        raise ValidationError("Current password and new password are required")

    # Fetch stored hash
    db_user = query_one("SELECT password_hash, prn, staff_username FROM users WHERE user_id = %s", (user["user_id"],))
    if not db_user:
        raise InvalidCredentialsError("User account not found")

    stored_hash = db_user["password_hash"]
    prn = db_user["prn"]

    # Verify current password
    if stored_hash is None:
        if not prn or not hmac.compare_digest(current_password, prn):
            raise InvalidCredentialsError("Current password is incorrect (must be your PRN for first-time change)")
    else:
        if not verify_password(current_password, stored_hash):
            raise InvalidCredentialsError("Current password is incorrect")

    # Validate new password rules
    validate_password_rules(new_password, prn)

    # Hash new password with bcrypt
    new_hash = hash_password(new_password)

    # Update database
    execute(
        """UPDATE users 
           SET password_hash = %s, must_change_password = 0, last_password_change = NOW() 
           WHERE user_id = %s""",
        (new_hash, user["user_id"])
    )

    # Record audit log
    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'PASSWORD_CHANGED', 'USER', %s, JSON_OBJECT('user_id', %s), %s)""",
        (user["user_id"], str(user["user_id"]), user["user_id"], request.remote_addr)
    )

    # Issue new full-scope token
    new_token = create_jwt(
        user_id=user["user_id"],
        role=user["role"],
        campus_id=user["campus_id"],
        scope="full",
        portal=user["token_portal"],
        must_change_password=False
    )

    return jsonify({
        "message": "Password updated successfully",
        "token": new_token,
        "scope": "full"
    })

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user_info():
    user = request.current_user
    db_user = query_one(
        """SELECT u.user_id, u.prn, u.staff_username, u.name, u.email, u.phone, 
                  r.role_name, u.campus_id, cp.campus_name, cp.code AS campus_code, 
                  u.must_change_password, u.profile_completed 
           FROM users u 
           JOIN roles r ON u.role_id = r.role_id 
           LEFT JOIN campuses cp ON u.campus_id = cp.campus_id 
           WHERE u.user_id = %s""",
        (user["user_id"],)
    )
    return jsonify({
        "user": {
            "user_id": db_user["user_id"],
            "prn": db_user["prn"],
            "staff_username": db_user["staff_username"],
            "name": db_user["name"],
            "email": db_user["email"],
            "phone": db_user["phone"],
            "role": db_user["role_name"],
            "campus_id": db_user["campus_id"],
            "campus_name": db_user["campus_name"],
            "campus_code": db_user["campus_code"],
            "must_change_password": bool(db_user["must_change_password"]),
            "profile_completed": bool(db_user["profile_completed"]),
            "token_scope": user["token_scope"]
        }
    })

@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"})

