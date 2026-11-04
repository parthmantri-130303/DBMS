import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from backend.config import config

def run_explain():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)

    queries = [
        {
            "name": "Query 1: Filtered Lost Items Search & Pagination",
            "desc": "Used by student and admin portals for browsing active/all lost items with multi-column filtering (campus, category, date range, status) and pagination.",
            "sql": """
                SELECT l.lost_id, l.item_name, l.description, l.category_id, c.category_name,
                       l.campus_id, cmp.campus_name, l.location_id, loc.location_name,
                       l.date_lost, l.time_lost, l.status, l.created_at
                FROM lost_items l
                JOIN categories c ON l.category_id = c.category_id
                JOIN campuses cmp ON l.campus_id = cmp.campus_id
                JOIN locations loc ON l.location_id = loc.location_id
                WHERE l.campus_id = 1
                  AND l.category_id = 1
                  AND l.status = 'ACTIVE'
                  AND l.date_lost >= '2026-01-01'
                ORDER BY l.date_lost DESC, l.lost_id DESC
                LIMIT 20 OFFSET 0;
            """
        },
        {
            "name": "Query 2: Filtered Found Items Search (Public Catalog)",
            "desc": "Public view of found items preventing private detail leakage, filtering by campus and category with pagination.",
            "sql": """
                SELECT f.found_id, f.item_name, f.description, f.category_id, c.category_name,
                       f.campus_id, cmp.campus_name, f.location_id, loc.location_name,
                       f.date_found, f.time_found, f.status, f.created_at
                FROM found_items f
                JOIN categories c ON f.category_id = c.category_id
                JOIN campuses cmp ON f.campus_id = cmp.campus_id
                JOIN locations loc ON f.location_id = loc.location_id
                WHERE f.campus_id = 1
                  AND f.status = 'ACTIVE'
                ORDER BY f.date_found DESC, f.found_id DESC
                LIMIT 20 OFFSET 0;
            """
        },
        {
            "name": "Query 3: Match Engine Candidate Pool Discovery",
            "desc": "Core scoring algorithm query scanning active found items eligible to pair with a newly reported lost item within 14-day temporal window.",
            "sql": """
                SELECT f.found_id, f.campus_id, f.category_id, f.location_id,
                       f.date_found, f.item_name, f.description, f.brand, f.color
                FROM found_items f
                WHERE f.campus_id = 1
                  AND f.category_id = 1
                  AND f.status = 'ACTIVE'
                  AND f.date_found BETWEEN '2026-10-01' AND '2026-10-29';
            """
        },
        {
            "name": "Query 4: Timeline Event Sequence Reconstruction",
            "desc": "Auditing and visual stepper reconstruction for lost/found items with user role attribution and chronological ordering.",
            "sql": """
                SELECT e.event_id, e.event_type, e.title, e.description, e.created_at,
                       e.actor_id, r.role_name AS actor_role, e.is_public
                FROM item_events e
                LEFT JOIN users u ON e.actor_id = u.user_id
                LEFT JOIN roles r ON u.role_id = r.role_id
                WHERE e.item_type = 'LOST'
                  AND e.item_id = 1
                ORDER BY e.created_at ASC, e.event_id ASC;
            """
        },
        {
            "name": "Query 5: Admin All-Items Unified View & Claim Status Aggregation",
            "desc": "Admin table query reporting claim pipeline status, claimant details, and physical item custody across both campuses.",
            "sql": """
                SELECT c.claim_id, c.found_id, f.item_name, c.claimant_id,
                       u.prn, u.name, c.claim_status,
                       c.submitted_at, f.campus_id, cmp.campus_name,
                       f.storage_location
                FROM claims c
                JOIN found_items f ON c.found_id = f.found_id
                JOIN campuses cmp ON f.campus_id = cmp.campus_id
                JOIN users u ON c.claimant_id = u.user_id
                WHERE c.claim_status IN ('PENDING', 'UNDER_REVIEW')
                ORDER BY c.submitted_at DESC
                LIMIT 50;
            """
        }
    ]

    results = []
    for q in queries:
        clean_sql = q["sql"].strip()
        # Traditional tabular EXPLAIN
        cursor.execute(f"EXPLAIN {clean_sql}")
        rows = cursor.fetchall()
        
        # MySQL 8 FORMAT=TREE EXPLAIN
        cursor.execute(f"EXPLAIN FORMAT=TREE {clean_sql}")
        tree_row = cursor.fetchone()
        tree_text = tree_row.get("EXPLAIN", "") if tree_row else ""

        results.append({
            "name": q["name"],
            "desc": q["desc"],
            "sql": clean_sql,
            "table_plan": rows,
            "tree_plan": tree_text
        })

    cursor.close()
    conn.close()
    return results

if __name__ == '__main__':
    plans = run_explain()
    for p in plans:
        print("="*60)
        print(p["name"])
        print("="*60)
        print("TABLE EXPLAIN:")
        for r in p["table_plan"]:
            print(f"  table: {r.get('table')} | type: {r.get('type')} | key: {r.get('key')} | rows: {r.get('rows')} | Extra: {r.get('Extra')}")
        print("\nTREE PLAN:")
        print(p["tree_plan"])
        print("\n")
