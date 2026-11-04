import datetime
import difflib
import json
from typing import Any

from .config import config
from .db import get_db, query_all, query_one
from .message_templates import record_outbox_message


def calculate_match_score(
    lost: dict[str, Any],
    found: dict[str, Any],
    lost_building: str | None = None,
    found_building: str | None = None
) -> dict[str, Any]:
    """
    Scores similarity between a lost item and a found item.
    Returns: {"score": int, "breakdown": dict}
    """
    # Hard filters: Must be same campus and same category
    if lost["campus_id"] != found["campus_id"]:
        return {"score": 0, "breakdown": {}}
    if lost["category_id"] != found["category_id"]:
        return {"score": 0, "breakdown": {}}

    breakdown = {}

    # 1. Category match (30 pts)
    category_pts = 30
    breakdown["category"] = category_pts

    # 2. Item name similarity (0 - 25 pts)
    lost_name = (lost.get("item_name") or "").lower().strip()
    found_name = (found.get("item_name") or "").lower().strip()
    ratio = difflib.SequenceMatcher(None, lost_name, found_name).ratio()
    name_pts = int(round(ratio * 25))
    breakdown["name"] = name_pts

    # 3. Color match (15 pts)
    color_pts = 0
    lost_color = (lost.get("color") or "").lower().strip()
    found_color = (found.get("color") or "").lower().strip()
    if lost_color and found_color:
        if lost_color == found_color or lost_color in found_color or found_color in lost_color:
            color_pts = 15
    breakdown["color"] = color_pts

    # 4. Location match (0 - 20 pts)
    location_pts = 0
    if lost.get("location_id") == found.get("location_id"):
        location_pts = 20
    elif lost_building and found_building and lost_building.lower() == found_building.lower():
        location_pts = 10
    breakdown["location"] = location_pts

    # 5. Date proximity (0 - 10 pts)
    date_pts = 0
    date_lost = lost.get("date_lost")
    date_found = found.get("date_found")
    if isinstance(date_lost, str):
        date_lost = datetime.datetime.strptime(date_lost, "%Y-%m-%d").date()
    if isinstance(date_found, str):
        date_found = datetime.datetime.strptime(date_found, "%Y-%m-%d").date()

    if date_lost and date_found:
        diff_days = (date_found - date_lost).days
        if diff_days < -1:
            # Found more than 1 day before lost is unlikely
            date_pts = 0
        elif diff_days == 0:
            date_pts = 10
        elif abs(diff_days) <= 3:
            date_pts = 5
        elif diff_days > 0 and diff_days <= 7:
            date_pts = 2

    breakdown["time"] = date_pts

    total_score = min(100, category_pts + name_pts + color_pts + location_pts + date_pts)
    return {"score": total_score, "breakdown": breakdown}

def run_matcher_for_lost_item(lost_id: int) -> list[dict[str, Any]]:
    """Runs matcher against all active found items for a given lost report."""
    lost = query_one(
        "SELECT l.*, loc.building FROM lost_items l JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id WHERE l.lost_id = %s",
        (lost_id,)
    )
    if not lost or lost["status"] not in ("ACTIVE", "MATCHED"):
        return []

    candidates = query_all(
        """SELECT f.*, loc.building 
           FROM found_items f 
           JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id 
           WHERE f.campus_id = %s AND f.category_id = %s AND f.status IN ('ACTIVE', 'MATCHED')""",
        (lost["campus_id"], lost["category_id"])
    )

    created_matches = []
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            for found in candidates:
                result = calculate_match_score(lost, found, lost.get("building"), found.get("building"))
                score = result["score"]
                if score >= config.MATCH_THRESHOLD:
                    breakdown_json = json.dumps(result["breakdown"])
                    cursor.execute(
                        """INSERT INTO match_suggestions (lost_id, found_id, campus_id, score, breakdown)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE score = VALUES(score), breakdown = VALUES(breakdown)""",
                        (lost["lost_id"], found["found_id"], lost["campus_id"], score, breakdown_json)
                    )
                    # Notify lost item owner
                    cursor.execute(
                        """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                           VALUES (%s, %s, 'MATCH_SUGGESTED', 'LOST', %s)""",
                        (
                            lost["user_id"],
                            f"Possible match found for your lost '{lost['item_name']}' ({score}% similarity)",
                            lost["lost_id"]
                        )
                    )
                    # Add timeline event
                    cursor.execute(
                        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, is_public)
                           VALUES ('LOST', %s, %s, 'MATCH_SUGGESTED', 'Potential Match Found', %s, 0)""",
                        (lost["lost_id"], lost["campus_id"], f"System identified a matching found item ({score}% score).")
                    )
                    # Create transactional simulated SMS outbox message
                    record_outbox_message(
                        cursor=cursor,
                        user_id=lost["user_id"],
                        campus_id=lost["campus_id"],
                        channel="SMS",
                        template_code="MATCH_FOUND",
                        context={"item_name": lost["item_name"], "score": score},
                        ref_type="LOST",
                        ref_id=lost["lost_id"]
                    )
                    created_matches.append({"found_id": found["found_id"], "score": score})

            if created_matches:
                cursor.execute("UPDATE lost_items SET status = 'MATCHED' WHERE lost_id = %s AND status = 'ACTIVE'", (lost_id,))
                found_ids = [m["found_id"] for m in created_matches]
                format_strings = ','.join(['%s'] * len(found_ids))
                cursor.execute(f"UPDATE found_items SET status = 'MATCHED' WHERE found_id IN ({format_strings}) AND status = 'ACTIVE'", tuple(found_ids))

            conn.commit()
        finally:
            cursor.close()

    return created_matches

def run_matcher_for_found_item(found_id: int) -> list[dict[str, Any]]:
    """Runs matcher against all active lost items for a given found report."""
    found = query_one(
        "SELECT f.*, loc.building FROM found_items f JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id WHERE f.found_id = %s",
        (found_id,)
    )
    if not found or found["status"] not in ("ACTIVE", "MATCHED"):
        return []

    candidates = query_all(
        """SELECT l.*, loc.building 
           FROM lost_items l 
           JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id 
           WHERE l.campus_id = %s AND l.category_id = %s AND l.status IN ('ACTIVE', 'MATCHED')""",
        (found["campus_id"], found["category_id"])
    )

    created_matches = []
    with get_db() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            for lost in candidates:
                result = calculate_match_score(lost, found, lost.get("building"), found.get("building"))
                score = result["score"]
                if score >= config.MATCH_THRESHOLD:
                    breakdown_json = json.dumps(result["breakdown"])
                    cursor.execute(
                        """INSERT INTO match_suggestions (lost_id, found_id, campus_id, score, breakdown)
                           VALUES (%s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE score = VALUES(score), breakdown = VALUES(breakdown)""",
                        (lost["lost_id"], found["found_id"], found["campus_id"], score, breakdown_json)
                    )
                    cursor.execute(
                        """INSERT INTO notifications (user_id, message, notification_type, ref_type, ref_id)
                           VALUES (%s, %s, 'MATCH_SUGGESTED', 'LOST', %s)""",
                        (
                            lost["user_id"],
                            f"A found item matches your lost '{lost['item_name']}' ({score}% similarity)",
                            lost["lost_id"]
                        )
                    )
                    cursor.execute(
                        """INSERT INTO item_events (item_type, item_id, campus_id, event_type, title, description, is_public)
                           VALUES ('LOST', %s, %s, 'MATCH_SUGGESTED', 'Potential Match Found', %s, 0)""",
                        (lost["lost_id"], lost["campus_id"], f"System identified a matching found item ({score}% score).")
                    )
                    # Create transactional simulated SMS outbox message
                    record_outbox_message(
                        cursor=cursor,
                        user_id=lost["user_id"],
                        campus_id=lost["campus_id"],
                        channel="SMS",
                        template_code="MATCH_FOUND",
                        context={"item_name": lost["item_name"], "score": score},
                        ref_type="LOST",
                        ref_id=lost["lost_id"]
                    )
                    created_matches.append({"lost_id": lost["lost_id"], "score": score})

            if created_matches:
                cursor.execute("UPDATE found_items SET status = 'MATCHED' WHERE found_id = %s AND status = 'ACTIVE'", (found_id,))
                lost_ids = [m["lost_id"] for m in created_matches]
                format_strings = ','.join(['%s'] * len(lost_ids))
                cursor.execute(f"UPDATE lost_items SET status = 'MATCHED' WHERE lost_id IN ({format_strings}) AND status = 'ACTIVE'", tuple(lost_ids))

            conn.commit()
        finally:
            cursor.close()

    return created_matches

