from flask import Blueprint, jsonify, request

from ..db import execute, get_db, query_all, query_one
from ..errors import ConflictError, ForbiddenError, NotFoundError, ValidationError, WrongCampusError
from ..image_handler import process_and_save_image
from ..matcher import run_matcher_for_found_item, run_matcher_for_lost_item
from ..message_templates import record_outbox_message
from ..search import build_search_clause
from ..security import require_scope, token_required
from ..validators import parse_pagination, validate_date, validate_int_param, validate_time

items_bp = Blueprint("items", __name__, url_prefix="/api/v1")

@items_bp.route("/lost", methods=["POST"])
@token_required
@require_scope("full")
def report_lost_item():
    user = request.current_user
    campus_id = user["campus_id"]
    if not campus_id:
        raise ForbiddenError("User is not associated with a campus")

    # Read from form or json
    if request.is_json:
        data = request.get_json() or {}
        image_url = None
    else:
        data = request.form.to_dict()
        file = request.files.get("image")
        image_url = process_and_save_image(file)

    item_name = str(data.get("item_name", "")).strip()
    category_id = data.get("category_id")
    location_id = data.get("location_id")
    description = str(data.get("description", "")).strip()
    date_lost_str = data.get("date_lost")
    time_lost_str = data.get("time_lost")
    brand = str(data.get("brand", "")).strip() if data.get("brand") else None
    color = str(data.get("color", "")).strip() if data.get("color") else None
    room_no = str(data.get("room_no", "")).strip() if data.get("room_no") else None
    specific_spot = str(data.get("specific_spot", "")).strip() if data.get("specific_spot") else None

    if not item_name or not category_id or not location_id or not description or not date_lost_str:
        raise ValidationError("Missing required fields: item_name, category_id, location_id, description, date_lost")

    date_lost = validate_date(date_lost_str, "date_lost")
    time_lost = validate_time(time_lost_str, "time_lost")

    # Validate that location belongs to the user's campus
    loc = query_one(
        "SELECT location_id, campus_id FROM locations WHERE location_id = %s",
        (location_id,)
    )
    if not loc:
        raise NotFoundError("Selected location does not exist")
    if loc["campus_id"] != campus_id:
        raise WrongCampusError("You can only report items in your own campus")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """INSERT INTO lost_items (
                    user_id, campus_id, category_id, location_id, room_no, specific_spot, item_name,
                    description, brand, color, date_lost, time_lost, image_url, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')""",
                (
                    user["user_id"], campus_id, category_id, location_id, room_no, specific_spot, item_name,
                    description, brand, color, str(date_lost), time_lost, image_url
                )
            )
            lost_id = cursor.lastrowid

            # Add initial timeline event
            cursor.execute(
                """INSERT INTO item_events (
                    item_type, item_id, campus_id, event_type, title, description, actor_id, is_public
                ) VALUES ('LOST', %s, %s, 'REPORTED', 'Lost Report Filed', 'Item complaint registered in system.', %s, 1)""",
                (lost_id, campus_id, user["user_id"])
            )

            conn.commit()
        finally:
            cursor.close()

    # Run matcher post-commit
    try:
        run_matcher_for_lost_item(lost_id)
    except Exception:
        # Matcher failure must never roll back report
        pass

    return jsonify({
        "lost_id": lost_id,
        "status": "ACTIVE",
        "campus_id": campus_id,
        "message": "Lost report filed successfully"
    }), 201

@items_bp.route("/lost/<int:lost_id>", methods=["GET"])
def get_lost_item_detail(lost_id: int):
    item = query_one(
        """SELECT l.lost_id, l.user_id, l.item_name, l.category_id, c.category_name, c.icon AS category_icon,
                  l.campus_id, cp.campus_name, cp.code AS campus_code,
                  l.location_id, l.room_no, l.specific_spot, loc.location_name, loc.building, loc.floor,
                  l.brand, l.color, l.description, l.date_lost, l.time_lost,
                  l.image_url, l.status, l.created_at
           FROM lost_items l
           JOIN categories c ON l.category_id = c.category_id
           JOIN campuses cp ON l.campus_id = cp.campus_id
           JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
           WHERE l.lost_id = %s""",
        (lost_id,)
    )
    if not item:
        raise NotFoundError("Lost item not found")
    return jsonify({"item": item})

@items_bp.route("/lost/<int:lost_id>", methods=["PATCH"])
@token_required
@require_scope("full")
def edit_lost_item(lost_id: int):
    user = request.current_user
    item = query_one("SELECT * FROM lost_items WHERE lost_id = %s", (lost_id,))
    if not item:
        raise NotFoundError("Lost item not found")
    if item["user_id"] != user["user_id"] and user["role"] not in ("CAMPUS_ADMIN", "SUPER_ADMIN"):
        raise ForbiddenError("You can only edit your own reports")
    if item["status"] not in ("ACTIVE", "MATCHED"):
        raise ForbiddenError(f"Cannot edit report in status {item['status']}")

    data = request.get_json() or {}
    item_name = data.get("item_name", item["item_name"])
    description = data.get("description", item["description"])
    brand = data.get("brand", item["brand"])
    color = data.get("color", item["color"])

    execute(
        """UPDATE lost_items 
           SET item_name = %s, description = %s, brand = %s, color = %s 
           WHERE lost_id = %s""",
        (item_name, description, brand, color, lost_id)
    )

    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('LOST', %s, %s, 'EDITED', 'Report Details Updated', 'Owner revised item information.', %s, 1)""",
        (lost_id, item["campus_id"], user["user_id"])
    )

    return jsonify({"message": "Report updated successfully"})

@items_bp.route("/lost/<int:lost_id>/close", methods=["POST"])
@token_required
@require_scope("full")
def close_lost_item(lost_id: int):
    user = request.current_user
    item = query_one("SELECT * FROM lost_items WHERE lost_id = %s", (lost_id,))
    if not item:
        raise NotFoundError("Lost item not found")
    if item["user_id"] != user["user_id"] and user["role"] not in ("CAMPUS_ADMIN", "SUPER_ADMIN"):
        raise ForbiddenError("You can only close your own reports")

    execute("UPDATE lost_items SET status = 'CLOSED' WHERE lost_id = %s", (lost_id,))
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('LOST', %s, %s, 'CLOSED', 'Report Closed by Owner', 'Owner marked this complaint as resolved/closed.', %s, 1)""",
        (lost_id, item["campus_id"], user["user_id"])
    )
    return jsonify({"message": "Lost report closed successfully"})

@items_bp.route("/lost/<int:lost_id>/matches", methods=["GET"])
@token_required
def get_lost_matches(lost_id: int):
    user = request.current_user
    item = query_one("SELECT * FROM lost_items WHERE lost_id = %s", (lost_id,))
    if not item:
        raise NotFoundError("Lost item not found")
    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and user["campus_id"] != item["campus_id"]:
        raise ForbiddenError("You cannot view matches for items from other campuses")
    if item["user_id"] != user["user_id"] and user["role"] not in ("CAMPUS_ADMIN", "SUPER_ADMIN", "SECURITY"):
        raise ForbiddenError("Only report owner or staff can view matches")

    matches = query_all(
        """SELECT ms.match_id, ms.score, ms.breakdown, ms.created_at,
                  f.found_id, f.item_name, f.category_id, c.category_name,
                  f.location_id, loc.location_name, loc.building,
                  f.color, f.brand, f.description, f.date_found, f.image_url, f.custody
           FROM match_suggestions ms
           JOIN found_items f ON ms.found_id = f.found_id
           JOIN categories c ON f.category_id = c.category_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           WHERE ms.lost_id = %s
           ORDER BY ms.score DESC""",
        (lost_id,)
    )
    return jsonify({"matches": matches})

@items_bp.route("/found", methods=["POST"])
@token_required
@require_scope("full")
def report_found_item():
    user = request.current_user
    campus_id = user["campus_id"]
    if not campus_id:
        raise ForbiddenError("User is not associated with a campus")

    if request.is_json:
        data = request.get_json() or {}
        image_url = None
    else:
        data = request.form.to_dict()
        file = request.files.get("image")
        image_url = process_and_save_image(file)

    item_name = str(data.get("item_name", "")).strip()
    category_id = data.get("category_id")
    location_id = data.get("location_id")
    description = str(data.get("description", "")).strip()
    private_details = str(data.get("private_details", "")).strip() if data.get("private_details") else None
    date_found_str = data.get("date_found")
    time_found_str = data.get("time_found")
    brand = str(data.get("brand", "")).strip() if data.get("brand") else None
    color = str(data.get("color", "")).strip() if data.get("color") else None
    room_no = str(data.get("room_no", "")).strip() if data.get("room_no") else None
    specific_spot = str(data.get("specific_spot", "")).strip() if data.get("specific_spot") else None
    custody = str(data.get("custody", "WITH_FINDER")).strip().upper()

    if custody not in ("WITH_FINDER", "AT_DESK"):
        custody = "WITH_FINDER"

    if not item_name or not category_id or not location_id or not description or not date_found_str:
        raise ValidationError("Missing required fields: item_name, category_id, location_id, description, date_found")

    date_found = validate_date(date_found_str, "date_found")
    time_found = validate_time(time_found_str, "time_found")

    # Campus check
    loc = query_one(
        "SELECT location_id, campus_id FROM locations WHERE location_id = %s",
        (location_id,)
    )
    if not loc:
        raise NotFoundError("Selected location does not exist")
    if loc["campus_id"] != campus_id:
        raise WrongCampusError("You can only report items found in your own campus")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """INSERT INTO found_items (
                    user_id, campus_id, category_id, location_id, room_no, specific_spot, item_name,
                    brand, color, description, private_details, date_found, time_found,
                    image_url, custody, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE')""",
                (
                    user["user_id"], campus_id, category_id, location_id, room_no, specific_spot, item_name,
                    brand, color, description, private_details, str(date_found), time_found,
                    image_url, custody
                )
            )
            found_id = cursor.lastrowid

            # Initial timeline event
            cursor.execute(
                """INSERT INTO item_events (
                    item_type, item_id, campus_id, event_type, title, description, actor_id, is_public
                ) VALUES ('FOUND', %s, %s, 'REPORTED', 'Found Item Reported', 'Found item details logged into system.', %s, 1)""",
                (found_id, campus_id, user["user_id"])
            )

            if custody == "AT_DESK":
                cursor.execute(
                    """INSERT INTO item_events (
                        item_type, item_id, campus_id, event_type, title, description, actor_id, is_public
                    ) VALUES ('FOUND', %s, %s, 'RECEIVED_AT_DESK', 'Deposited at Security Desk', 'Item has been deposited at campus security desk.', %s, 1)""",
                    (found_id, campus_id, user["user_id"])
                )

            conn.commit()
        finally:
            cursor.close()

    try:
        run_matcher_for_found_item(found_id)
    except Exception:
        pass

    return jsonify({
        "found_id": found_id,
        "status": "ACTIVE",
        "campus_id": campus_id,
        "message": "Found item reported successfully"
    }), 201

@items_bp.route("/found/recent", methods=["GET"])
def get_recent_found_items():
    limit = validate_int_param(request.args.get("limit"), "limit", default=8, min_val=1, max_val=20)
    campus_id = request.args.get("campus_id")

    params = []
    where_sql = ""
    if campus_id and campus_id != "ALL":
        try:
            cid = int(campus_id)
            where_sql = "WHERE f.campus_id = %s"
            params.append(cid)
        except ValueError:
            pass

    sql = f"""
        SELECT f.found_id, f.item_name, f.category_id, c.category_name, c.icon AS category_icon,
               f.campus_id, cp.campus_name, cp.code AS campus_code,
               f.location_id, loc.location_name, loc.building, loc.floor,
               f.room_no, f.specific_spot,
               f.brand, f.color, f.description, f.date_found, f.time_found,
               f.image_url, f.custody, f.status, f.created_at,
               CASE 
                 WHEN f.status IN ('ACTIVE', 'MATCHED') THEN 'Available'
                 ELSE 'Claimed'
               END AS availability_badge
        FROM found_items f
        JOIN categories c ON f.category_id = c.category_id
        JOIN campuses cp ON f.campus_id = cp.campus_id
        JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
        {where_sql}
        ORDER BY f.created_at DESC, f.date_found DESC
        LIMIT %s
    """
    params.append(limit)
    items = query_all(sql, tuple(params))
    return jsonify({"items": items})

@items_bp.route("/found/search", methods=["GET"])
def search_found_items():
    import math
    page, page_size, offset = parse_pagination(request, default_page=1, default_size=12, max_size=50)

    q = str(request.args.get("q", "")).strip()
    category_id = request.args.get("category_id")
    campus_id = request.args.get("campus_id")
    location_id = request.args.get("location_id")
    status_filter = str(request.args.get("status", "ALL")).strip().upper()
    from_date = request.args.get("from_date") or request.args.get("from")
    to_date = request.args.get("to_date") or request.args.get("to")
    sort_by = request.args.get("sort", "recent")

    where_clauses = ["1=1"]
    params = []

    if campus_id and campus_id != "ALL":
        try:
            where_clauses.append("f.campus_id = %s")
            params.append(int(campus_id))
        except ValueError:
            pass

    if status_filter == "AVAILABLE":
        where_clauses.append("f.status IN ('ACTIVE', 'MATCHED')")
    elif status_filter == "CLAIMED":
        where_clauses.append("f.status IN ('CLAIMED', 'HANDED_OVER', 'CLOSED')")

    if category_id and category_id != "ALL":
        try:
            where_clauses.append("f.category_id = %s")
            params.append(int(category_id))
        except ValueError:
            pass

    if location_id and location_id != "ALL":
        try:
            where_clauses.append("f.location_id = %s")
            params.append(int(location_id))
        except ValueError:
            pass

    if from_date:
        where_clauses.append("f.date_found >= %s")
        params.append(from_date)

    if to_date:
        where_clauses.append("f.date_found <= %s")
        params.append(to_date)

    if q:
        search_clause, search_params = build_search_clause("f", q, include_location=True, loc_prefix="loc")
        if search_clause:
            where_clauses.append(search_clause)
            params.extend(search_params)

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN f.status IN ('ACTIVE', 'MATCHED') THEN 1 ELSE 0 END) AS available_count,
            SUM(CASE WHEN f.status NOT IN ('ACTIVE', 'MATCHED') THEN 1 ELSE 0 END) AS claimed_count
        FROM found_items f
        JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
        WHERE {where_sql}
    """
    stats_row = query_one(count_sql, tuple(params))
    total = stats_row["total"] if stats_row and stats_row["total"] else 0
    available_count = int(stats_row["available_count"] or 0) if stats_row else 0
    claimed_count = int(stats_row["claimed_count"] or 0) if stats_row else 0

    order_sql = "ORDER BY f.date_found DESC, f.created_at DESC"
    if sort_by == "oldest":
        order_sql = "ORDER BY f.date_found ASC, f.created_at ASC"

    data_sql = f"""
        SELECT f.found_id, f.item_name, f.category_id, c.category_name, c.icon AS category_icon,
               f.campus_id, cp.campus_name, cp.code AS campus_code,
               f.location_id, loc.location_name, loc.building, loc.floor,
               f.room_no, f.specific_spot,
               f.brand, f.color, f.description, f.date_found, f.time_found,
               f.image_url, f.custody, f.status, f.created_at,
               CASE 
                 WHEN f.status IN ('ACTIVE', 'MATCHED') THEN 'Available'
                 ELSE 'Claimed'
               END AS availability_badge
        FROM found_items f
        JOIN categories c ON f.category_id = c.category_id
        JOIN campuses cp ON f.campus_id = cp.campus_id
        JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
        WHERE {where_sql}
        {order_sql}
        LIMIT %s OFFSET %s
    """
    query_params = list(params) + [page_size, offset]
    items = query_all(data_sql, tuple(query_params))

    total_pages = math.ceil(total / page_size) if page_size else 1

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "available_count": available_count,
        "claimed_count": claimed_count
    })

@items_bp.route("/found/<int:found_id>", methods=["GET"])
@token_required
@require_scope("full")
def get_found_item_detail(found_id: int):
    user = request.current_user
    caller_user_id = user["user_id"]
    caller_role = user["role"]
    caller_campus_id = user["campus_id"]

    item = query_one(
        """SELECT f.found_id, f.user_id, f.item_name, f.category_id, c.category_name, c.icon AS category_icon,
                  f.campus_id, cp.campus_name, cp.code AS campus_code,
                  f.location_id, f.room_no, f.specific_spot, loc.location_name, loc.building, loc.floor,
                  f.brand, f.color, f.description, f.date_found, f.time_found,
                  f.image_url, f.custody, f.status, f.created_at,
                  f.private_details, f.storage_location
           FROM found_items f
           JOIN categories c ON f.category_id = c.category_id
           JOIN campuses cp ON f.campus_id = cp.campus_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           WHERE f.found_id = %s""",
        (found_id,)
    )
    if not item:
        raise NotFoundError("Found item not found")

    item["availability_badge"] = "Available" if item["status"] in ("ACTIVE", "MATCHED") else "Claimed"
    item["is_claimed"] = item["status"] in ("CLAIMED", "HANDED_OVER", "CLOSED")

    item["user_has_disputed"] = False
    if caller_user_id:
        existing_dispute = query_one(
            """SELECT event_id, created_at FROM item_events 
               WHERE item_type = 'FOUND' AND item_id = %s AND event_type = 'DISPUTE_RAISED' AND actor_id = %s""",
            (found_id, caller_user_id)
        )
        item["user_has_disputed"] = bool(existing_dispute)

    # Strict privacy filter:
    # 1. Finder can see own private details.
    # 2. SUPER_ADMIN can see private details across all campuses.
    # 3. CAMPUS_ADMIN and SECURITY can ONLY see private details for items in their own campus.
    # 4. All other callers (opposite campus staff, general students) have private details scrubbed.
    is_finder = (item["user_id"] is not None and caller_user_id == item["user_id"])
    is_authorized_staff = (caller_role == "SUPER_ADMIN") or (
        caller_role in ("SECURITY", "CAMPUS_ADMIN") and caller_campus_id == item["campus_id"]
    )

    # Storage location is internal desk custody information — visible to authorized staff ONLY
    if not is_authorized_staff:
        item["storage_location"] = None

    # Private details and finder identity are visible to authorized staff OR the finder themselves
    if not is_authorized_staff and not is_finder:
        item["private_details"] = None
        item["user_id"] = None  # Do not leak finder user ID

    return jsonify({"item": item})

@items_bp.route("/found/<int:found_id>/double-verify", methods=["POST"])
@token_required
@require_scope("full")
def request_double_verification(found_id: int):
    user = request.current_user
    item = query_one(
        """SELECT f.*, c.category_name, cp.campus_name, loc.location_name
           FROM found_items f
           JOIN categories c ON f.category_id = c.category_id
           JOIN campuses cp ON f.campus_id = cp.campus_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           WHERE f.found_id = %s""",
        (found_id,)
    )
    if not item:
        raise NotFoundError("Found item not found")

    if request.is_json:
        data = request.get_json() or {}
        proof_url = None
    else:
        data = request.form.to_dict()
        file = request.files.get("proof")
        proof_url = process_and_save_image(file)

    dispute_reason = str(data.get("dispute_reason", "")).strip()
    contact_phone = str(data.get("contact_phone", "")).strip() or user.get("phone")

    if not dispute_reason or len(dispute_reason) < 10:
        raise ValidationError("Please provide a detailed explanation of your ownership claim (at least 10 characters).")

    # Enforce one open dispute per student per item
    existing_dispute = query_one(
        """SELECT event_id FROM item_events 
           WHERE item_type = 'FOUND' AND item_id = %s AND event_type = 'DISPUTE_RAISED' AND actor_id = %s""",
        (found_id, user["user_id"])
    )
    if existing_dispute:
        raise ConflictError("You already have an open double verification dispute for this item.")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            detail_text = f"Student PRN {user['prn']} requested double-verification inquiry for this claimed item. Reason: {dispute_reason}"
            if proof_url:
                detail_text += f" [Proof Attached: {proof_url}]"
            if contact_phone:
                detail_text += f" [Contact Phone: {contact_phone}]"

            cursor.execute(
                """INSERT INTO item_events (
                    item_type, item_id, campus_id, event_type, title, description, actor_id, is_public
                ) VALUES ('FOUND', %s, %s, 'DISPUTE_RAISED', 'Double Verification Inquiry Requested', %s, %s, 0)""",
                (found_id, item["campus_id"], detail_text, user["user_id"])
            )
            event_id = cursor.lastrowid

            # Create immutable audit log entry
            cursor.execute(
                """INSERT INTO audit_logs (
                    user_id, action, entity_type, entity_id, details, ip_address
                ) VALUES (%s, 'DOUBLE_VERIFY_REQUESTED', 'FOUND', %s, JSON_OBJECT('found_id', %s, 'dispute_id', %s, 'reason', %s), %s)""",
                (user["user_id"], str(found_id), found_id, event_id, dispute_reason[:100], request.remote_addr)
            )

            cursor.execute(
                """SELECT u.user_id FROM users u
                   JOIN roles r ON u.role_id = r.role_id
                   WHERE u.campus_id = %s AND r.role_name IN ('SECURITY', 'CAMPUS_ADMIN') AND u.status = 'ACTIVE'""",
                (item["campus_id"],)
            )
            staff_users = cursor.fetchall()
            for s in staff_users:
                cursor.execute(
                    """INSERT INTO notifications (
                        user_id, message, notification_type, ref_type, ref_id, is_read
                    ) VALUES (%s, %s, 'SECURITY', 'FOUND', %s, 0)""",
                    (
                        s["user_id"],
                        f"Double Verification Dispute: Student {user.get('name') or user['prn']} (PRN {user['prn']}) filed ownership inquiry on Item #{found_id} ({item['item_name']}).",
                        found_id
                    )
                )

            cursor.execute(
                """INSERT INTO notifications (
                    user_id, message, notification_type, ref_type, ref_id, is_read
                ) VALUES (%s, %s, 'CLAIM_UPDATE', 'FOUND', %s, 0)""",
                (
                    user["user_id"],
                    f"Your double-verification inquiry for Item #{found_id} ({item['item_name']}) was received by Campus Security Desk.",
                    found_id
                )
            )

            # Transactional simulated outbox message
            record_outbox_message(
                cursor=cursor,
                user_id=user["user_id"],
                campus_id=item["campus_id"],
                channel="SMS",
                template_code="DOUBLE_VERIFICATION",
                context={"item_id": found_id},
                ref_type="FOUND",
                ref_id=found_id,
                phone=contact_phone or user.get("phone")
            )

            conn.commit()
        finally:
            cursor.close()

    return jsonify({
        "message": "Double verification inquiry registered successfully. Campus Security Desk will review the records.",
        "item_id": found_id,
        "dispute_id": event_id
    }), 201

@items_bp.route("/found/<int:found_id>", methods=["PATCH"])
@token_required
@require_scope("full")
def edit_found_item(found_id: int):
    user = request.current_user
    item = query_one("SELECT * FROM found_items WHERE found_id = %s", (found_id,))
    if not item:
        raise NotFoundError("Found item not found")
    if item["user_id"] != user["user_id"] and user["role"] not in ("CAMPUS_ADMIN", "SUPER_ADMIN"):
        raise ForbiddenError("You can only edit your own reports")
    if item["status"] not in ("ACTIVE", "MATCHED"):
        raise ForbiddenError(f"Cannot edit report in status {item['status']}")

    data = request.get_json() or {}
    item_name = data.get("item_name", item["item_name"])
    description = data.get("description", item["description"])
    brand = data.get("brand", item["brand"])
    color = data.get("color", item["color"])
    private_details = data.get("private_details", item["private_details"])

    execute(
        """UPDATE found_items 
           SET item_name = %s, description = %s, brand = %s, color = %s, private_details = %s
           WHERE found_id = %s""",
        (item_name, description, brand, color, private_details, found_id)
    )

    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('FOUND', %s, %s, 'EDITED', 'Found Item Details Updated', 'Finder revised item details.', %s, 1)""",
        (found_id, item["campus_id"], user["user_id"])
    )

    return jsonify({"message": "Found report updated successfully"})

@items_bp.route("/found/<int:found_id>/close", methods=["POST"])
@token_required
@require_scope("full")
def close_found_item(found_id: int):
    user = request.current_user
    item = query_one("SELECT * FROM found_items WHERE found_id = %s", (found_id,))
    if not item:
        raise NotFoundError("Found item not found")
    if item["user_id"] != user["user_id"] and user["role"] not in ("CAMPUS_ADMIN", "SUPER_ADMIN"):
        raise ForbiddenError("You can only close your own reports")

    execute("UPDATE found_items SET status = 'CLOSED' WHERE found_id = %s", (found_id,))
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('FOUND', %s, %s, 'CLOSED', 'Report Closed by Finder', 'Finder closed this item report.', %s, 1)""",
        (found_id, item["campus_id"], user["user_id"])
    )
    return jsonify({"message": "Found report closed successfully"})

@items_bp.route("/me/lost", methods=["GET"])
@token_required
def get_my_lost_reports():
    user = request.current_user
    items = query_all(
        """SELECT l.lost_id, l.item_name, l.category_id, c.category_name, c.icon AS category_icon,
                  l.campus_id, cp.campus_name, l.location_id, loc.location_name, loc.building,
                  l.color, l.brand, l.date_lost, l.image_url, l.status, l.created_at,
                  (SELECT COUNT(*) FROM match_suggestions ms WHERE ms.lost_id = l.lost_id) AS match_count
           FROM lost_items l
           JOIN categories c ON l.category_id = c.category_id
           JOIN campuses cp ON l.campus_id = cp.campus_id
           JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
           WHERE l.user_id = %s
           ORDER BY l.created_at DESC""",
        (user["user_id"],)
    )
    return jsonify({"items": items})

@items_bp.route("/me/found", methods=["GET"])
@token_required
def get_my_found_reports():
    user = request.current_user
    items = query_all(
        """SELECT f.found_id, f.item_name, f.category_id, c.category_name, c.icon AS category_icon,
                  f.campus_id, cp.campus_name, f.location_id, loc.location_name, loc.building,
                  f.color, f.brand, f.date_found, f.image_url, f.custody, f.status, f.created_at,
                  f.private_details,
                  (SELECT COUNT(*) FROM claims cl WHERE cl.found_id = f.found_id) AS claim_count
           FROM found_items f
           JOIN categories c ON f.category_id = c.category_id
           JOIN campuses cp ON f.campus_id = cp.campus_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           WHERE f.user_id = %s
           ORDER BY f.created_at DESC""",
        (user["user_id"],)
    )
    return jsonify({"items": items})

@items_bp.route("/items/<string:item_type>/<int:item_id>/poster-data", methods=["GET"])
def get_item_poster_data(item_type: str, item_id: int):
    from .claims import generate_qr_data_url
    item_type = item_type.upper()
    if item_type == "LOST":
        item = query_one(
            """SELECT l.*, c.category_name, cp.campus_name, cp.code AS campus_code,
                      loc.location_name, loc.building, loc.floor
               FROM lost_items l
               JOIN categories c ON l.category_id = c.category_id
               JOIN campuses cp ON l.campus_id = cp.campus_id
               JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
               WHERE l.lost_id = %s""",
            (item_id,)
        )
    else:
        item = query_one(
            """SELECT f.*, c.category_name, cp.campus_name, cp.code AS campus_code,
                      loc.location_name, loc.building, loc.floor
               FROM found_items f
               JOIN categories c ON f.category_id = c.category_id
               JOIN campuses cp ON f.campus_id = cp.campus_id
               JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
               WHERE f.found_id = %s""",
            (item_id,)
        )
    if not item:
        raise NotFoundError("Item not found")

    # Ensure public printable poster never leaks private details, storage location, or reporter user_id
    item["user_id"] = None
    if item_type != "LOST":
        item["private_details"] = None
        item["storage_location"] = None

    target_url = f"http://localhost:3000/student-portal/item-detail.html?type={item_type.lower()}&id={item_id}"
    qr_data_url = generate_qr_data_url(target_url)

    return jsonify({
        "item": item,
        "item_type": item_type,
        "qr_data_url": qr_data_url,
        "portal_url": target_url
    })

