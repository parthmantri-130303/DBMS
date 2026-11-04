from flask import Blueprint, jsonify, request

from ..db import execute, query_one
from ..errors import ValidationError
from ..security import require_scope, token_required
from ..validators import validate_email, validate_phone

profile_bp = Blueprint("profile", __name__, url_prefix="/api/v1/me")

@profile_bp.route("/profile", methods=["GET"])
@token_required
def get_profile():
    user = request.current_user
    db_user = query_one(
        """SELECT u.user_id, u.prn, u.staff_username, u.name, u.email, u.phone, 
                  r.role_name, u.campus_id, cp.campus_name, cp.code AS campus_code, 
                  u.profile_completed 
           FROM users u 
           JOIN roles r ON u.role_id = r.role_id 
           LEFT JOIN campuses cp ON u.campus_id = cp.campus_id 
           WHERE u.user_id = %s""",
        (user["user_id"],)
    )
    return jsonify({
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
        "profile_completed": bool(db_user["profile_completed"])
    })

@profile_bp.route("/profile", methods=["PUT"])
@token_required
@require_scope("full")
def update_profile():
    user = request.current_user
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip() if data.get("phone") else None
    email = str(data.get("email", "")).strip() if data.get("email") else None

    if not name:
        raise ValidationError("Full name is required", {"field": "name"})

    validated_phone = validate_phone(phone)
    validated_email = validate_email(email, user.get("prn"))

    execute(
        """UPDATE users 
           SET name = %s, phone = %s, email = %s, profile_completed = 1 
           WHERE user_id = %s""",
        (name, validated_phone, validated_email, user["user_id"])
    )

    return jsonify({
        "message": "Profile updated successfully",
        "user": {
            "user_id": user["user_id"],
            "prn": user.get("prn"),
            "name": name,
            "phone": validated_phone,
            "email": validated_email,
            "profile_completed": True
        }
    })

