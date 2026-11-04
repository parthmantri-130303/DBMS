from flask import Blueprint, jsonify, request

from ..db import execute, query_all, query_one
from ..security import token_required
from ..validators import parse_pagination

notif_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/me/notifications")

@notif_bp.route("", methods=["GET"])
@token_required
def get_notifications():
    user = request.current_user
    page, page_size, offset = parse_pagination(request, default_page=1, default_size=20, max_size=50)

    count_row = query_one(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s",
        (user["user_id"],)
    )
    total = count_row["total"] if count_row else 0

    notifications = query_all(
        """SELECT notification_id, message, notification_type, ref_type, ref_id, is_read, created_at
           FROM notifications
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (user["user_id"], page_size, offset)
    )
    return jsonify({
        "notifications": notifications,
        "page": page,
        "page_size": page_size,
        "total": total
    })

@notif_bp.route("/unread_count", methods=["GET"])
@token_required
def get_unread_count():
    user = request.current_user
    row = query_one(
        "SELECT COUNT(*) AS unread_count FROM notifications WHERE user_id = %s AND is_read = 0",
        (user["user_id"],)
    )
    return jsonify({"unread_count": row["unread_count"] if row else 0})

@notif_bp.route("/<int:notif_id>/read", methods=["POST"])
@token_required
def mark_read(notif_id: int):
    user = request.current_user
    execute(
        "UPDATE notifications SET is_read = 1 WHERE notification_id = %s AND user_id = %s",
        (notif_id, user["user_id"])
    )
    return jsonify({"message": "Notification marked as read"})

@notif_bp.route("/read_all", methods=["POST"])
@token_required
def mark_all_read():
    user = request.current_user
    execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
        (user["user_id"],)
    )
    return jsonify({"message": "All notifications marked as read"})

