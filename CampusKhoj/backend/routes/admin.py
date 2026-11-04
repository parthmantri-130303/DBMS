import csv
import datetime
import io

from flask import Blueprint, Response, jsonify, request

from ..db import execute, get_db, query_all, query_one
from ..errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from ..message_templates import record_outbox_message
from ..search import build_search_clause
from ..security import (
    generate_passport_signature,
    hash_password,
    require_portal,
    require_role,
    token_required,
    validate_password_rules,
    verify_passport_signature,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")

def enforce_admin_campus(user: dict, requested_campus: any) -> any:
    """Enforces that campus admins & security are locked to their assigned campus."""
    if user["role"] in ("CAMPUS_ADMIN", "SECURITY"):
        return user["campus_id"]
    if requested_campus and str(requested_campus).lower() != "all":
        try:
            return int(requested_campus)
        except ValueError:
            return None
    return None

# -----------------------------------------------------------------------------
# 1. Dashboard KPIs
# -----------------------------------------------------------------------------
@admin_bp.route("/dashboard", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def get_dashboard():
    user = request.current_user
    campus_id = enforce_admin_campus(user, request.args.get("campus"))

    if campus_id:
        stats = query_one("SELECT * FROM v_dashboard_stats WHERE campus_id = %s", (campus_id,))
        if not stats:
            stats = {
                "campus_id": campus_id, "active_lost_count": 0, "active_found_count": 0,
                "pending_claims_count": 0, "returned_items_count": 0,
                "registered_students_count": 0, "recovery_rate_pct": 0
            }
        urgent_claims = query_all(
            """SELECT cl.claim_id, cl.found_id, fi.item_name, cl.claim_status, cl.submitted_at, u.prn, u.name
               FROM claims cl
               JOIN found_items fi ON cl.found_id = fi.found_id
               JOIN users u ON cl.claimant_id = u.user_id
               WHERE cl.campus_id = %s AND cl.claim_status IN ('PENDING', 'UNDER_REVIEW')
                 AND cl.submitted_at <= NOW() - INTERVAL 24 HOUR
               ORDER BY cl.submitted_at ASC LIMIT 10""",
            (campus_id,)
        )
    else:
        # Aggregate across both campuses for super admin
        rows = query_all("SELECT * FROM v_dashboard_stats")
        active_lost = sum(r["active_lost_count"] for r in rows)
        active_found = sum(r["active_found_count"] for r in rows)
        pending_claims = sum(r["pending_claims_count"] for r in rows)
        returned_items = sum(r["returned_items_count"] for r in rows)
        registered_students = sum(r["registered_students_count"] for r in rows)
        avg_recovery = round(sum(r["recovery_rate_pct"] for r in rows) / max(len(rows), 1), 1)

        stats = {
            "campus_id": None,
            "campus_name": "All Campuses",
            "active_lost_count": active_lost,
            "active_found_count": active_found,
            "pending_claims_count": pending_claims,
            "returned_items_count": returned_items,
            "registered_students_count": registered_students,
            "recovery_rate_pct": avg_recovery
        }
        urgent_claims = query_all(
            """SELECT cl.claim_id, cl.found_id, fi.item_name, cl.claim_status, cl.submitted_at, u.prn, u.name
               FROM claims cl
               JOIN found_items fi ON cl.found_id = fi.found_id
               JOIN users u ON cl.claimant_id = u.user_id
               WHERE cl.claim_status IN ('PENDING', 'UNDER_REVIEW')
                 AND cl.submitted_at <= NOW() - INTERVAL 24 HOUR
               ORDER BY cl.submitted_at ASC LIMIT 10"""
        )

    return jsonify({
        "stats": stats,
        "urgent_claims": urgent_claims
    })

# -----------------------------------------------------------------------------
# 2. All Items Table & CSV Export
# -----------------------------------------------------------------------------
@admin_bp.route("/items", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def list_admin_items():
    user = request.current_user
    campus_id = enforce_admin_campus(user, request.args.get("campus"))

    item_type = request.args.get("type", "ALL").upper()
    status = request.args.get("status")
    category_id = request.args.get("category_id")
    q = request.args.get("q", "").strip()
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    export_format = request.args.get("format", "json").lower()

    queries = []
    # Lost items query
    if item_type in ("ALL", "LOST"):
        w = []
        p = []
        if campus_id:
            w.append("l.campus_id = %s")
            p.append(campus_id)
        if status and status != "ALL":
            w.append("l.status = %s")
            p.append(status)
        if category_id:
            w.append("l.category_id = %s")
            p.append(category_id)
        if from_date:
            w.append("l.date_lost >= %s")
            p.append(from_date)
        if to_date:
            w.append("l.date_lost <= %s")
            p.append(to_date)
        if q:
            search_clause, search_params = build_search_clause("l", q, include_location=False)
            if search_clause:
                w.append(search_clause)
                p.extend(search_params)

        w_str = f"WHERE {' AND '.join(w)}" if w else ""
        queries.append((
            f"""SELECT 'LOST' AS item_type, l.lost_id AS item_id, l.item_name, l.category_id, c.category_name,
                       l.campus_id, cp.campus_name, l.location_id, loc.location_name, loc.building,
                       l.brand, l.color, l.date_lost AS incident_date, l.status, l.created_at,
                       NULL AS custody, NULL AS private_details, NULL AS storage_location,
                       u.prn AS reporter_prn, u.name AS reporter_name
                FROM lost_items l
                JOIN categories c ON l.category_id = c.category_id
                JOIN campuses cp ON l.campus_id = cp.campus_id
                JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
                JOIN users u ON l.user_id = u.user_id
                {w_str}""",
            p
        ))

    # Found items query
    if item_type in ("ALL", "FOUND"):
        w = []
        p = []
        if campus_id:
            w.append("f.campus_id = %s")
            p.append(campus_id)
        if status and status != "ALL":
            w.append("f.status = %s")
            p.append(status)
        if category_id:
            w.append("f.category_id = %s")
            p.append(category_id)
        if from_date:
            w.append("f.date_found >= %s")
            p.append(from_date)
        if to_date:
            w.append("f.date_found <= %s")
            p.append(to_date)
        if q:
            search_clause, search_params = build_search_clause("f", q, include_location=False)
            if search_clause:
                w.append(search_clause)
                p.extend(search_params)

        w_str = f"WHERE {' AND '.join(w)}" if w else ""
        queries.append((
            f"""SELECT 'FOUND' AS item_type, f.found_id AS item_id, f.item_name, f.category_id, c.category_name,
                       f.campus_id, cp.campus_name, f.location_id, loc.location_name, loc.building,
                       f.brand, f.color, f.date_found AS incident_date, f.status, f.created_at,
                       f.custody, f.private_details, f.storage_location,
                       u.prn AS reporter_prn, u.name AS reporter_name
                FROM found_items f
                JOIN categories c ON f.category_id = c.category_id
                JOIN campuses cp ON f.campus_id = cp.campus_id
                JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
                JOIN users u ON f.user_id = u.user_id
                {w_str}""",
            p
        ))

    combined_sql = " UNION ALL ".join([q_pair[0] for q_pair in queries]) + " ORDER BY incident_date DESC, created_at DESC"
    combined_params = []
    for q_pair in queries:
        combined_params.extend(q_pair[1])

    items = query_all(combined_sql, tuple(combined_params))

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Item Type", "Item ID", "Item Name", "Category", "Campus", "Location", "Building",
            "Brand", "Color", "Date", "Status", "Custody", "Private Details", "Storage Location",
            "Reporter PRN", "Reporter Name", "Created At"
        ])
        for it in items:
            writer.writerow([
                it["item_type"], it["item_id"], it["item_name"], it["category_name"], it["campus_name"],
                it["location_name"], it["building"], it["brand"], it["color"], it["incident_date"],
                it["status"], it["custody"], it["private_details"], it["storage_location"],
                it["reporter_prn"], it["reporter_name"], it["created_at"]
            ])
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=campuskhoj_items_{datetime.date.today()}.csv"}
        )

    return jsonify({"items": items, "count": len(items)})

# -----------------------------------------------------------------------------
# 3. Item Detail with Private Fields
# -----------------------------------------------------------------------------
@admin_bp.route("/items/<string:item_type>/<int:item_id>", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def get_admin_item_detail(item_type: str, item_id: int):
    user = request.current_user
    t = item_type.upper()
    if t == "LOST":
        item = query_one(
            """SELECT l.*, c.category_name, cp.campus_name, loc.location_name, loc.building,
                      u.prn AS reporter_prn, u.name AS reporter_name, u.phone AS reporter_phone
               FROM lost_items l
               JOIN categories c ON l.category_id = c.category_id
               JOIN campuses cp ON l.campus_id = cp.campus_id
               JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
               JOIN users u ON l.user_id = u.user_id
               WHERE l.lost_id = %s""",
            (item_id,)
        )
    elif t == "FOUND":
        item = query_one(
            """SELECT f.*, c.category_name, cp.campus_name, loc.location_name, loc.building,
                      u.prn AS reporter_prn, u.name AS reporter_name, u.phone AS reporter_phone
               FROM found_items f
               JOIN categories c ON f.category_id = c.category_id
               JOIN campuses cp ON f.campus_id = cp.campus_id
               JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
               JOIN users u ON f.user_id = u.user_id
               WHERE f.found_id = %s""",
            (item_id,)
        )
    else:
        raise ValidationError("Invalid item type")

    if not item:
        raise NotFoundError(f"{t} item not found")

    # Campus lock check
    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and item["campus_id"] != user["campus_id"]:
        raise ForbiddenError("You cannot view items from other campuses")

    return jsonify({"item": item})

# -----------------------------------------------------------------------------
# 4. Claims Review Queue & Actions
# -----------------------------------------------------------------------------
@admin_bp.route("/claims/verify-passport", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def verify_passport_qr():
    data = request.get_json(silent=True) or {}
    scanned = str(data.get("code", "")).strip()

    # Reject empty or plain numeric input
    if not scanned or scanned.isdigit():
        raise ValidationError("Invalid Passport format. Plain numbers are rejected; signed QR payload required.")

    claim_id = None
    signature = None

    if scanned.startswith("CK-VERIFY:"):
        # Format: CK-VERIFY:<claim_id>:<prn>:<signature>
        parts = scanned.split(":")
        if len(parts) >= 4:
            try:
                claim_id = int(parts[1])
                signature = parts[3].strip()
            except ValueError:
                pass
    elif scanned.startswith("CK-PASSPORT-"):
        # Format: CK-PASSPORT-<claim_id>-<signature>
        parts = scanned.split("-")
        if len(parts) >= 4:
            try:
                claim_id = int(parts[2])
                signature = parts[3].strip()
            except ValueError:
                pass

    if not claim_id or not signature:
        raise ValidationError("Invalid Passport code format. Signed QR or Passport code required.")

    claim = query_one(
        """SELECT cl.*, fi.item_name AS found_item_name, fi.image_url AS found_image_url,
                  fi.description AS found_description, fi.private_details,
                  u.prn AS claimant_prn, u.name AS claimant_name, u.phone AS claimant_phone,
                  cp.campus_name
           FROM claims cl
           JOIN found_items fi ON cl.found_id = fi.found_id
           JOIN users u ON cl.claimant_id = u.user_id
           JOIN campuses cp ON cl.campus_id = cp.campus_id
           WHERE cl.claim_id = %s""",
        (claim_id,)
    )
    if not claim:
        raise NotFoundError(f"Claim #{claim_id} not found in system")

    # Campus isolation: desk staff can only verify claims belonging to their assigned campus
    user = request.current_user
    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("This claim belongs to another campus security desk")

    # Status check: only APPROVED claims can be handed over
    if claim["claim_status"] != "APPROVED":
        raise ConflictError(f"Claim #{claim_id} is '{claim['claim_status']}'. Only APPROVED claims can be verified for physical handover.")

    # Cryptographic tamper-proofing: verify HMAC-SHA256 signature
    if not verify_passport_signature(claim["claim_id"], claim["claimant_prn"], claim["found_id"], signature):
        raise ValidationError("Invalid or forged Passport signature. Physical handover rejected.")

    return jsonify({
        "verified": True,
        "claim": claim,
        "message": f"Passport Verified for Claim #{claim_id} ({claim['claimant_name']} — PRN: {claim['claimant_prn']})"
    })

@admin_bp.route("/claims", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def list_claims_queue():
    user = request.current_user
    campus_id = enforce_admin_campus(user, request.args.get("campus"))
    status = request.args.get("status")

    w = []
    p = []
    if campus_id:
        w.append("cl.campus_id = %s")
        p.append(campus_id)
    if status and status != "ALL":
        w.append("cl.claim_status = %s")
        p.append(status)

    w_str = f"WHERE {' AND '.join(w)}" if w else ""
    claims = query_all(
        f"""SELECT cl.*, fi.item_name AS found_item_name, fi.image_url AS found_image_url,
                   fi.private_details, fi.storage_location,
                   u.prn AS claimant_prn, u.name AS claimant_name, u.phone AS claimant_phone,
                   cp.campus_name, loc.location_name
            FROM claims cl
            JOIN found_items fi ON cl.found_id = fi.found_id
            JOIN users u ON cl.claimant_id = u.user_id
            JOIN campuses cp ON cl.campus_id = cp.campus_id
            JOIN locations loc ON fi.location_id = loc.location_id AND fi.campus_id = loc.campus_id
            {w_str}
            ORDER BY cl.submitted_at DESC""",
        tuple(p)
    )

    for c in claims:
        c["questions"] = query_all(
            "SELECT * FROM claim_verifications WHERE claim_id = %s ORDER BY verification_id ASC",
            (c["claim_id"],)
        )

    return jsonify({"claims": claims, "count": len(claims)})

@admin_bp.route("/claims/<int:claim_id>/start-review", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def start_claim_review(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    if claim["claim_status"] != "PENDING":
        raise ConflictError(f"Claim is already in status {claim['claim_status']}")

    execute(
        """UPDATE claims 
           SET claim_status = 'UNDER_REVIEW', reviewed_by = %s, reviewed_at = NOW() 
           WHERE claim_id = %s""",
        (user["user_id"], claim_id)
    )
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('CLAIM', %s, %s, 'UNDER_REVIEW', 'Under Review', 'Security desk staff started reviewing verification.', %s, 0)""",
        (claim_id, claim["campus_id"], user["user_id"])
    )
    return jsonify({"message": "Claim is now under review"})

@admin_bp.route("/claims/<int:claim_id>/questions", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def add_verification_question(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    expected_evidence = str(data.get("expected_evidence", "")).strip() if data.get("expected_evidence") else None

    if not question:
        raise ValidationError("Question text is required", {"field": "question"})

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """INSERT INTO claim_verifications (claim_id, question, expected_evidence, asked_by, created_at)
                   VALUES (%s, %s, %s, %s, NOW())""",
                (claim_id, question, expected_evidence, user["user_id"])
            )
            # Notify student
            cursor.execute(
                """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                   VALUES (%s, %s, 'VERIFICATION_REQUIRED', 'CLAIM', %s)""",
                (claim["claimant_id"], "Security desk has requested additional proof for your claim.", claim_id)
            )
            # Transactional simulated outbox message
            record_outbox_message(
                cursor=cursor,
                user_id=claim["claimant_id"],
                campus_id=claim["campus_id"],
                channel="SMS",
                template_code="QUESTION_ASKED",
                context={"claim_id": claim_id},
                ref_type="CLAIM",
                ref_id=claim_id
            )
            conn.commit()
        finally:
            cursor.close()

    return jsonify({"message": "Verification question added"})

@admin_bp.route("/claims/<int:claim_id>/verify", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def verify_question_answer(claim_id: int):
    user = request.current_user
    data = request.get_json(silent=True) or {}
    verif_id = data.get("verification_id")
    status = str(data.get("status", "")).upper()

    if not verif_id or status not in ("VERIFIED", "FAILED"):
        raise ValidationError("Invalid verification_id or status ('VERIFIED' / 'FAILED')")

    execute(
        """UPDATE claim_verifications 
           SET verification_status = %s, verified_by = %s, verified_at = NOW() 
           WHERE verification_id = %s AND claim_id = %s""",
        (status, user["user_id"], verif_id, claim_id)
    )
    return jsonify({"message": f"Verification marked as {status}"})

@admin_bp.route("/claims/<int:claim_id>/approve", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def approve_claim(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    if claim["claim_status"] not in ("PENDING", "UNDER_REVIEW"):
        raise ConflictError(f"Cannot approve claim in status {claim['claim_status']}")

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Update target claim to APPROVED
            cursor.execute(
                """UPDATE claims 
                   SET claim_status = 'APPROVED', reviewed_by = %s, reviewed_at = NOW() 
                   WHERE claim_id = %s""",
                (user["user_id"], claim_id)
            )

            # 2. Update found item to CLAIMED
            cursor.execute(
                "UPDATE found_items SET status = 'CLAIMED' WHERE found_id = %s",
                (claim["found_id"],)
            )

            # 3. If lost item linked, update to CLAIMED
            if claim["lost_id"]:
                cursor.execute(
                    "UPDATE lost_items SET status = 'CLAIMED' WHERE lost_id = %s",
                    (claim["lost_id"],)
                )

            # 4. Reject competing claims
            cursor.execute(
                """UPDATE claims 
                   SET claim_status = 'REJECTED', reject_reason = 'Another claim on this item was approved',
                       reviewed_by = %s, reviewed_at = NOW()
                   WHERE found_id = %s AND claim_id <> %s AND claim_status IN ('PENDING', 'UNDER_REVIEW')""",
                (user["user_id"], claim["found_id"], claim_id)
            )

            # 5. Events
            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('CLAIM', %s, %s, 'CLAIM_APPROVED', 'Claim Approved by Desk', 'Ready for collection at campus security desk.', %s, 0)""",
                (claim_id, claim["campus_id"], user["user_id"])
            )
            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('FOUND', %s, %s, 'CLAIM_APPROVED', 'Ownership Verified', 'Item claimed and awaiting handover at desk.', %s, 1)""",
                (claim["found_id"], claim["campus_id"], user["user_id"])
            )

            # 6. Notification to student
            cursor.execute(
                """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                   VALUES (%s, %s, 'CLAIM_APPROVED', 'CLAIM', %s)""",
                (claim["claimant_id"], "Your claim has been approved! Visit your campus security desk with your ID card to collect it.", claim_id)
            )

            # 7. Audit log
            cursor.execute(
                """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
                   VALUES (%s, 'CLAIM_APPROVED', 'CLAIM', %s, JSON_OBJECT('claim_id', %s, 'found_id', %s), %s)""",
                (user["user_id"], str(claim_id), claim_id, claim["found_id"], request.remote_addr)
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    return jsonify({"message": "Claim approved successfully"})

@admin_bp.route("/claims/<int:claim_id>/reject", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def reject_claim(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "Verification could not be confirmed.")).strip()

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """UPDATE claims 
                   SET claim_status = 'REJECTED', reject_reason = %s, reviewed_by = %s, reviewed_at = NOW() 
                   WHERE claim_id = %s""",
                (reason, user["user_id"], claim_id)
            )

            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('CLAIM', %s, %s, 'CLAIM_REJECTED', 'Claim Rejected', %s, %s, 0)""",
                (claim_id, claim["campus_id"], reason, user["user_id"])
            )

            cursor.execute(
                """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                   VALUES (%s, %s, 'CLAIM_REJECTED', 'CLAIM', %s)""",
                (claim["claimant_id"], f"Your claim was rejected: {reason}", claim_id)
            )

            cursor.execute(
                """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
                   VALUES (%s, 'CLAIM_REJECTED', 'CLAIM', %s, JSON_OBJECT('claim_id', %s, 'reason', %s), %s)""",
                (user["user_id"], str(claim_id), claim_id, reason, request.remote_addr)
            )

            # Transactional simulated outbox message
            record_outbox_message(
                cursor=cursor,
                user_id=claim["claimant_id"],
                campus_id=claim["campus_id"],
                channel="SMS",
                template_code="CLAIM_REJECTED",
                context={"claim_id": claim_id, "reason": reason},
                ref_type="CLAIM",
                ref_id=claim_id
            )

            conn.commit()
        finally:
            cursor.close()

    return jsonify({"message": "Claim rejected"})

@admin_bp.route("/claims/<int:claim_id>/handover", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
def record_handover(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and claim["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    if claim["claim_status"] != "APPROVED":
        raise ConflictError(f"Handover requires claim in APPROVED status (currently {claim['claim_status']})")

    data = request.get_json(silent=True) or {}
    received_by_prn = str(data.get("received_by_prn", "")).strip()

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Update claim to COMPLETED
            cursor.execute(
                """UPDATE claims 
                   SET claim_status = 'COMPLETED', handed_over_at = NOW(), handed_over_by = %s 
                   WHERE claim_id = %s""",
                (user["user_id"], claim_id)
            )

            # 2. Update found item to HANDED_OVER
            cursor.execute(
                "UPDATE found_items SET status = 'HANDED_OVER' WHERE found_id = %s",
                (claim["found_id"],)
            )

            # 3. If lost item linked, update to RETURNED
            if claim["lost_id"]:
                cursor.execute(
                    "UPDATE lost_items SET status = 'RETURNED' WHERE lost_id = %s",
                    (claim["lost_id"],)
                )

            # 4. Events
            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('CLAIM', %s, %s, 'COMPLETED', 'Handover Completed', %s, %s, 0)""",
                (claim_id, claim["campus_id"], f"Physically handed over to student (PRN: {received_by_prn}).", user["user_id"])
            )
            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('FOUND', %s, %s, 'HANDED_OVER', 'Item Handed Over', 'Item has been collected by owner at campus desk.', %s, 1)""",
                (claim["found_id"], claim["campus_id"], user["user_id"])
            )

            # 5. Notification
            cursor.execute(
                """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                   VALUES (%s, %s, 'HANDOVER_COMPLETED', 'CLAIM', %s)""",
                (claim["claimant_id"], "Handover complete! Item marked as successfully returned to owner.", claim_id)
            )

            # 6. Audit
            cursor.execute(
                """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
                   VALUES (%s, 'HANDOVER_COMPLETED', 'CLAIM', %s, JSON_OBJECT('claim_id', %s, 'received_by_prn', %s), %s)""",
                (user["user_id"], str(claim_id), claim_id, received_by_prn, request.remote_addr)
            )

            # 7. Transactional simulated outbox message
            record_outbox_message(
                cursor=cursor,
                user_id=claim["claimant_id"],
                campus_id=claim["campus_id"],
                channel="SMS",
                template_code="HANDOVER_COMPLETED",
                context={"claim_id": claim_id},
                ref_type="CLAIM",
                ref_id=claim_id
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    return jsonify({"message": "Handover recorded successfully"})

# -----------------------------------------------------------------------------
# 5. Users & PRN Registry Management
# -----------------------------------------------------------------------------
@admin_bp.route("/users", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def list_users():
    user = request.current_user
    campus_id = enforce_admin_campus(user, request.args.get("campus"))
    q = request.args.get("q", "").strip()
    status = request.args.get("status")

    w = []
    p = []
    if campus_id:
        w.append("u.campus_id = %s")
        p.append(campus_id)
    if status:
        w.append("u.status = %s")
        p.append(status)
    if q:
        w.append("(u.prn LIKE %s OR LOWER(u.name) LIKE %s OR LOWER(u.email) LIKE %s)")
        qw = f"%{q}%"
        p.extend([qw, qw.lower(), qw.lower()])

    w_str = f"WHERE {' AND '.join(w)}" if w else ""
    users = query_all(
        f"""SELECT u.user_id, u.prn, u.staff_username, u.name, u.email, u.phone,
                   r.role_name, u.campus_id, cp.campus_name, u.status,
                   u.must_change_password, u.profile_completed, u.created_at
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            LEFT JOIN campuses cp ON u.campus_id = cp.campus_id
            {w_str}
            ORDER BY u.created_at DESC LIMIT 100""",
        tuple(p)
    )
    return jsonify({"users": users, "count": len(users)})

@admin_bp.route("/users/<int:target_user_id>/suspend", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def toggle_user_suspend(target_user_id: int):
    user = request.current_user
    target = query_one("SELECT * FROM users WHERE user_id = %s", (target_user_id,))
    if not target:
        raise NotFoundError("User not found")

    new_status = "ACTIVE" if target["status"] == "SUSPENDED" else "SUSPENDED"
    execute("UPDATE users SET status = %s WHERE user_id = %s", (new_status, target_user_id))

    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, %s, 'USER', %s, JSON_OBJECT('user_id', %s, 'new_status', %s), %s)""",
        (user["user_id"], f"USER_{new_status}", str(target_user_id), target_user_id, new_status, request.remote_addr)
    )
    return jsonify({"message": f"User status changed to {new_status}"})

@admin_bp.route("/users/<int:target_user_id>/reset-password", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def reset_user_password(target_user_id: int):
    user = request.current_user
    target = query_one("SELECT * FROM users WHERE user_id = %s", (target_user_id,))
    if not target:
        raise NotFoundError("User not found")

    # Resetting password clears password_hash and forces first-login credential (PRN for students)
    execute(
        """UPDATE users 
           SET password_hash = NULL, must_change_password = 1, last_password_change = NULL 
           WHERE user_id = %s""",
        (target_user_id,)
    )
    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'PASSWORD_RESET_ADMIN', 'USER', %s, JSON_OBJECT('user_id', %s), %s)""",
        (user["user_id"], str(target_user_id), target_user_id, request.remote_addr)
    )
    return jsonify({"message": "Password reset to initial state. Student must log in with PRN."})

@admin_bp.route("/users/<int:target_user_id>/unlock", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def unlock_user_account(target_user_id: int):
    user = request.current_user
    target = query_one("SELECT prn, staff_username FROM users WHERE user_id = %s", (target_user_id,))
    if not target:
        raise NotFoundError("User not found")

    identifier = target["prn"] or target["staff_username"]
    execute("DELETE FROM login_attempts WHERE identifier = %s", (identifier,))

    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'ACCOUNT_UNLOCKED', 'USER', %s, JSON_OBJECT('user_id', %s), %s)""",
        (user["user_id"], str(target_user_id), target_user_id, request.remote_addr)
    )
    return jsonify({"message": "Account unlocked. Login lockout counter cleared."})

@admin_bp.route("/prn-registry/import", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def import_prn_batch():
    user = request.current_user
    data = request.get_json(silent=True) or {}
    campus_id = enforce_admin_campus(user, data.get("campus_id"))
    if not campus_id:
        raise ValidationError("Valid campus_id is required")

    raw_items = data.get("prns", [])
    if isinstance(raw_items, str):
        raw_items = [p.strip() for p in raw_items.replace("\r", "\n").replace(",", "\n").split("\n") if p.strip()]

    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("Provide a list of PRNs in 'prns'")

    from ..validators import PRN_REGEX
    inserted = 0
    skipped = 0
    invalid = 0
    seen = set()

    for item in raw_items:
        prn_str = str(item).strip()
        if not PRN_REGEX.match(prn_str):
            invalid += 1
            continue
        if prn_str in seen:
            skipped += 1
            continue
        seen.add(prn_str)

        existing = query_one("SELECT prn FROM prn_registry WHERE prn = %s", (prn_str,))
        if existing:
            skipped += 1
            continue

        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO prn_registry (prn, campus_id, imported_at) VALUES (%s, %s, NOW())",
                    (prn_str, campus_id)
                )
                cursor.execute(
                    """INSERT INTO users (prn, role_id, campus_id, status, must_change_password, profile_completed)
                       VALUES (%s, 1, %s, 'ACTIVE', 1, 0)
                       ON DUPLICATE KEY UPDATE campus_id = VALUES(campus_id)""",
                    (prn_str, campus_id)
                )
                conn.commit()
                inserted += 1
            except Exception:
                conn.rollback()
                skipped += 1
            finally:
                cursor.close()

    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'PRN_IMPORT', 'PRN_REGISTRY', %s, JSON_OBJECT('campus_id', %s, 'inserted', %s, 'skipped', %s, 'invalid', %s), %s)""",
        (user["user_id"], str(campus_id), campus_id, inserted, skipped, invalid, request.remote_addr)
    )

    return jsonify({
        "message": f"PRN import completed: {inserted} added, {skipped} duplicate/skipped, {invalid} invalid",
        "inserted": inserted,
        "skipped": skipped,
        "invalid": invalid
    })

# -----------------------------------------------------------------------------
# 6. Analytics Endpoints
# -----------------------------------------------------------------------------
@admin_bp.route("/analytics/<string:metric>", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def get_analytics(metric: str):
    m = metric.lower()
    if m == "summary":
        rows = query_all("SELECT * FROM v_dashboard_stats")
        return jsonify({"summary": rows})
    elif m == "locations":
        rows = query_all("SELECT * FROM v_top_locations LIMIT 10")
        return jsonify({"locations": rows})
    elif m == "categories":
        rows = query_all("SELECT * FROM v_top_categories")
        return jsonify({"categories": rows})
    elif m == "trend":
        rows = query_all("SELECT * FROM v_monthly_trend LIMIT 12")
        return jsonify({"trend": rows})
    elif m == "campus-compare":
        rows = query_all("SELECT * FROM v_campus_comparison")
        return jsonify({"campus_compare": rows})
    raise ValidationError("Unknown analytics metric")

# -----------------------------------------------------------------------------
# 7. Audit Logs
# -----------------------------------------------------------------------------
@admin_bp.route("/audit-logs", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def get_audit_logs():
    action = request.args.get("action")
    entity_type = request.args.get("entity_type")
    entity_id = request.args.get("entity_id")

    w = []
    p = []
    if action:
        w.append("action LIKE %s")
        p.append(f"%{action}%")
    if entity_type:
        w.append("entity_type = %s")
        p.append(entity_type)
    if entity_id:
        w.append("entity_id = %s")
        p.append(entity_id)

    w_str = f"WHERE {' AND '.join(w)}" if w else ""
    logs = query_all(
        f"""SELECT a.*, u.staff_username, u.name AS staff_name
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.user_id
            {w_str}
            ORDER BY a.created_at DESC LIMIT 100""",
        tuple(p)
    )
    return jsonify({"audit_logs": logs, "count": len(logs)})

# -----------------------------------------------------------------------------
# 8. Staff Management (SUPER_ADMIN only)
# -----------------------------------------------------------------------------
@admin_bp.route("/staff", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("SUPER_ADMIN")
def list_staff():
    staff = query_all(
        """SELECT u.user_id, u.staff_username, u.name, u.email, u.phone,
                  r.role_name, u.campus_id, cp.campus_name, u.status, u.created_at
           FROM users u
           JOIN roles r ON u.role_id = r.role_id
           LEFT JOIN campuses cp ON u.campus_id = cp.campus_id
           WHERE u.staff_username IS NOT NULL
           ORDER BY u.created_at DESC"""
    )
    return jsonify({"staff": staff})

@admin_bp.route("/staff", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("SUPER_ADMIN")
def create_staff():
    user = request.current_user
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    name = str(data.get("name", "")).strip()
    role_name = str(data.get("role", "SECURITY")).strip().upper()
    campus_id = data.get("campus_id")
    password = str(data.get("password", "")).strip()

    if not username or not name or not role_name or not password:
        raise ValidationError("Username, name, role and password are required")

    ALLOWED_STAFF_ROLES = ("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
    if role_name not in ALLOWED_STAFF_ROLES:
        raise ValidationError(f"Invalid staff role: {role_name}. Allowed: {', '.join(ALLOWED_STAFF_ROLES)}")

    if role_name in ("CAMPUS_ADMIN", "SECURITY"):
        if not campus_id:
            raise ValidationError("Campus is required for Campus Admin and Security roles", {"field": "campus_id"})
        campus_row = query_one("SELECT campus_id FROM campuses WHERE campus_id = %s", (campus_id,))
        if not campus_row:
            raise ValidationError(f"Invalid campus_id: {campus_id}", {"field": "campus_id"})
        campus_id = campus_row["campus_id"]
    elif role_name == "SUPER_ADMIN":
        if campus_id is not None:
            raise ValidationError("Super Admin must have no campus assignment (must be NULL)", {"field": "campus_id"})
        campus_id = None

    role_row = query_one("SELECT role_id FROM roles WHERE role_name = %s", (role_name,))
    if not role_row:
        raise ValidationError(f"Invalid role: {role_name}")

    existing = query_one("SELECT user_id FROM users WHERE staff_username = %s", (username,))
    if existing:
        raise ConflictError(f"Staff username '{username}' is already taken")

    # Validate password rules (min 8 chars, NIST SP 800-63B, common passwords)
    validate_password_rules(password, prn=None)

    pwd_hash = hash_password(password)
    new_id = execute(
        """INSERT INTO users (staff_username, name, password_hash, must_change_password, role_id, campus_id, status)
           VALUES (%s, %s, %s, 1, %s, %s, 'ACTIVE')""",
        (username, name, pwd_hash, role_row["role_id"], campus_id)
    )

    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'STAFF_CREATED', 'USER', %s, JSON_OBJECT('staff_username', %s, 'role', %s), %s)""",
        (user["user_id"], str(new_id), username, role_name, request.remote_addr)
    )

    return jsonify({"message": "Staff account created successfully", "user_id": new_id}), 201

# -----------------------------------------------------------------------------
# 8. Campus Locations Management
# -----------------------------------------------------------------------------
@admin_bp.route("/locations", methods=["GET"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def list_admin_locations():
    user = request.current_user
    campus_filter = request.args.get("campus_id")

    where_clauses = ["1=1"]
    params = []

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY"):
        where_clauses.append("l.campus_id = %s")
        params.append(user["campus_id"])
    elif campus_filter and campus_filter != "ALL":
        where_clauses.append("l.campus_id = %s")
        params.append(int(campus_filter))

    where_sql = " AND ".join(where_clauses)
    locations = query_all(
        f"""SELECT l.location_id, l.campus_id, cp.campus_name, cp.code AS campus_code,
                   l.location_name, l.room_or_spot, l.building, l.floor, l.description,
                   l.sort_order, l.is_active, l.created_at,
                   (SELECT COUNT(*) FROM lost_items lost WHERE lost.location_id = l.location_id AND lost.campus_id = l.campus_id) AS lost_count,
                   (SELECT COUNT(*) FROM found_items fnd WHERE fnd.location_id = l.location_id AND fnd.campus_id = l.campus_id) AS found_count
            FROM locations l
            JOIN campuses cp ON l.campus_id = cp.campus_id
            WHERE {where_sql}
            ORDER BY cp.campus_id ASC, l.sort_order ASC, l.building ASC, l.room_or_spot ASC, l.location_name ASC""",
        tuple(params)
    )
    return jsonify({"locations": locations}), 200

@admin_bp.route("/locations", methods=["POST"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def add_admin_location():
    user = request.current_user
    data = request.get_json(silent=True) or {}

    building = str(data.get("building", "")).strip()
    room_or_spot = str(data.get("room_or_spot", "")).strip()
    floor = str(data.get("floor", "")).strip() or None
    description = str(data.get("description", "")).strip() or None
    sort_order = int(data.get("sort_order", 0))

    if user["role"] == "SUPER_ADMIN":
        campus_id = data.get("campus_id")
        if not campus_id:
            raise ValidationError("campus_id is required for super admin")
    else:
        campus_id = user["campus_id"]

    if not building:
        raise ValidationError("Building or Area name is required")

    location_name = str(data.get("location_name", "")).strip()
    if not location_name:
        if room_or_spot and room_or_spot != building:
            location_name = f"{building} - {room_or_spot}"[:80]
        else:
            location_name = building[:80]

    existing = query_one(
        "SELECT location_id FROM locations WHERE campus_id = %s AND location_name = %s",
        (campus_id, location_name)
    )
    if existing:
        raise ConflictError(f"A location named '{location_name}' already exists in this campus")

    new_id = execute(
        """INSERT INTO locations (campus_id, location_name, room_or_spot, building, floor, description, sort_order, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 1)""",
        (campus_id, location_name, room_or_spot or building, building, floor, description, sort_order)
    )

    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'LOCATION_ADDED', 'LOCATION', %s, JSON_OBJECT('campus_id', %s, 'location_name', %s, 'building', %s), %s)""",
        (user["user_id"], str(new_id), campus_id, location_name, building, request.remote_addr)
    )

    return jsonify({
        "message": "Location added successfully",
        "location_id": new_id,
        "campus_id": campus_id,
        "location_name": location_name
    }), 201

@admin_bp.route("/locations/<int:loc_id>", methods=["PATCH"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def update_admin_location(loc_id: int):
    user = request.current_user
    loc = query_one("SELECT * FROM locations WHERE location_id = %s", (loc_id,))
    if not loc:
        raise NotFoundError("Location not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and loc["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    data = request.get_json(silent=True) or {}

    building = str(data.get("building", loc["building"] or "")).strip()
    room_or_spot = str(data.get("room_or_spot", loc["room_or_spot"] or "")).strip()
    location_name = str(data.get("location_name", loc["location_name"])).strip()
    floor = data.get("floor", loc["floor"])
    description = data.get("description", loc["description"])
    sort_order = int(data.get("sort_order", loc["sort_order"]))
    is_active = int(bool(data.get("is_active", loc["is_active"])))

    execute(
        """UPDATE locations 
           SET building = %s, room_or_spot = %s, location_name = %s, floor = %s, description = %s, sort_order = %s, is_active = %s
           WHERE location_id = %s""",
        (building, room_or_spot, location_name, floor, description, sort_order, is_active, loc_id)
    )

    action = 'LOCATION_DEACTIVATED' if is_active == 0 and loc["is_active"] == 1 else 'LOCATION_UPDATED'
    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, %s, 'LOCATION', %s, JSON_OBJECT('is_active', %s, 'location_name', %s), %s)""",
        (user["user_id"], action, str(loc_id), is_active, location_name, request.remote_addr)
    )

    return jsonify({"message": f"Location updated successfully (Active: {bool(is_active)})"}), 200

@admin_bp.route("/locations/<int:loc_id>", methods=["DELETE"])
@token_required
@require_portal("admin")
@require_role("CAMPUS_ADMIN", "SUPER_ADMIN")
def delete_admin_location(loc_id: int):
    user = request.current_user
    loc = query_one("SELECT * FROM locations WHERE location_id = %s", (loc_id,))
    if not loc:
        raise NotFoundError("Location not found")

    if user["role"] in ("CAMPUS_ADMIN", "SECURITY") and loc["campus_id"] != user["campus_id"]:
        raise ForbiddenError("Action restricted to your campus")

    in_use_lost = query_one("SELECT COUNT(*) AS c FROM lost_items WHERE location_id = %s", (loc_id,))
    in_use_found = query_one("SELECT COUNT(*) AS c FROM found_items WHERE location_id = %s", (loc_id,))
    total_usage = (in_use_lost["c"] if in_use_lost else 0) + (in_use_found["c"] if in_use_found else 0)

    if total_usage > 0:
        raise ConflictError(
            f"Cannot delete location '{loc['location_name']}' because it is in use by {total_usage} reports. Please deactivate it instead.",
            {"in_use_reports": total_usage}
        )

    execute("DELETE FROM locations WHERE location_id = %s", (loc_id,))
    execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (%s, 'LOCATION_DELETED', 'LOCATION', %s, JSON_OBJECT('location_name', %s), %s)""",
        (user["user_id"], str(loc_id), loc["location_name"], request.remote_addr)
    )
    return jsonify({"message": "Location deleted successfully"}), 200
