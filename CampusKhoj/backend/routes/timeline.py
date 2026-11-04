from flask import Blueprint, jsonify, request

from ..db import query_all, query_one
from ..errors import NotFoundError, ValidationError
from ..security import token_required

timeline_bp = Blueprint("timeline", __name__, url_prefix="/api/v1")

@timeline_bp.route("/items/<string:item_type>/<int:item_id>/timeline", methods=["GET"])
@token_required
def get_item_timeline(item_type: str, item_id: int):
    item_type_upper = item_type.strip().upper()
    if item_type_upper not in ("LOST", "FOUND", "CLAIM"):
        raise ValidationError("item_type must be 'lost', 'found', or 'claim'")

    user = request.current_user
    caller_user_id = user["user_id"]
    caller_role = user["role"]
    caller_campus_id = user["campus_id"]

    is_owner = False
    item_campus_id = None

    if item_type_upper == "LOST":
        row = query_one("SELECT user_id, campus_id FROM lost_items WHERE lost_id = %s", (item_id,))
        if not row:
            raise NotFoundError("Lost item not found")
        if caller_user_id == row["user_id"]:
            is_owner = True
        item_campus_id = row["campus_id"]

    elif item_type_upper == "FOUND":
        row = query_one("SELECT user_id, campus_id FROM found_items WHERE found_id = %s", (item_id,))
        if not row:
            raise NotFoundError("Found item not found")
        if caller_user_id == row["user_id"]:
            is_owner = True
        item_campus_id = row["campus_id"]

    elif item_type_upper == "CLAIM":
        row = query_one("SELECT claimant_id, campus_id FROM claims WHERE claim_id = %s", (item_id,))
        if not row:
            raise NotFoundError("Claim not found")
        if caller_user_id == row["claimant_id"]:
            is_owner = True
        item_campus_id = row["campus_id"]

    # Staff sees full timeline ONLY for their own campus (or SUPER_ADMIN)
    is_authorized_staff = (caller_role == "SUPER_ADMIN") or (
        caller_role in ("SECURITY", "CAMPUS_ADMIN") and caller_campus_id == item_campus_id
    )

    if is_owner or is_authorized_staff:
        # Full timeline for owners and authorized staff
        events = query_all(
            """SELECT event_id, item_type, item_id, campus_id, event_type, title, description,
                      actor_id, is_public, created_at
               FROM item_events
               WHERE item_type = %s AND item_id = %s
               ORDER BY created_at ASC""",
            (item_type_upper, item_id)
        )
    else:
        # Public events only for other viewers (and cross-campus staff)
        events = query_all(
            """SELECT event_id, item_type, item_id, campus_id, event_type, title, description,
                      is_public, created_at
               FROM item_events
               WHERE item_type = %s AND item_id = %s AND is_public = 1
               ORDER BY created_at ASC""",
            (item_type_upper, item_id)
        )

    return jsonify({"events": events, "count": len(events)})

