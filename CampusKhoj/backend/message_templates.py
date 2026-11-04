"""
CampusKhoj Message Outbox Templates & Dispatcher
Zero real SMS or WhatsApp messages are sent.
All messages are strictly simulated for audit, evaluation, and user notification review.
"""

from typing import Any

TEMPLATES = {
    "MATCH_FOUND": (
        "CampusKhoj: A found item may match your lost '{item_name}' ({score}/100). "
        "Open the app to check. Do not share your PRN."
    ),
    "CLAIM_SUBMITTED": (
        "CampusKhoj: Your claim for item '{item_name}' was received by Security Desk. "
        "We will notify you once verification is under review."
    ),
    "QUESTION_ASKED": (
        "CampusKhoj: Security Desk asked a verification question for your claim #{claim_id}. "
        "Open the app to answer."
    ),
    "CLAIM_APPROVED": (
        "CampusKhoj: Good news! Your claim #{claim_id} was APPROVED by Security Desk. "
        "Bring your student ID to the Security Desk for handover. Do not share your PRN."
    ),
    "CLAIM_REJECTED": (
        "CampusKhoj: Update on claim #{claim_id}: Not approved by Security Desk ({reason}). "
        "Contact security desk if you believe this is in error."
    ),
    "HANDOVER_REMINDER": (
        "CampusKhoj: Reminder: Your approved item '{item_name}' is waiting at the Security Desk. "
        "Please collect it within 7 days."
    ),
    "HANDOVER_COMPLETED": (
        "CampusKhoj: Physical handover completed for claim #{claim_id}. "
        "Thank you for using CampusKhoj."
    ),
    "DOUBLE_VERIFICATION": (
        "CampusKhoj: Double-verification dispute inquiry logged for item #{item_id}. "
        "Security supervisor audit opened. You will be contacted."
    )
}


def mask_phone(phone: str | None) -> str:
    """
    Masks a phone number: only 2 leading digits and 4 trailing digits visible.
    Example: 9876543210 -> 98****3210.
    Returns 'No phone saved (preview only)' if empty.
    """
    if not phone:
        return "No phone saved (preview only)"
    clean = "".join(ch for ch in str(phone) if ch.isdigit())
    if clean.startswith("91") and len(clean) == 12:
        clean = clean[2:]
    if len(clean) >= 6:
        return f"{clean[:2]}****{clean[-4:]}"
    elif len(clean) >= 4:
        return f"****{clean[-4:]}"
    return "No phone saved (preview only)"


def render_message(template_code: str, context: dict[str, Any]) -> str:
    """
    Renders message body from template ensuring zero private fields leak.
    Guaranteed to omit private_details, expected_evidence, other student data.
    """
    template = TEMPLATES.get(template_code)
    if not template:
        template = "CampusKhoj: Notification update for your account. Open the app to view."

    # Filter context to safe parameters only
    safe_context = {
        "item_name": str(context.get("item_name", "item"))[:50],
        "score": str(context.get("score", "0")),
        "claim_id": str(context.get("claim_id", "")),
        "item_id": str(context.get("item_id", "")),
        "reason": str(context.get("reason", "verification criteria not met"))[:80]
    }

    try:
        body = template.format(**safe_context)
    except KeyError:
        body = template

    # Enforce maximum length 480 characters
    return body[:480]


def record_outbox_message(
    cursor,
    user_id: int,
    campus_id: int,
    channel: str,
    template_code: str,
    context: dict[str, Any],
    ref_type: str | None = None,
    ref_id: int | None = None,
    phone: str | None = None
) -> int:
    """
    Inserts a simulated message into message_outbox using the active database cursor.
    Must be executed inside the same transaction as the triggering event.
    """
    # If phone was not passed in, attempt to fetch user's phone
    if phone is None:
        cursor.execute("SELECT phone FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        if row:
            phone = row["phone"] if isinstance(row, dict) else row[0]

    phone_masked = mask_phone(phone)
    body = render_message(template_code, context)
    channel = channel.upper() if channel in ("SMS", "WHATSAPP", "EMAIL") else "SMS"

    cursor.execute(
        """INSERT INTO message_outbox (
            user_id, campus_id, channel, template_code, body, to_phone_masked, ref_type, ref_id, status, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SIMULATED', NOW())""",
        (user_id, campus_id, channel, template_code, body, phone_masked, ref_type, ref_id)
    )
    return cursor.lastrowid
