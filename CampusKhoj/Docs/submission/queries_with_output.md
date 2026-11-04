# DBMS Course Demonstration Queries & Live Execution Outputs

**Database**: `campuskhoj_zero` (MySQL 8.0 on port 3307)  
**Executed**: All queries executed against live seeded database state.  

---

## QUERY 1: Multi-Table INNER & LEFT JOIN

*Demonstrates: 5-table join linking found items, categories, campuses, locations, and any active claims with claimant details.*

### SQL Statement

```sql
SELECT
    fi.found_id,
    fi.item_name,
    c.category_name,
    cp.campus_name,
    loc.location_name,
    loc.building,
    fi.date_found,
    fi.custody,
    fi.status AS item_status,
    cl.claim_id,
    cl.claim_status,
    u.prn AS claimant_prn,
    u.name AS claimant_name
FROM found_items fi
JOIN categories c ON fi.category_id = c.category_id
JOIN campuses cp ON fi.campus_id = cp.campus_id
JOIN locations loc ON fi.location_id = loc.location_id AND fi.campus_id = loc.campus_id
LEFT JOIN claims cl ON fi.found_id = cl.found_id AND cl.claim_status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED')
LEFT JOIN users u ON cl.claimant_id = u.user_id
ORDER BY fi.date_found DESC;
```

### Live Execution Output (2 row(s) returned)

| found_id | item_name | category_name | campus_name | location_name | building | date_found | custody | item_status | claim_id | claim_status | claimant_prn | claimant_name |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Dell Laptop with Charger | Electronics | Kondhwa Campus | Central Library Kondhwa | Main Building | 2026-11-03 | AT_DESK | MATCHED | 1 | UNDER_REVIEW | 1251150353 | Aarav Sharma |
| 2 | Titan Analogue Watch | Clothing & Accessories | Bibwewadi Campus | Building 3 | Building 3 | 2026-11-02 | AT_DESK | CLAIMED | 2 | APPROVED | 1251030471 | Ananya Kulkarni |

---

## QUERY 2: GROUP BY with HAVING Clause

*Demonstrates: Identifying high-risk campus locations that have had at least 2 reported loss incidents, calculating resolution percentage.*

### SQL Statement

```sql
SELECT
    loc.campus_id,
    cp.campus_name,
    loc.location_name,
    loc.building,
    COUNT(l.lost_id) AS total_lost_reports,
    SUM(CASE WHEN l.status = 'RETURNED' THEN 1 ELSE 0 END) AS returned_count,
    ROUND(
        (SUM(CASE WHEN l.status = 'RETURNED' THEN 1 ELSE 0 END) * 100.0) / COUNT(l.lost_id),
        1
    ) AS return_rate_pct
FROM locations loc
JOIN campuses cp ON loc.campus_id = cp.campus_id
JOIN lost_items l ON loc.location_id = l.location_id AND loc.campus_id = l.campus_id
GROUP BY loc.campus_id, cp.campus_name, loc.location_id, loc.location_name, loc.building
HAVING total_lost_reports >= 2
ORDER BY total_lost_reports DESC;
```

### Live Execution Output (0 row(s) returned)

*No rows returned for current dataset filters.*

---

## QUERY 3: Correlated Subquery

*Demonstrates: Finding lost items that have at least one potential match suggestion with a high similarity score (>= 75).*

### SQL Statement

```sql
SELECT
    l.lost_id,
    l.item_name,
    l.color,
    l.date_lost,
    cp.campus_name,
    (
        SELECT MAX(ms.score)
        FROM match_suggestions ms
        WHERE ms.lost_id = l.lost_id
    ) AS highest_match_score,
    (
        SELECT fi.item_name
        FROM match_suggestions ms
        JOIN found_items fi ON ms.found_id = fi.found_id
        WHERE ms.lost_id = l.lost_id
        ORDER BY ms.score DESC
        LIMIT 1
    ) AS best_matched_found_item
FROM lost_items l
JOIN campuses cp ON l.campus_id = cp.campus_id
WHERE EXISTS (
    SELECT 1
    FROM match_suggestions ms
    WHERE ms.lost_id = l.lost_id
      AND ms.score >= 75
);
```

### Live Execution Output (1 row(s) returned)

| lost_id | item_name | color | date_lost | campus_name | highest_match_score | best_matched_found_item |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Dell Inspiron 15 Laptop | Black | 2026-11-02 | Kondhwa Campus | 82 | Dell Laptop with Charger |

---

## QUERY 4: FULLTEXT Search with Boolean Operators

*Demonstrates: MySQL FULLTEXT natural language and boolean matching across indexed columns (item_name, description, brand).*

### SQL Statement

```sql
SELECT
    lost_id,
    item_name,
    brand,
    description,
    MATCH(item_name, description, brand) AGAINST('+calculator +casio' IN BOOLEAN MODE) AS relevance
FROM lost_items
WHERE MATCH(item_name, description, brand) AGAINST('+calculator +casio' IN BOOLEAN MODE)
ORDER BY relevance DESC;
```

### Live Execution Output (0 row(s) returned)

*No rows returned for current dataset filters.*

---

## QUERY 5: JSON Extraction & Aggregation

*Demonstrates: Querying match breakdown components stored in JSON datatype.*

### SQL Statement

```sql
SELECT
    ms.match_id,
    ms.lost_id,
    l.item_name AS lost_name,
    ms.found_id,
    f.item_name AS found_name,
    ms.score AS total_score,
    JSON_UNQUOTE(JSON_EXTRACT(ms.breakdown, '$.category')) AS category_points,
    JSON_UNQUOTE(JSON_EXTRACT(ms.breakdown, '$.name')) AS name_similarity_points,
    JSON_UNQUOTE(JSON_EXTRACT(ms.breakdown, '$.location')) AS location_points
FROM match_suggestions ms
JOIN lost_items l ON ms.lost_id = l.lost_id
JOIN found_items f ON ms.found_id = f.found_id
WHERE ms.score >= 50
ORDER BY ms.score DESC;
```

### Live Execution Output (1 row(s) returned)

| match_id | lost_id | lost_name | found_id | found_name | total_score | category_points | name_similarity_points | location_points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | Dell Inspiron 15 Laptop | 1 | Dell Laptop with Charger | 82 | 30 | 12 | 20 |

---

## QUERY 6: EXPLAIN Plan Analysis for Viva Demo

*Demonstrates: Proving indexed lookups avoid full table scans on campus listings.*

### SQL Statement

```sql
EXPLAIN
SELECT l.lost_id, l.item_name, l.status
FROM lost_items l
WHERE l.campus_id = 1
  AND l.status = 'ACTIVE'
  AND l.category_id = 1
  AND l.date_lost >= '2026-01-01';
```

### Live Execution Output (1 row(s) returned)

| id | select_type | table | partitions | type | possible_keys | key | key_len | ref | rows | filtered | Extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | SIMPLE | l | NULL | ref | fk_lost_category,idx_lost_query | fk_lost_category | 2 | const | 1 | 16.67 | Using where |

---

