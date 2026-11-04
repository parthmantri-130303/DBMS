# CampusKhoj — 30 Comprehensive DBMS Viva Questions & Answers

**Project**: CampusKhoj — Two-Campus Lost & Found System  
**Database**: MySQL 8.0.46 Community Edition (InnoDB)  
**Backend**: Python Flask (Raw Parameterized SQL, No ORM)  

---

## Category 1: Schema Design & Relational Constraints

### Q1: Why does CampusKhoj use a composite foreign key on `(location_id, campus_id)` instead of a simple foreign key on `location_id` alone?
**Answer**:
A simple FK on `location_id` ensures that a referenced location exists, but it *cannot* ensure that the location belongs to the same campus as the item. In a multi-campus system (Kondhwa vs Bibwewadi), this would allow an anomaly where an item lost in Kondhwa is assigned a Bibwewadi classroom location. By creating a composite unique key `UNIQUE (location_id, campus_id)` on `locations` and referencing it via `FOREIGN KEY (location_id, campus_id)` in both `lost_items` and `found_items`, the MySQL InnoDB storage engine enforces geographic consistency at the relational layer without needing application triggers.

### Q2: How does the stored generated column `active_key` guarantee exactly one active claim per student per found item?
**Answer**:
MySQL does not support partial unique indexes (e.g. `CREATE UNIQUE INDEX ... WHERE status IN ('PENDING', 'APPROVED')`). To solve this, `claims` defines:
```sql
active_key TINYINT GENERATED ALWAYS AS (
    CASE WHEN claim_status IN ('PENDING','UNDER_REVIEW','APPROVED') THEN 1 ELSE NULL END
) STORED,
CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)
```
When a claim is active, `active_key = 1`. A second active claim by the same student produces `(found_id, claimant_id, 1)`, triggering a duplicate key error (MySQL error 1062). When a claim is completed or rejected, `active_key` evaluates to `NULL`. Since the SQL standard defines that `NULL != NULL` in unique constraints, students can submit future claims if an item is re-opened, while maintaining an immutable historical audit trail.

### Q3: Why is `active_key` defined as `STORED` rather than `VIRTUAL`?
**Answer**:
In MySQL 8, unique constraints and secondary indexes on generated columns can be `STORED` or `VIRTUAL`. However, `STORED` generated columns are computed during `INSERT` and `UPDATE` and physically persisted on disk with the clustered index. This eliminates CPU re-calculation overhead during high-frequency index lookup scans and guarantees immediate ACID consistency during serialized concurrent claim submissions.

### Q4: Explain the `chk_user_identity` constraint on the `users` table.
**Answer**:
CampusKhoj maintains a unified `users` table for both students and staff, but enforces mutually exclusive identities:
```sql
CONSTRAINT chk_user_identity CHECK ((prn IS NOT NULL) <> (staff_username IS NOT NULL))
```
The `<>` (exclusive OR) operator requires that either `prn` is provided (for students) or `staff_username` is provided (for staff/security), but never both and never neither. Furthermore, students must reference the verified whitelist in `prn_registry(prn)`.

### Q5: How is polymorphic behavior implemented in `item_events`?
**Answer**:
The `item_events` table models chronological timelines across three distinct entity types (Lost items, Found items, and Claims). It uses a polymorphic association pattern:
```sql
item_type ENUM('LOST','FOUND','CLAIM') NOT NULL,
item_id INT NOT NULL,
INDEX idx_timeline (item_type, item_id, created_at)
```
The composite index `idx_timeline` ensures that fetching the event history for any item is a high-speed `ref` index lookup ordered by timestamp.

---

## Category 2: Normalization & Functional Dependencies

### Q6: What normal form does the CampusKhoj schema achieve?
**Answer**:
All primary relational entities (`campuses`, `roles`, `categories`, `users`, `claim_verifications`, `claim_messages`, `item_events`, `message_outbox`, `notifications`, `audit_logs`, `login_attempts`) satisfy **Boyce-Codd Normal Form (BCNF)** across the 17 tables. Tables `lost_items`, `found_items`, and `claims` satisfy **3NF** with intentional, documented denormalizations.

### Q7: If `location_id -> campus_id`, why is `campus_id` stored in `lost_items` and `found_items`? Doesn't this introduce a transitive dependency?
**Answer**:
Yes, in pure mathematical normalization, $\text{item\_id} \rightarrow \text{location\_id} \rightarrow \text{campus\_id}$ is a transitive dependency. However, this is an **intentional engineering denormalization**. SQL foreign keys cannot validate multi-hop relationships. Without storing `campus_id` directly on the item, the database cannot enforce the composite foreign key constraint `(location_id, campus_id) REFERENCES locations(location_id, campus_id)`. The slight redundancy is strictly controlled and guarantees relational integrity.

### Q8: Identify the candidate keys of the `locations` table.
**Answer**:
1. $\{ \text{location\_id} \}$ (Surrogate Primary Key)
2. $\{ \text{campus\_id}, \text{location\_name} \}$ (Alternate natural key: no two rooms on the same campus have the same name)
3. $\{ \text{location\_id}, \text{campus\_id} \}$ (Composite Superkey: unique target for child composite FKs)

### Q9: Why was the PRN registry normalized into its own table rather than putting student lists directly into `users`?
**Answer**:
The college provides pre-authorized student enrolment lists (582 Bibwewadi, 513 Kondhwa) before students ever log in. Normalizing `prn_registry` as an independent entity separates administrative whitelist authorization from active user accounts. An unactivated PRN consumes only 10 bytes of storage in `prn_registry` without generating bloated default rows in `users`.

### Q10: How does the schema prevent multi-valued dependencies (4NF)?
**Answer**:
In 4NF, no table may contain two or more independent multi-valued facts about an entity. In CampusKhoj:
- An item's status history is separated into `item_events` rather than an array of timestamps.
- Verification questions and answers are stored in `claim_verifications` rows rather than an unnormalized table of claimant dialogues.
- Multi-campus access is separated into distinct relations.

---

## Category 3: Indexing, Query Optimization & Execution Plans

### Q11: Explain the structure and purpose of `idx_lost_query (campus_id, status, category_id, date_lost)`.
**Answer**:
This 4-column composite index follows the "Equality First, Range Later" indexing rule:
1. `campus_id` (Equality: 1 or 2)
2. `status` (Equality: 'ACTIVE', 'MATCHED', etc.)
3. `category_id` (Equality: Electronics, Books, etc.)
4. `date_lost` (Range / Sort: `>= DATE` or `ORDER BY date_lost DESC`)
Because MySQL B-tree indexes are sorted, equality matches narrow the search space to a contiguous range, and the final column satisfies both date range filtering and sorting without an in-memory `filesort`.

### Q12: In the EXPLAIN plan for Query 1, what does "Backward index scan" mean?
**Answer**:
The query specifies `ORDER BY date_lost DESC`. In MySQL 8, InnoDB B-tree indexes can be traversed in reverse direction (high keys to low keys). A backward index scan means MySQL reads the index leaf pages in reverse, returning rows in descending order directly to the client without buffering or sorting in temporary tables.

### Q13: What is Index Condition Pushdown (ICP) and where does CampusKhoj utilize it?
**Answer**:
ICP is an optimization where the storage engine (InnoDB) evaluates `WHERE` filter conditions directly on index columns before fetching the full clustered row from disk. In Query 3 (Match Candidate Discovery), `EXPLAIN FORMAT=TREE` shows `Using index condition`. InnoDB filters non-matching dates and categories within the index buffer, dramatically reducing disk I/O and buffer pool churn.

### Q14: Why does Query 5 (Global Admin Claim Pipeline) use a hash join instead of an index lookup?
**Answer**:
The index on claims is `idx_claims_search (campus_id, claim_status, submitted_at)`. When the Super-Admin queries pending claims across *all* campuses, the query omits `campus_id`. Because `campus_id` is the leading prefix column of the composite index, MySQL cannot use a B-tree range scan on the remaining columns. It defaults to a table scan and builds a hash table in memory (`Inner hash join`). To optimize this, a secondary index `(claim_status, submitted_at)` should be added for global views.

### Q15: How does FULLTEXT indexing work in CampusKhoj compared to standard `LIKE '%keyword%'`?
**Answer**:
`LIKE '%keyword%'` begins with a wildcard, which completely disables B-tree indexes and forces a full table scan ($O(N)$). CampusKhoj creates:
```sql
FULLTEXT INDEX ft_lost_search (item_name, description, brand)
```
MySQL builds an inverted index that tokenizes text into words. `MATCH(...) AGAINST('+calculator +casio' IN BOOLEAN MODE)` performs an inverted index lookup in $O(\log N)$, matching only rows containing both tokens and computing relevance scores.

---

## Category 4: Transactions, Concurrency & Stored Procedures

### Q16: What happens during `sp_approve_claim` and why is it encapsulated in a stored procedure?
**Answer**:
Claim approval is a critical multi-step business transaction:
1. Marks the selected claim as `APPROVED` and records `reviewed_at` and `reviewed_by`.
2. Marks the referenced found item as `CLAIMED`.
3. Auto-rejects all competing claims on that found item (`claim_status = 'REJECTED'`, `reject_reason = 'Another claim was approved'`).
4. Updates any linked lost item to `CLAIMED`.
5. Emits events in `item_events` and writes to `audit_logs`.
Encapsulating this in `sp_approve_claim` with an explicit `START TRANSACTION ... COMMIT` ensures ACID atomicity. If a power failure or error occurs halfway through, the entire sequence rolls back, preventing orphaned claims or lost items.

### Q17: What MySQL isolation level is used and why?
**Answer**:
CampusKhoj runs on InnoDB's default **REPEATABLE READ** isolation level. It uses multi-version concurrency control (MVCC) and Next-Key Locking (record locks + gap locks) to prevent dirty reads, non-repeatable reads, and phantom reads, ensuring that concurrent student claims on the same item are serialized correctly.

### Q18: What is a deadlock and how does CampusKhoj prevent it?
**Answer**:
A deadlock occurs when two concurrent transactions hold locks that the other needs (e.g. Transaction A locks Item 1 and waits for Claim 2; Transaction B locks Claim 2 and waits for Item 1). CampusKhoj prevents deadlocks by enforcing **deterministic lock ordering**: all multi-row updates and transactions acquire row locks in strict primary key ascending order (`found_id ASC`, `claim_id ASC`).

### Q19: How did the integration test suite prove ACID rollback on `sp_approve_claim`?
**Answer**:
In `test_live_mysql.py` (`test_c_sp_approve_claim_execution_and_rollback`), the test starts a transaction, calls `sp_approve_claim`, verifies that competing claims are transitioned to `REJECTED`, and then explicitly issues `conn.rollback()`. It then verifies on the live MySQL server that the found item reverted to `ACTIVE`, the claim reverted to `PENDING`, and competing claims remained `PENDING`, proving zero partial mutation leakage.

### Q20: What triggers exist in the CampusKhoj database?
**Answer**:
1. `trg_claim_status_audit`: `AFTER UPDATE ON claims` writes an automated row to `audit_logs` whenever `claim_status` changes, logging old and new status and timestamps.
2. `trg_password_change_audit`: `AFTER UPDATE ON users` logs password change events and automatically resets `must_change_password = 0`.
3. `trg_found_custody_event`: `AFTER UPDATE ON found_items` creates an `item_events` row when custody transfers from finder to security desk.

---

## Category 5: Security, Authentication & Web Architecture

### Q21: How are passwords secured in the database?
**Answer**:
Passwords are encrypted using **bcrypt** with a salt work factor of 12. Bcrypt incorporates automatic salting and key-stretching, making rainbow table attacks and GPU-accelerated hash cracking infeasible. Raw passwords are never written to disk, session files, or log streams.

### Q22: What is the first-login enclave workflow?
**Answer**:
When an imported student logs in for the first time:
1. The student submits their 10-digit PRN as both username and password.
2. The backend confirms `password_hash IS NULL` and verifies the PRN against `prn_registry`.
3. The API issues a JWT with restricted claim `scope: "pwd_change"`.
4. All protected API endpoints (`/campuses`, `/lost`, `/found`, `/claims`) reject tokens with this scope (HTTP 403 `PASSWORD_CHANGE_REQUIRED`).
5. The student portal enforces client-side redirection to `change-password.html`, locking navigation until a compliant password and profile are submitted.

### Q23: How does the system prevent SQL injection without an ORM?
**Answer**:
CampusKhoj does not use an ORM (like SQLAlchemy), adhering to course requirements for raw SQL. It prevents SQL injection by strictly using **parameterized prepared queries** with MySQL Connector's placeholder syntax (`%s`). User inputs are passed as separate data tuples to `cursor.execute(sql, params)`. The database engine compiles the SQL query structure prior to binding parameter values, preventing SQL code execution from user input.

### Q24: What is Insecure Direct Object Reference (IDOR) and how is it prevented?
**Answer**:
IDOR occurs when a user accesses or modifies another user's record by changing an ID in the URL (e.g. `PATCH /api/v1/lost/15`). CampusKhoj prevents IDOR by extracting the authenticated `user_id` and `role` directly from the cryptographically signed JWT token:
```python
if item["user_id"] != caller_user_id and caller_role not in ("CAMPUS_ADMIN", "SUPER_ADMIN"):
    raise ForbiddenError("You cannot modify another user's report")
```
Tested and verified in test case `test_t24_idor_prevention`.

### Q25: How is privacy protected when unauthenticated students browse found items?
**Answer**:
In `GET /api/v1/found` and `GET /api/v1/found/<id>`, the serializer explicitly excludes sensitive columns:
- `private_details` (e.g., serial numbers, wallpaper description)
- `storage_location` (e.g., Locker 4B behind desk)
- `reporter_prn` / `reporter_phone`
Only authenticated campus security and admins can view these fields to evaluate claims.

---

## Category 6: Application Flow & Business Rules

### Q26: Describe the matching algorithm rule engine.
**Answer**:
When a lost or found report is submitted, `backend/matcher.py` searches opposite-type ACTIVE items within the **same campus** and within a **14-day temporal window**. It calculates a match score (0–100):
- **Category Match**: +35 points (mandatory prerequisite)
- **Item Name Similarity**: Up to +30 points (token overlap & Levenshtein similarity)
- **Location Match**: +15 points (same location) or +5 points (same building)
- **Brand Match**: +10 points
- **Color Match**: +10 points
If total score $\ge 60$, a `match_suggestions` row is inserted and an in-app notification is sent to the lost item owner.

### Q27: Can a student claim an item on the other campus?
**Answer**:
No. Assumption A-2 specifies that students can *browse* both campuses to verify if their item was handed in elsewhere, but they cannot file reports or claims outside their registered campus. Attempting to claim an item from the opposite campus returns HTTP 403 `WRONG_CAMPUS`.

### Q28: How does the system enforce accessibility (WCAG 2.2 AA)?
**Answer**:
1. All form inputs have explicit `<label for="...">` associations.
2. Interactive buttons have minimum 44px touch targets.
3. Color contrast ratios exceed 4.5:1 for normal text (cream `#FAF6EE`, forest green `#1F4D3A`, dark ink text on saffron `#E8892B` buttons).
4. No status is conveyed by color alone (all badges include icon + text label).
5. All animations honor `prefers-reduced-motion: reduce`.
6. Automated compliance audited via `axe-core` across 10 portal views.

### Q29: What happens when an item remains unclaimed for 90 days?
**Answer**:
Per College Lost Property Policy (Assumption A-8), items unclaimed after 90 days are flagged as `STALE` in the admin dashboard and can be transitioned to `CLOSED` or approved for campus auction/charity disposal.

### Q30: Why does the system use two separate web portals instead of one?
**Answer**:
Role-based portal separation isolates attack surfaces and user workflows:
1. **Student Portal** (`student-portal/`): Mobile-first, friendly, distraction-free interface for self-service reporting, discovery, and claim tracking using PRN authentication.
2. **Admin Portal** (`admin-portal/`): Dense, data-rich workstation interface for security guards and college administrators featuring KPI cards, claim approval queues, CSV export, user management, and audit logs using staff username credentials.
Both portals communicate with the same unified Flask API and MySQL database.

