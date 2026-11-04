# Database Query Performance & EXPLAIN Plan Analysis

**Project**: CampusKhoj — Multi-Campus Lost & Found System  
**Database**: MySQL 8.0.46 Community Server  
**Environment**: `campuskhoj_demo` (Live Port 3307)  
**Evaluated**: 5 Heaviest Production Queries  

---

## Executive Summary

To guarantee responsive performance under concurrent college usage, the 5 heaviest read/write patterns in CampusKhoj were benchmarked and profiled using MySQL 8.0's execution optimizer (`EXPLAIN` and `EXPLAIN FORMAT=TREE`).

| # | Query Pattern | Main Table | Index Utilized | Scan Type | Rows Examined | Optimization Status |
|---|---------------|------------|----------------|-----------|---------------|---------------------|
| **1** | Filtered Lost Items Search | `lost_items` | `idx_lost_query` | Range Scan | 1 | Optimal (Composite Index) |
| **2** | Public Found Catalog Catalog | `found_items` | `idx_found_query` | Ref Lookup | 5 | Optimal (Composite Index) |
| **3** | Match Engine Window Discovery | `found_items` | `idx_found_query` | Range Scan | 1 | Optimal (Date Range Scan) |
| **4** | Activity Timeline Reconstruction | `item_events` | `idx_timeline` | Ref Lookup | 1 | Optimal (Composite Prefix) |
| **5** | Admin Multi-Campus Claim Pipeline | `claims` | `idx_claims_search` | Hash Join / Scan | 19 | Recommended Index Tuning |

---

## Detailed Query Profiles & Execution Plans

### 1. Filtered Lost Items Search & Pagination

Used by student and admin portals for browsing active/all lost items with multi-column filtering (campus, category, date range, status) and descending pagination.

```sql
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
```

#### MySQL 8 Tabular Plan
```
+-------+--------+----------------+---------+---------+----------------------------------------------------+
| table | type   | key            | key_len | rows    | Extra                                              |
+-------+--------+----------------+---------+---------+----------------------------------------------------+
| c     | const  | PRIMARY        | 2       | 1       | NULL                                               |
| cmp   | const  | PRIMARY        | 1       | 1       | NULL                                               |
| l     | range  | idx_lost_query | 7       | 1       | Using index condition; Backward index scan         |
| loc   | eq_ref | PRIMARY        | 4       | 1       | NULL                                               |
+-------+--------+----------------+---------+---------+----------------------------------------------------+
```

#### MySQL 8 Tree Plan
```
-> Limit: 20 row(s)  (cost=1.06 rows=1)
    -> Nested loop inner join  (cost=1.06 rows=1)
        -> Index range scan on l using idx_lost_query over (campus_id = 1 AND status = 'ACTIVE' AND category_id = 1 AND '2026-01-01' <= date_lost) (reverse), with index condition: ((l.category_id = 1) and (l.campus_id = 1) and (l.`status` = 'ACTIVE') and (l.date_lost >= DATE'2026-01-01'))  (cost=0.71 rows=1)
        -> Single-row index lookup on loc using PRIMARY (location_id=l.location_id)  (cost=0.35 rows=1)
```

- **Analysis**: The 4-column composite index `idx_lost_query (campus_id, status, category_id, date_lost)` satisfies equality matches on the first three columns and executes a bounded range scan on `date_lost`. The engine utilizes a **backward index scan** to satisfy `ORDER BY date_lost DESC` without requiring an in-memory `filesort`. Cost: **1.06**.

---

### 2. Filtered Found Items Search (Public Catalog)

Public view of found items preventing private detail leakage, filtering by campus and category with pagination.

```sql
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
```

#### MySQL 8 Tabular Plan
```
+-------+--------+----------------+---------+---------+-----------------+
| table | type   | key            | key_len | rows    | Extra           |
+-------+--------+----------------+---------+---------+-----------------+
| cmp   | const  | PRIMARY        | 1       | 1       | Using filesort  |
| f     | ref    | idx_found_query| 2       | 5       | NULL            |
| c     | eq_ref | PRIMARY        | 2       | 1       | NULL            |
| loc   | eq_ref | PRIMARY        | 4       | 1       | NULL            |
+-------+--------+----------------+---------+---------+-----------------+
```

#### MySQL 8 Tree Plan
```
-> Limit: 20 row(s)  (cost=4.5 rows=5)
    -> Nested loop inner join  (cost=4.5 rows=5)
        -> Nested loop inner join  (cost=2.75 rows=5)
            -> Sort: f.date_found DESC, f.found_id DESC  (cost=1 rows=5)
                -> Index lookup on f using idx_found_query (campus_id=1, status='ACTIVE')  (cost=1 rows=5)
            -> Single-row index lookup on c using PRIMARY (category_id=f.category_id)  (cost=0.27 rows=1)
        -> Single-row index lookup on loc using PRIMARY (location_id=f.location_id)  (cost=0.27 rows=1)
```

- **Analysis**: Uses the prefix `(campus_id, status)` of composite index `idx_found_query`. Since `category_id` was not filtered, `filesort` orders the 5 returned candidates before limit. Join to lookup tables `categories` and `locations` uses primary key `eq_ref` (single-row index lookup). Total cost: **4.5**.

---

### 3. Match Engine Candidate Pool Discovery

Core scoring algorithm query scanning active found items eligible to pair with a newly reported lost item within a 14-day temporal window.

```sql
SELECT f.found_id, f.campus_id, f.category_id, f.location_id,
       f.date_found, f.item_name, f.description, f.brand, f.color
FROM found_items f
WHERE f.campus_id = 1
  AND f.category_id = 1
  AND f.status = 'ACTIVE'
  AND f.date_found BETWEEN '2026-10-01' AND '2026-10-29';
```

#### MySQL 8 Tabular Plan
```
+-------+-------+----------------+---------+------+-----------------------+
| table | type  | key            | key_len | rows | Extra                 |
+-------+-------+----------------+---------+------+-----------------------+
| f     | range | idx_found_query| 7       | 1    | Using index condition |
+-------+-------+----------------+---------+------+-----------------------+
```

#### MySQL 8 Tree Plan
```
-> Index range scan on f using idx_found_query over (campus_id = 1 AND status = 'ACTIVE' AND category_id = 1 AND '2026-10-01' <= date_found <= '2026-10-29'), with index condition: ((f.category_id = 1) and (f.campus_id = 1) and (f.`status` = 'ACTIVE') and (f.date_found between '2026-10-01' and '2026-10-29'))  (cost=0.71 rows=1)
```

- **Analysis**: High-performance index range scan using Index Condition Pushdown (ICP). All 4 filter attributes match the index columns in exact order, filtering the search set down to candidate rows directly at the storage engine layer. Cost: **0.71**.

---

### 4. Activity Timeline Sequence Reconstruction

Auditing and visual stepper reconstruction for lost/found items with user role attribution and chronological ordering.

```sql
SELECT e.event_id, e.event_type, e.title, e.description, e.created_at,
       e.actor_id, r.role_name AS actor_role, e.is_public
FROM item_events e
LEFT JOIN users u ON e.actor_id = u.user_id
LEFT JOIN roles r ON u.role_id = r.role_id
WHERE e.item_type = 'LOST'
  AND e.item_id = 1
ORDER BY e.created_at ASC, e.event_id ASC;
```

#### MySQL 8 Tabular Plan
```
+-------+--------+--------------+---------+------+-------+
| table | type   | key          | key_len | rows | Extra |
+-------+--------+--------------+---------+------+-------+
| e     | ref    | idx_timeline | 5       | 1    | NULL  |
| u     | eq_ref | PRIMARY      | 4       | 1    | NULL  |
| r     | eq_ref | PRIMARY      | 1       | 1    | NULL  |
+-------+--------+--------------+---------+------+-------+
```

#### MySQL 8 Tree Plan
```
-> Nested loop left join  (cost=1.05 rows=1)
    -> Nested loop left join  (cost=0.7 rows=1)
        -> Index lookup on e using idx_timeline (item_type='LOST', item_id=1)  (cost=0.35 rows=1)
        -> Single-row index lookup on u using PRIMARY (user_id=e.actor_id)  (cost=0.35 rows=1)
    -> Single-row index lookup on r using PRIMARY (role_id=u.role_id)  (cost=0.35 rows=1)
```

- **Analysis**: Polymorphic lookup using `idx_timeline (item_type, item_id, created_at)`. Because the index already contains `created_at` in ASC order, MySQL avoids a filesort pass. Subsequent joins to `users` and `roles` execute via clustered primary key lookups (`eq_ref`). Total cost: **1.05**.

---

### 5. Admin Multi-Campus Claim Pipeline & Verification Review

Admin table query reporting claim pipeline status, claimant details, and physical item custody across both campuses.

```sql
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
```

#### MySQL 8 Tabular Plan
```
+-------+--------+-------------------+---------+------+----------------------------------------------------+
| table | type   | key               | key_len | rows | Extra                                              |
+-------+--------+-------------------+---------+------+----------------------------------------------------+
| cmp   | index  | campus_name       | 162     | 2    | Using index; Using temporary; Using filesort       |
| c     | ALL    | NULL              | NULL    | 19   | Using where; Using join buffer (hash join)         |
| f     | eq_ref | PRIMARY           | 4       | 1    | Using where                                        |
| u     | eq_ref | PRIMARY           | 4       | 1    | NULL                                               |
+-------+--------+-------------------+---------+------+----------------------------------------------------+
```

#### MySQL 8 Tree Plan
```
-> Limit: 50 row(s)
    -> Sort: c.submitted_at DESC, limit input to 50 row(s) per chunk
        -> Stream results  (cost=6.08 rows=1.76)
            -> Nested loop inner join  (cost=6.08 rows=1.76)
                -> Nested loop inner join  (cost=5.24 rows=1.76)
                    -> Inner hash join (no condition)  (cost=3.24 rows=4.22)
                        -> Filter: (c.claim_status in ('PENDING','UNDER_REVIEW'))  (cost=1.08 rows=6.33)
                            -> Table scan on c  (cost=1.08 rows=19)
                        -> Hash
                            -> Index scan on cmp using campus_name  (cost=0.45 rows=2)
                    -> Filter: (f.campus_id = cmp.campus_id)  (cost=0.128 rows=0.417)
                        -> Single-row index lookup on f using PRIMARY (found_id=c.found_id)  (cost=0.128 rows=1)
                -> Single-row index lookup on u using PRIMARY (user_id=c.claimant_id)  (cost=0.144 rows=1)
```

- **Analysis & Tuning Recommendation**:
  - The current index on `claims` is `idx_claims_search (campus_id, claim_status, submitted_at)`.
  - When the Super-Admin queries pending claims across *all* campuses simultaneously (without specifying a single `campus_id`), MySQL cannot use the leading column of `idx_claims_search`, resulting in a table scan on `claims` (19 rows) and a hash join.
  - **Proposed Index Optimization**: Add a secondary index:
    ```sql
    CREATE INDEX idx_claims_status_date ON claims (claim_status, submitted_at);
    ```
    This eliminates the table scan and hash join for global admin views. For campus-specific admin views (`campus_id = 1`), `idx_claims_search` operates as an index ref lookup.

---

### 6. Full-Text Search Query Analysis & Wildcard Sanitization

Used across the student portal and administrative console for keyword search on items (`q` parameter).

#### 6.1 Multi-Word Fulltext Search (3+ Character Tokens)
Queries containing words with 3 or more characters utilize MySQL InnoDB FULLTEXT indexes in Boolean Mode:
```sql
EXPLAIN SELECT found_id, item_name, description, brand
FROM found_items f
WHERE MATCH(f.item_name, f.description, f.brand) AGAINST('+Dell* +Inspiron*' IN BOOLEAN MODE);
```

#### MySQL 8 Tabular Plan
```
+-------+----------+-----------------+---------+---------+------+----------+------------------------------------+
| table | type     | key             | key_len | ref     | rows | filtered | Extra                              |
+-------+----------+-----------------+---------+---------+------+----------+------------------------------------+
| f     | fulltext | ft_found_search | 0       | const   | 1    | 100.00   | Using where; Ft_hints: no_ranking  |
+-------+----------+-----------------+---------+---------+------+----------+------------------------------------+
```

#### MySQL 8 Tree Plan
```
-> Filter: (match f.item_name,f.description,f.brand against ('+Dell* +Inspiron*' in boolean mode))  (cost=0.35 rows=1)
    -> Full-text index scan on f using ft_found_search (item_name,description,brand)  (cost=0.35 rows=1)
```

- **Analysis**: The optimizer selects `ft_found_search (item_name, description, brand)` with scan type `fulltext`. InnoDB evaluates the inverted index using word prefixes without full table scanning.

#### 6.2 Short Query & Wildcard Sanitization Fallback (< 3 Characters / %, _)
For queries shorter than InnoDB's minimum token size (e.g. 2-character brands like "HP" or "MI") or queries containing search wildcards (`%`, `_`), CampusKhoj automatically routes the query to an escaped SQL `LIKE` clause with explicit `ESCAPE '\\'`:
```sql
EXPLAIN SELECT found_id, item_name, description, brand
FROM found_items f
WHERE (LOWER(f.item_name) LIKE '%\\%%' ESCAPE '\\' 
    OR LOWER(f.description) LIKE '%\\%%' ESCAPE '\\' 
    OR LOWER(COALESCE(f.brand, '')) LIKE '%\\%%' ESCAPE '\\');
```

- **Security & Integrity Guarantee**: Literal `%` and `_` inputs are escaped as `\%` and `\_`, preventing attackers or users from triggering catastrophic unbounded wildcard scans or matching all records inadvertently.


