"""
Message Outbox Routes: Student Notification Simulator & Admin Message Log
Zero real SMS or WhatsApp messages are sent.
All messages are strictly simulated for audit, evaluation, and user notification review.
"""

from flask import Blueprint, jsonify, request

from ..db import execute, query_all, query_one
from ..errors import ForbiddenError
from ..security import require_portal, require_role, token_required
from ..validators import parse_pagination

messages_bp = Blueprint("messages", __name__, url_prefix="/api/v1")


@messages_bp.route("/me/messages", methods=["GET"])
@token_required
def get_my_messages():
    """
    Returns simulated SMS/WhatsApp message outbox history for the authenticated student.
    Enforces strict IDOR protection: a student can NEVER access another student's messages.
    """
    user = request.current_user
    page, page_size, offset = parse_pagination(request, default_page=1, default_size=20, max_size=50)

    count_row = query_one(
        "SELECT COUNT(*) AS total FROM message_outbox WHERE user_id = %s",
        (user["user_id"],)
    )
    total = count_row["total"] if count_row else 0

    unread_row = query_one(
        "SELECT COUNT(*) AS unread FROM message_outbox WHERE user_id = %s AND status = 'SIMULATED'",
        (user["user_id"],)
    )
    unread_count = unread_row["unread"] if unread_row else 0

    messages = query_all(
        """SELECT message_id, user_id, campus_id, channel, template_code,
                  body, to_phone_masked, ref_type, ref_id, status, created_at
           FROM message_outbox
           WHERE user_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (user["user_id"], page_size, offset)
    )

    return jsonify({
        "messages": messages,
        "page": page,
        "page_size": page_size,
        "total": total,
        "unread_count": unread_count,
        "disclaimer": "Simulated: no real SMS or WhatsApp is sent."
    }), 200


@messages_bp.route("/me/messages/unread_count", methods=["GET"])
@token_required
def get_my_messages_unread_count():
    """Returns unread simulated message count for badge display."""
    user = request.current_user
    row = query_one(
        "SELECT COUNT(*) AS unread FROM message_outbox WHERE user_id = %s AND status = 'SIMULATED'",
        (user["user_id"],)
    )
    return jsonify({"unread_count": row["unread"] if row else 0}), 200


@messages_bp.route("/me/messages/read_all", methods=["POST"])
@token_required
def mark_all_messages_read():
    """Marks all simulated messages as READ for the authenticated student."""
    user = request.current_user
    execute(
        "UPDATE message_outbox SET status = 'READ' WHERE user_id = %s AND status = 'SIMULATED'",
        (user["user_id"],)
    )
    return jsonify({"message": "All simulated messages marked as read"}), 200


@messages_bp.route("/admin/messages", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def get_admin_messages_log():
    """
    Returns message outbox log for staff/examiner audit.
    Campus Admin and Security are strictly scoped to their own campus;
    SUPER_ADMIN can view all campuses or filter by campus.
    """
    user = request.current_user
    page, page_size, offset = parse_pagination(request, default_page=1, default_size=25, max_size=100)

    campus_filter = request.args.get("campus_id")
    channel_filter = request.args.get("channel")
    template_filter = request.args.get("template_code")
    q = request.args.get("q", "").strip()

    where_clauses = ["1=1"]
    params = []

    # Enforce campus scoping
    if user["role"] in ("CAMPUS_ADMIN", "SECURITY"):
        where_clauses.append("m.campus_id = %s")
        params.append(user["campus_id"])
    elif campus_filter and campus_filter != "ALL":
        where_clauses.append("m.campus_id = %s")
        params.append(int(campus_filter))

    if channel_filter and channel_filter != "ALL":
        where_clauses.append("m.channel = %s")
        params.append(channel_filter.upper())

    if template_filter and template_filter != "ALL":
        where_clauses.append("m.template_code = %s")
        params.append(template_filter)

    if q:
        where_clauses.append("(m.body LIKE %s OR u.prn LIKE %s OR u.name LIKE %s)")
        q_wild = f"%{q}%"
        params.extend([q_wild, q_wild, q_wild])

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM message_outbox m
        JOIN users u ON m.user_id = u.user_id
        WHERE {where_sql}
    """
    count_row = query_one(count_sql, tuple(params))
    total = count_row["total"] if count_row else 0

    data_sql = f"""
        SELECT m.message_id, m.user_id, u.prn, u.name AS student_name,
               m.campus_id, cp.campus_name, cp.code AS campus_code,
               m.channel, m.template_code, m.body, m.to_phone_masked,
               m.ref_type, m.ref_id, m.status, m.created_at
        FROM message_outbox m
        JOIN users u ON m.user_id = u.user_id
        JOIN campuses cp ON m.campus_id = cp.campus_id
        WHERE {where_sql}
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
    """
    data_params = list(params) + [page_size, offset]
    messages = query_all(data_sql, tuple(data_params))

    return jsonify({
        "messages": messages,
        "page": page,
        "page_size": page_size,
        "total": total,
        "disclaimer": "Simulated: no real SMS or WhatsApp is sent. For evaluation and audit only."
    }), 200

