import base64
import hashlib
import io
import qrcode
from flask import Blueprint, jsonify, request

from ..config import config
from ..db import execute, get_db, query_all, query_one
from ..errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    WrongCampusError,
)
from ..image_handler import process_and_save_image
from ..message_templates import record_outbox_message
from ..security import generate_passport_signature, require_scope, token_required

claims_bp = Blueprint("claims", __name__, url_prefix="/api/v1")

def generate_qr_data_url(data_str: str) -> str:
    """Generates an in-memory base64 PNG data URL of a QR Code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1F4D3A", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

@claims_bp.route("/found/<int:found_id>/claims", methods=["POST"])
@token_required
@require_scope("full")
def submit_claim(found_id: int):
    user = request.current_user
    if request.is_json:
        data = request.get_json(silent=True) or {}
        proof_url = data.get("proof_url")
    else:
        data = request.form.to_dict()
        file = request.files.get("proof") or request.files.get("image")
        proof_url = process_and_save_image(file) if file else None

    claim_description = str(data.get("claim_description", "")).strip()
    proof_type = str(data.get("proof_type", "RECEIPT")).strip().upper() if data.get("proof_type") else "RECEIPT"
    lost_id = data.get("lost_id")
    if lost_id:
        try:
            lost_id = int(lost_id)
        except (ValueError, TypeError):
            lost_id = None

    if not claim_description:
        raise ValidationError("Claim description / proof of ownership is required", {"field": "claim_description"})

    found = query_one("SELECT * FROM found_items WHERE found_id = %s", (found_id,))
    if not found:
        raise NotFoundError("Found item not found")

    # Campus check
    if found["campus_id"] != user["campus_id"]:
        raise WrongCampusError("You can only claim items found in your own campus")

    # Status check
    if found["status"] not in ("ACTIVE", "MATCHED"):
        raise ConflictError(f"Cannot claim an item with status {found['status']}")

    # Cannot claim own found report
    if found["user_id"] == user["user_id"]:
        raise ConflictError("You cannot claim an item you reported as found")

    # Check for existing active claim by this user
    existing = query_one(
        """SELECT claim_id FROM claims 
           WHERE found_id = %s AND claimant_id = %s AND claim_status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED')""",
        (found_id, user["user_id"])
    )
    if existing:
        raise ConflictError("You already have an active claim under review for this item", {"claim_id": existing["claim_id"]})

    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """INSERT INTO claims (
                    found_id, lost_id, claimant_id, campus_id, claim_description, proof_url, proof_type, claim_status, submitted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', NOW())""",
                (found_id, lost_id, user["user_id"], user["campus_id"], claim_description, proof_url, proof_type)
            )
            claim_id = cursor.lastrowid

            # Add timeline events
            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('CLAIM', %s, %s, 'CLAIM_SUBMITTED', 'Claim Submitted', 'Student filed ownership claim with description.', %s, 0)""",
                (claim_id, user["campus_id"], user["user_id"])
            )

            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('FOUND', %s, %s, 'CLAIM_SUBMITTED', 'New Claim Filed', 'A student submitted an ownership claim.', %s, 0)""",
                (found_id, user["campus_id"], user["user_id"])
            )

            # Transactional simulated outbox message
            record_outbox_message(
                cursor=cursor,
                user_id=user["user_id"],
                campus_id=user["campus_id"],
                channel="SMS",
                template_code="CLAIM_SUBMITTED",
                context={"item_name": found.get("item_name", "Found Item"), "claim_id": claim_id},
                ref_type="CLAIM",
                ref_id=claim_id,
                phone=user.get("phone")
            )

            conn.commit()
        finally:
            cursor.close()

    return jsonify({
        "claim_id": claim_id,
        "claim_status": "PENDING",
        "proof_url": proof_url,
        "proof_type": proof_type,
        "message": "Claim submitted successfully. Security desk staff will review your claim."
    }), 201

@claims_bp.route("/me/claims", methods=["GET"])
@token_required
def get_my_claims():
    user = request.current_user
    claims = query_all(
        """SELECT cl.claim_id, cl.found_id, cl.lost_id, cl.campus_id, cl.claim_description,
                  cl.proof_url, cl.proof_type,
                  cl.claim_status, cl.reject_reason, cl.submitted_at, cl.reviewed_at, cl.handed_over_at,
                  f.item_name AS found_item_name, f.image_url AS found_image_url,
                  f.date_found, loc.location_name, loc.building, cp.campus_name
           FROM claims cl
           JOIN found_items f ON cl.found_id = f.found_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           JOIN campuses cp ON cl.campus_id = cp.campus_id
           WHERE cl.claimant_id = %s
           ORDER BY cl.submitted_at DESC""",
        (user["user_id"],)
    )

    # Attach verification questions (without expected_evidence!)
    for c in claims:
        questions = query_all(
            """SELECT verification_id, question, answer, verification_status, created_at 
               FROM claim_verifications 
               WHERE claim_id = %s 
               ORDER BY verification_id ASC""",
            (c["claim_id"],)
        )
        c["questions"] = questions

    return jsonify({"claims": claims})

@claims_bp.route("/claims/<int:claim_id>", methods=["GET"])
@token_required
def get_claim_detail(claim_id: int):
    user = request.current_user
    is_staff = user["role"] in ("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")

    claim = query_one(
        """SELECT cl.*, f.item_name AS found_item_name, f.image_url AS found_image_url,
                  f.description AS found_description, f.date_found, loc.location_name, loc.building,
                  u.prn AS claimant_prn, u.name AS claimant_name, u.phone AS claimant_phone
           FROM claims cl
           JOIN found_items f ON cl.found_id = f.found_id
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
           JOIN users u ON cl.claimant_id = u.user_id
           WHERE cl.claim_id = %s""",
        (claim_id,)
    )
    if not claim:
        raise NotFoundError("Claim not found")

    if not is_staff and claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only view your own claims")

    # Fetch questions
    if is_staff:
        # Staff see expected_evidence
        questions = query_all(
            """SELECT verification_id, question, expected_evidence, answer, verification_status,
                      asked_by, verified_by, verified_at, created_at
               FROM claim_verifications
               WHERE claim_id = %s
               ORDER BY verification_id ASC""",
            (claim_id,)
        )
    else:
        # Students NEVER see expected_evidence
        questions = query_all(
            """SELECT verification_id, question, answer, verification_status, created_at
               FROM claim_verifications
               WHERE claim_id = %s
               ORDER BY verification_id ASC""",
            (claim_id,)
        )

    claim["questions"] = questions
    return jsonify({"claim": claim})

@claims_bp.route("/claims/<int:claim_id>/answers", methods=["POST"])
@token_required
@require_scope("full")
def submit_verification_answers(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")
    if claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only submit answers to your own claim")
    if claim["claim_status"] not in ("PENDING", "UNDER_REVIEW"):
        raise ConflictError(f"Cannot submit answers for claim with status {claim['claim_status']}")

    data = request.get_json(silent=True) or {}
    answers = data.get("answers", [])
    if not answers or not isinstance(answers, list):
        raise ValidationError("Missing 'answers' list")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            for item in answers:
                verif_id = item.get("verification_id")
                answer_text = str(item.get("answer", "")).strip()
                if verif_id and answer_text:
                    cursor.execute(
                        """UPDATE claim_verifications 
                           SET answer = %s, verification_status = 'ANSWERED' 
                           WHERE verification_id = %s AND claim_id = %s""",
                        (answer_text, verif_id, claim_id)
                    )

            cursor.execute(
                """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
                   VALUES ('CLAIM', %s, %s, 'VERIFICATION_ANSWERED', 'Verification Answers Provided', 'Claimant submitted requested verification proof.', %s, 0)""",
                (claim_id, claim["campus_id"], user["user_id"])
            )
            conn.commit()
        finally:
            cursor.close()

    return jsonify({"message": "Verification answers submitted successfully"})

@claims_bp.route("/claims/<int:claim_id>/cancel", methods=["POST"])
@token_required
@require_scope("full")
def cancel_claim(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")
    if claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only cancel your own claim")
    if claim["claim_status"] not in ("PENDING", "UNDER_REVIEW"):
        raise ConflictError(f"Cannot cancel claim with status {claim['claim_status']}")

    execute("UPDATE claims SET claim_status = 'CANCELLED' WHERE claim_id = %s", (claim_id,))
    execute(
        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, actor_id, is_public)
           VALUES ('CLAIM', %s, %s, 'CLAIM_CANCELLED', 'Claim Cancelled', 'Claimant cancelled ownership claim.', %s, 0)""",
        (claim_id, claim["campus_id"], user["user_id"])
    )
    return jsonify({"message": "Claim cancelled successfully"})

@claims_bp.route("/claims/<int:claim_id>/messages", methods=["GET"])
@token_required
def get_claim_messages(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")
    is_staff = user["role"] in ("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
    if not is_staff and claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only view messages for your own claim")

    messages = query_all(
        """SELECT m.message_id, m.claim_id, m.sender_id, m.sender_role, m.message_text,
                  m.sent_at, m.read_at, u.name AS sender_name, u.prn AS sender_prn, u.staff_username
           FROM claim_messages m
           JOIN users u ON m.sender_id = u.user_id
           WHERE m.claim_id = %s
           ORDER BY m.sent_at ASC""",
        (claim_id,)
    )

    # Mark other party's messages as read
    target_role = "STUDENT" if is_staff else "STAFF"
    execute(
        "UPDATE claim_messages SET read_at = NOW() WHERE claim_id = %s AND sender_role = %s AND read_at IS NULL",
        (claim_id, target_role)
    )

    return jsonify({"messages": messages})

@claims_bp.route("/claims/<int:claim_id>/messages", methods=["POST"])
@token_required
def send_claim_message(claim_id: int):
    user = request.current_user
    claim = query_one("SELECT * FROM claims WHERE claim_id = %s", (claim_id,))
    if not claim:
        raise NotFoundError("Claim not found")

    is_staff = user["role"] in ("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
    if not is_staff and claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only send messages for your own claim")

    data = request.get_json(silent=True) or {}
    text = str(data.get("message", "")).strip()
    if not text:
        raise ValidationError("Message text cannot be empty")

    sender_role = "STAFF" if is_staff else "STUDENT"
    msg_id = execute(
        """INSERT INTO claim_messages (claim_id, sender_id, sender_role, message_text, sent_at)
           VALUES (%s, %s, %s, %s, NOW())""",
        (claim_id, user["user_id"], sender_role, text)
    )

    if is_staff:
        execute(
            """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id, is_read)
               VALUES (%s, %s, 'CLAIM_MESSAGE', 'CLAIM', %s, 0)""",
            (
                claim["claimant_id"],
                f"Security desk sent you a message regarding Claim #{claim_id}",
                claim_id
            )
        )

    return jsonify({
        "message_id": msg_id,
        "claim_id": claim_id,
        "sender_role": sender_role,
        "message_text": text,
        "sent_at": "Just now",
        "status": "SENT"
    }), 201

@claims_bp.route("/claims/<int:claim_id>/passport", methods=["GET"])
@token_required
def get_claim_passport(claim_id: int):
    user = request.current_user
    claim = query_one(
        """SELECT cl.*, fi.item_name AS found_item_name, fi.image_url AS found_image_url,
                  fi.date_found, loc.location_name, loc.building, cp.campus_name, cp.code AS campus_code,
                  u.prn AS claimant_prn, u.name AS claimant_name
           FROM claims cl
           JOIN found_items fi ON cl.found_id = fi.found_id
           JOIN locations loc ON fi.location_id = loc.location_id AND fi.campus_id = loc.campus_id
           JOIN campuses cp ON cl.campus_id = cp.campus_id
           JOIN users u ON cl.claimant_id = u.user_id
           WHERE cl.claim_id = %s""",
        (claim_id,)
    )
    if not claim:
        raise NotFoundError("Claim not found")

    is_staff = user["role"] in ("SECURITY", "CAMPUS_ADMIN", "SUPER_ADMIN")
    if not is_staff and claim["claimant_id"] != user["user_id"]:
        raise ForbiddenError("You can only access the passport for your own claim")

    # Only APPROVED claims can receive an active pickup passport
    if claim["claim_status"] != "APPROVED":
        raise ConflictError(f"Claim #{claim_id} is '{claim['claim_status']}'. A Pickup Passport is only issued once your claim is APPROVED by security.")

    # Generate tamper-evident HMAC-SHA256 signature
    sec_sig = generate_passport_signature(claim_id, claim["claimant_prn"], claim["found_id"])
    qr_payload = f"CK-VERIFY:{claim_id}:{claim['claimant_prn']}:{sec_sig}"
    qr_data_url = generate_qr_data_url(qr_payload)

    return jsonify({
        "claim_id": claim_id,
        "passport_code": f"CK-PASSPORT-{claim_id:04d}-{sec_sig}",
        "claimant_name": claim["claimant_name"],
        "claimant_prn": claim["claimant_prn"],
        "campus_name": claim["campus_name"],
        "campus_code": claim["campus_code"],
        "found_item_name": claim["found_item_name"],
        "found_image_url": claim["found_image_url"],
        "claim_status": claim["claim_status"],
        "submitted_at": claim["submitted_at"],
        "security_hash": sec_sig,
        "qr_data_url": qr_data_url
    })


