from flask import Blueprint, jsonify, request

from ..db import query_all, query_one
from ..errors import NotFoundError
from ..search import build_search_clause
from ..validators import parse_pagination, validate_int_param

ref_bp = Blueprint("reference", __name__, url_prefix="/api/v1")

@ref_bp.route("/campuses", methods=["GET"])
def get_campuses():
    campuses = query_all("SELECT campus_id, campus_name, code FROM campuses ORDER BY campus_id")
    return jsonify({"campuses": campuses})

@ref_bp.route("/campuses/<int:cid>/locations", methods=["GET"])
def get_campus_locations(cid: int):
    campus = query_one("SELECT campus_id FROM campuses WHERE campus_id = %s", (cid,))
    if not campus:
        raise NotFoundError("Campus not found")

    include_inactive = request.args.get("include_inactive") in ("1", "true", "True")
    active_clause = "" if include_inactive else "AND is_active = 1"

    locations = query_all(
        f"""SELECT location_id, campus_id, location_name, room_or_spot, building, floor, description, sort_order, is_active 
           FROM locations 
           WHERE campus_id = %s {active_clause}
           ORDER BY sort_order ASC, building ASC, room_or_spot ASC, location_name ASC""",
        (cid,)
    )
    return jsonify({"locations": locations})

@ref_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = query_all("SELECT category_id, category_name, description, icon FROM categories ORDER BY category_id")
    return jsonify({"categories": categories})

@ref_bp.route("/campuses/<int:cid>/lost", methods=["GET"])
def get_campus_lost_items(cid: int):
    campus = query_one("SELECT campus_id FROM campuses WHERE campus_id = %s", (cid,))
    if not campus:
        raise NotFoundError("Campus not found")

    page, page_size, offset = parse_pagination(request, default_page=1, default_size=20, max_size=50)

    category_id = request.args.get("category_id")
    location_id = request.args.get("location_id")
    color = request.args.get("color")
    q = request.args.get("q", "").strip()
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    status = request.args.get("status", "ACTIVE")

    where_clauses = ["l.campus_id = %s"]
    params = [cid]

    if status and status != "ALL":
        where_clauses.append("l.status = %s")
        params.append(status)

    if category_id:
        where_clauses.append("l.category_id = %s")
        params.append(category_id)

    if location_id:
        where_clauses.append("l.location_id = %s")
        params.append(location_id)

    if color:
        where_clauses.append("LOWER(l.color) LIKE %s")
        params.append(f"%{color.lower().strip()}%")

    if from_date:
        where_clauses.append("l.date_lost >= %s")
        params.append(from_date)

    if to_date:
        where_clauses.append("l.date_lost <= %s")
        params.append(to_date)

    if q:
        search_clause, search_params = build_search_clause("l", q, include_location=False)
        if search_clause:
            where_clauses.append(search_clause)
            params.extend(search_params)

    where_str = " AND ".join(where_clauses)

    count_row = query_one(f"SELECT COUNT(*) AS total FROM lost_items l WHERE {where_str}", tuple(params))
    total = count_row["total"] if count_row else 0

    query_params = list(params) + [page_size, offset]
    sql = f"""
        SELECT l.lost_id, l.item_name, l.category_id, c.category_name, c.icon AS category_icon,
               l.campus_id, cp.campus_name, cp.code AS campus_code,
               l.location_id, loc.location_name, loc.building, loc.floor,
               l.brand, l.color, l.description, l.date_lost, l.time_lost,
               l.image_url, l.status, l.created_at
        FROM lost_items l
        JOIN categories c ON l.category_id = c.category_id
        JOIN campuses cp ON l.campus_id = cp.campus_id
        JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
        WHERE {where_str}
        ORDER BY l.date_lost DESC, l.created_at DESC
        LIMIT %s OFFSET %s
    """
    items = query_all(sql, tuple(query_params))

    return jsonify({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total
    })


@ref_bp.route("/campuses/<int:cid>/found", methods=["GET"])
def get_campus_found_items(cid: int):
    campus = query_one("SELECT campus_id FROM campuses WHERE campus_id = %s", (cid,))
    if not campus:
        raise NotFoundError("Campus not found")

    page, page_size, offset = parse_pagination(request, default_page=1, default_size=20, max_size=50)

    category_id = request.args.get("category_id")
    location_id = request.args.get("location_id")
    color = request.args.get("color")
    q = request.args.get("q", "").strip()
    from_date = request.args.get("from")
    to_date = request.args.get("to")
    status = request.args.get("status", "ACTIVE")

    where_clauses = ["f.campus_id = %s"]
    params = [cid]

    if status and status != "ALL":
        where_clauses.append("f.status = %s")
        params.append(status)

    if category_id:
        where_clauses.append("f.category_id = %s")
        params.append(category_id)

    if location_id:
        where_clauses.append("f.location_id = %s")
        params.append(location_id)

    if color:
        where_clauses.append("LOWER(f.color) LIKE %s")
        params.append(f"%{color.lower().strip()}%")

    if from_date:
        where_clauses.append("f.date_found >= %s")
        params.append(from_date)

    if to_date:
        where_clauses.append("f.date_found <= %s")
        params.append(to_date)

    if q:
        search_clause, search_params = build_search_clause("f", q, include_location=False)
        if search_clause:
            where_clauses.append(search_clause)
            params.extend(search_params)

    where_str = " AND ".join(where_clauses)

    count_row = query_one(f"SELECT COUNT(*) AS total FROM found_items f WHERE {where_str}", tuple(params))
    total = count_row["total"] if count_row else 0

    query_params = list(params) + [page_size, offset]
    # NOTE: private_details and storage_location are deliberately EXCLUDED from SELECT!
    sql = f"""
        SELECT f.found_id, f.item_name, f.category_id, c.category_name, c.icon AS category_icon,
               f.campus_id, cp.campus_name, cp.code AS campus_code,
               f.location_id, loc.location_name, loc.building, loc.floor,
               f.brand, f.color, f.description, f.date_found, f.time_found,
               f.image_url, f.custody, f.status, f.created_at
        FROM found_items f
        JOIN categories c ON f.category_id = c.category_id
        JOIN campuses cp ON f.campus_id = cp.campus_id
        JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
        WHERE {where_str}
        ORDER BY f.date_found DESC, f.created_at DESC
        LIMIT %s OFFSET %s
    """
    items = query_all(sql, tuple(query_params))

    return jsonify({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total
    })

@ref_bp.route("/items/recent", methods=["GET"])
def get_recent_items():
    limit = validate_int_param(request.args.get("limit"), "limit", default=6, min_val=1, max_val=20)
    item_type = request.args.get("type", "ALL").upper()
    campus_id = request.args.get("campus_id")

    queries = []
    params = []

    if item_type in ("ALL", "FOUND"):
        q_found = """
            SELECT f.found_id AS id, 'FOUND' AS item_type, f.item_name, f.category_id,
                   c.category_name, c.icon AS category_icon,
                   f.campus_id, cp.campus_name, cp.code AS campus_code,
                   loc.location_name, loc.building,
                   f.image_url, f.date_found AS item_date, f.status, f.created_at
            FROM found_items f
            JOIN categories c ON f.category_id = c.category_id
            JOIN campuses cp ON f.campus_id = cp.campus_id
            JOIN locations loc ON f.location_id = loc.location_id AND f.campus_id = loc.campus_id
            WHERE f.status IN ('ACTIVE', 'MATCHED')
        """
        if campus_id:
            q_found += " AND f.campus_id = %s"
            params.append(int(campus_id))
        queries.append(q_found)

    if item_type in ("ALL", "LOST"):
        q_lost = """
            SELECT l.lost_id AS id, 'LOST' AS item_type, l.item_name, l.category_id,
                   c.category_name, c.icon AS category_icon,
                   l.campus_id, cp.campus_name, cp.code AS campus_code,
                   loc.location_name, loc.building,
                   l.image_url, l.date_lost AS item_date, l.status, l.created_at
            FROM lost_items l
            JOIN categories c ON l.category_id = c.category_id
            JOIN campuses cp ON l.campus_id = cp.campus_id
            JOIN locations loc ON l.location_id = loc.location_id AND l.campus_id = loc.campus_id
            WHERE l.status IN ('ACTIVE', 'MATCHED')
        """
        if campus_id:
            q_lost += " AND l.campus_id = %s"
            params.append(int(campus_id))
        queries.append(q_lost)

    if not queries:
        return jsonify({"items": []})

    union_sql = " UNION ALL ".join(queries)
    final_sql = f"""
        SELECT * FROM ({union_sql}) AS combined
        ORDER BY (image_url IS NOT NULL AND image_url != '') DESC, created_at DESC
        LIMIT %s
    """
    params.append(limit)
    items = query_all(final_sql, tuple(params))
    return jsonify({"items": items})


