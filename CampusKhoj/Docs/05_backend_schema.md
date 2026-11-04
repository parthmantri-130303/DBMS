<!-- File: 05_backend_schema.md -->
# CampusKhoj — Backend Data Schema & API Overview

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Overview

The backend is a Flask REST API over MySQL 8 (InnoDB, `utf8mb4`). It owns authentication, campus rules, matching, the claim state machine, the event timeline, notifications and the audit trail. Both portals call the same API; the token's `role`, `portal`, `scope` and `campus_id` decide what is allowed.

## 2. Data Model

### 2.1 Entity list
`campuses`, `roles`, `users`, `prn_registry`, `login_attempts`, `categories`, `locations`, `lost_items`, `found_items`, `match_suggestions`, `claims`, `claim_verifications`, `item_events`, `notifications`, `audit_logs`.

### 2.2 Tables

```text
campuses
  - campus_id: TINYINT (PK)            -- 1 = Kondhwa, 2 = Bibwewadi
  - campus_name: VARCHAR(40) UNIQUE
  - code: VARCHAR(10) UNIQUE           -- KON, BIB

roles
  - role_id: TINYINT (PK)
  - role_name: VARCHAR(20) UNIQUE      -- STUDENT, SECURITY, CAMPUS_ADMIN, SUPER_ADMIN

prn_registry                           -- imported from the two Excel files
  - prn: CHAR(10) (PK)                 -- 10 digits, validated
  - campus_id: TINYINT (FK -> campuses)
  - imported_at: DATETIME
  - imported_by: INT NULL (FK -> users)

users
  - user_id: INT (PK, AUTO_INCREMENT)
  - prn: CHAR(10) NULL UNIQUE (FK -> prn_registry.prn)   -- NULL for staff
  - staff_username: VARCHAR(40) NULL UNIQUE               -- NULL for students
  - name: VARCHAR(100) NULL
  - email: VARCHAR(120) NULL UNIQUE
  - phone: VARCHAR(15) NULL
  - password_hash: VARCHAR(60) NULL    -- NULL = never set; PRN is the one-time credential
  - must_change_password: BOOLEAN DEFAULT 1
  - role_id: TINYINT (FK -> roles)
  - campus_id: TINYINT NULL (FK -> campuses)   -- NULL only for SUPER_ADMIN
  - status: ENUM('ACTIVE','SUSPENDED','DEACTIVATED') DEFAULT 'ACTIVE'
  - last_password_change: DATETIME NULL
  - profile_completed: BOOLEAN DEFAULT 0
  - created_at: DATETIME
  - CHECK ( (prn IS NOT NULL) <> (staff_username IS NOT NULL) )   -- exactly one identity

login_attempts
  - attempt_id: BIGINT (PK)
  - identifier: VARCHAR(40)            -- PRN or staff username
  - ip_address: VARCHAR(45)
  - success: BOOLEAN
  - attempted_at: DATETIME
  - INDEX (identifier, attempted_at)

categories
  - category_id: SMALLINT (PK)
  - category_name: VARCHAR(50) UNIQUE
  - description: VARCHAR(200)

locations
  - location_id: INT (PK)
  - campus_id: TINYINT (FK -> campuses)
  - location_name: VARCHAR(80)
  - building: VARCHAR(60)
  - room_or_spot: VARCHAR(100) NULL          -- specific spot or room/lab
  - floor: VARCHAR(20)
  - description: VARCHAR(200)
  - sort_order: SMALLINT DEFAULT 0
  - is_active: BOOLEAN DEFAULT 1
  - UNIQUE (location_id, campus_id)    -- target for the composite FK
  - UNIQUE (campus_id, location_name)

lost_items
  - lost_id: INT (PK)
  - user_id: INT (FK -> users)
  - campus_id: TINYINT
  - category_id: SMALLINT (FK -> categories)
  - location_id: INT
  - item_name: VARCHAR(100)
  - description: TEXT
  - brand: VARCHAR(60) NULL
  - color: VARCHAR(30) NULL
  - date_lost: DATE
  - time_lost: TIME NULL
  - image_url: VARCHAR(255) NULL
  - status: ENUM('ACTIVE','MATCHED','CLAIMED','RETURNED','CLOSED') DEFAULT 'ACTIVE'
  - created_at, updated_at: DATETIME
  - FOREIGN KEY (location_id, campus_id) REFERENCES locations(location_id, campus_id)
  - INDEX (campus_id, status, category_id, date_lost)
  - FULLTEXT (item_name, description, brand)

found_items
  - found_id: INT (PK)
  - user_id: INT (FK -> users)         -- finder or staff who registered it
  - campus_id: TINYINT
  - category_id: SMALLINT (FK)
  - location_id: INT
  - item_name, brand, color, description (public)
  - private_details: TEXT NULL         -- staff-only, used for verification
  - date_found: DATE
  - time_found: TIME NULL
  - image_url: VARCHAR(255) NULL
  - custody: ENUM('WITH_FINDER','AT_DESK') DEFAULT 'WITH_FINDER'
  - storage_location: VARCHAR(100) NULL   -- staff-only
  - status: ENUM('ACTIVE','MATCHED','CLAIMED','HANDED_OVER','CLOSED') DEFAULT 'ACTIVE'
  - created_at, updated_at: DATETIME
  - FOREIGN KEY (location_id, campus_id) REFERENCES locations(location_id, campus_id)
  - INDEX (campus_id, status, category_id, date_found)
  - FULLTEXT (item_name, description, brand)

match_suggestions
  - match_id: INT (PK)
  - lost_id: INT (FK), found_id: INT (FK)
  - campus_id: TINYINT
  - score: TINYINT                     -- 0..100
  - breakdown: JSON                    -- {"category":30,"name":18,"color":15,"location":20,"time":10}
  - created_at: DATETIME
  - UNIQUE (lost_id, found_id)

claims
  - claim_id: INT (PK)
  - found_id: INT (FK -> found_items)  -- required
  - lost_id: INT NULL (FK -> lost_items)   -- optional link to claimant's own lost report
  - claimant_id: INT (FK -> users)
  - campus_id: TINYINT
  - claim_description: TEXT
  - claim_status: ENUM('PENDING','UNDER_REVIEW','APPROVED','REJECTED','COMPLETED','CANCELLED') DEFAULT 'PENDING'
  - reject_reason: VARCHAR(255) NULL
  - submitted_at, reviewed_at: DATETIME
  - reviewed_by: INT NULL (FK -> users)
  - handed_over_at: DATETIME NULL, handed_over_by: INT NULL (FK -> users)
  - active_key: TINYINT GENERATED ALWAYS AS
        (CASE WHEN claim_status IN ('PENDING','UNDER_REVIEW','APPROVED') THEN 1 ELSE NULL END) STORED
  - CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)   -- stored generated column: evaluates to 1 when active, NULL when resolved; permits re-claims after rejection since NULLs do not collide in unique index
  - INDEX (campus_id, claim_status, submitted_at)

claim_verifications
  - verification_id: INT (PK)
  - claim_id: INT (FK -> claims)
  - question: VARCHAR(255)
  - expected_evidence: VARCHAR(255) NULL     -- staff-only
  - answer: TEXT NULL                        -- claimant's answer
  - verification_status: ENUM('ASKED','ANSWERED','VERIFIED','FAILED') DEFAULT 'ASKED'
  - asked_by: INT (FK), verified_by: INT NULL (FK), verified_at: DATETIME NULL

item_events                                  -- the timeline
  - event_id: BIGINT (PK)
  - item_type: ENUM('LOST','FOUND','CLAIM')
  - item_id: INT
  - campus_id: TINYINT
  - event_type: VARCHAR(30)
  - title: VARCHAR(100)
  - description: VARCHAR(255) NULL
  - actor_id: INT NULL (FK -> users)
  - is_public: BOOLEAN DEFAULT 0
  - created_at: DATETIME(3)
  - INDEX (item_type, item_id, created_at)

notifications
  - notification_id: BIGINT (PK)
  - user_id: INT (FK)
  - message: VARCHAR(255)
  - notification_type: VARCHAR(30)
  - ref_type: VARCHAR(10) NULL, ref_id: INT NULL     -- deep link target
  - is_read: BOOLEAN DEFAULT 0
  - created_at: DATETIME
  - INDEX (user_id, is_read, created_at)

message_outbox                               -- simulated SMS and chat notifications
  - message_id: INT (PK, AUTO_INCREMENT)
  - user_id: INT (FK -> users)
  - campus_id: TINYINT (FK -> campuses)
  - channel: ENUM('SMS','WHATSAPP','EMAIL') DEFAULT 'SMS'
  - template_code: VARCHAR(50)
  - body: VARCHAR(480)
  - to_phone_masked: VARCHAR(15) NULL         -- e.g. '98****3210' or 'No phone saved (preview only)'
  - ref_type: VARCHAR(20) NULL, ref_id: INT NULL
  - status: ENUM('SIMULATED','READ') DEFAULT 'SIMULATED'
  - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - INDEX (user_id, created_at)
  - INDEX (campus_id, created_at)

audit_logs
  - log_id: BIGINT (PK)
  - user_id: INT NULL (FK)
  - action: VARCHAR(40)
  - entity_type: VARCHAR(20), entity_id: VARCHAR(20)
  - details: JSON NULL
  - ip_address: VARCHAR(45) NULL
  - created_at: DATETIME
```

### 2.3 Relationships (cardinality)
- campuses 1—N prn_registry, users, locations, lost_items, found_items, claims
- roles 1—N users · prn_registry 1—0..1 users
- users 1—N lost_items, found_items, claims (as claimant), notifications, audit_logs, item_events (as actor)
- categories 1—N lost_items, found_items · locations 1—N lost_items, found_items (campus-consistent via composite FK)
- found_items 1—N claims · lost_items 0..1—N claims (optional link)
- claims 1—N claim_verifications
- lost_items N—M found_items through `match_suggestions`
- lost/found/claim 1—N item_events (polymorphic via `item_type`+`item_id`)

### 2.4 Normalization notes
Reference data (campus, role, category, location) are separate tables (3NF). `claims.campus_id` and `match_suggestions.campus_id` are intentional, constraint-checked denormalizations for fast campus filtering (documented trade-off; verify with functional dependencies before claiming BCNF). `item_events` is polymorphic by design (no single FK) — an acceptable timeline trade-off; integrity checked in the service layer.

### 2.5 Views, triggers, procedures
- **Views:** `v_active_lost` and `v_active_found` (public columns only), `v_pending_claims`, `v_dashboard_stats`, `v_top_locations`, `v_top_categories`, `v_monthly_trend`, `v_campus_comparison`.
- **Triggers:** `trg_claims_status_audit` (AFTER UPDATE on claims → audit row), `trg_lost_status_event` / `trg_found_status_event` (status change → timeline row if not already written), `trg_users_pwd_change` (audit when `password_hash` changes).
- **Stored procedure:** `sp_approve_claim(claim_id, staff_id)` — executes within an atomic transaction. Sets target claim to `APPROVED`, found item to `CLAIMED`, optional lost report to `CLAIMED`, and automatically rejects all competing `PENDING` or `UNDER_REVIEW` claims on that found item (`reject_reason = 'Another claim on this item was approved'`), with `DECLARE EXIT HANDLER FOR SQLEXCEPTION` performing full `ROLLBACK`. Replicated in Python endpoint `POST /admin/claims/{id}/approve`.

## 3. Matching Rules (v1)

Candidates: opposite type, **same campus**, status ACTIVE/MATCHED, **same category (hard filter)**.

| Signal | Points |
|---|---|
| Category match | 30 (filter + points) |
| Item-name similarity (token overlap / `difflib` ratio × 25) | 0–25 |
| Colour match | 15 |
| Same location 20 · same building 10 | 0–20 |
| Date proximity: same day 10 · within 3 days 5 · found before lost − 1 day = 0 | 0–10 |

Threshold ≥ **50** (configurable). Only the lost-report owner is notified; finder identity is never revealed.

## 4. API Design Overview

- **Style:** REST/JSON. **Base:** `/api/v1`. **Versioning:** path prefix; breaking changes → `/v2`.
- **Auth:** `Authorization: Bearer <JWT>`; claims `sub, role, campus_id, scope, portal, exp`. `scope=pwd_change` tokens only reach `/auth/change-password` and `/auth/me`.
- **Pagination:** `?page=1&page_size=20` → `{items, page, page_size, total}`.
- **Dates:** ISO 8601 (campus local time stored; display in IST).

## 5. Key Endpoints

### Auth
| Method | Path | Purpose / key fields |
|---|---|---|
| POST | `/auth/login` | `{username, password, portal}` → `{token, scope, must_change_password, user:{role, campus}}` |
| POST | `/auth/change-password` | `{current_password, new_password}` → `{token}` (full scope) |
| GET | `/auth/me` | Current user, flags |
| PUT | `/me/profile` | `{name, phone, email?}` |

### Reference & browsing
| Method | Path | Purpose |
|---|---|---|
| GET | `/campuses` | Both campuses |
| GET | `/campuses/{cid}/locations` | Locations for a campus |
| GET | `/categories` | Categories |
| GET | `/campuses/{cid}/lost` · `/found` | Public listings; filters `q, category_id, location_id, color, from, to, status` |
| GET | `/lost/{id}` · `/found/{id}` | Public detail (no private fields) |

### Reporting (student)
| Method | Path | Request → Response |
|---|---|---|
| POST | `/lost` | multipart `{item_name, category_id, location_id, date_lost, time_lost?, color?, brand?, description, image?}` → `{lost_id, status, campus_id}`; 403 `WRONG_CAMPUS` if location not in own campus |
| POST | `/found` | same + `{custody, private_details?}` → `{found_id}` |
| PATCH | `/lost/{id}` · `/found/{id}` | Edit own ACTIVE report |
| POST | `/lost/{id}/close` · `/found/{id}/close` | Close own report |
| GET | `/me/lost` · `/me/found` | My reports |
| GET | `/lost/{id}/matches` | Owner only: `[{found_id, score, breakdown, public_summary}]` |

### Timeline
| Method | Path | Purpose |
|---|---|---|
| GET | `/items/{type}/{id}/timeline` | `type` = lost/found/claim → `[{event_id, event_type, title, description, created_at, is_public}]`; non-owners get public events only |

### Claims (student)
| Method | Path | Purpose |
|---|---|---|
| POST | `/found/{id}/claims` | `{claim_description, lost_id?}` → `{claim_id, claim_status:"PENDING"}`; 409 if active claim exists |
| GET | `/me/claims` · `/claims/{id}` | My claims (verification questions shown without expected evidence) |
| POST | `/claims/{id}/answers` | `{answers:[{verification_id, answer}]}` |
| POST | `/claims/{id}/cancel` | Cancel own PENDING/UNDER_REVIEW claim |

### Notifications
`GET /me/notifications` · `GET /me/notifications/unread_count` · `POST /me/notifications/{id}/read` · `POST /me/notifications/read_all`

### Admin (role SECURITY/CAMPUS_ADMIN/SUPER_ADMIN; campus-scoped except SUPER_ADMIN)
| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/dashboard?campus=` | KPI counters |
| GET | `/admin/items?type&campus&status&category_id&q&from&to` | All items incl. private fields; `&format=csv` for export |
| GET | `/admin/items/{type}/{id}` | Full detail + matches + timeline |
| PATCH | `/admin/items/{type}/{id}/status` | Close / reopen / mark AT_DESK (audited) |
| GET | `/admin/claims?status=` | Queue |
| POST | `/admin/claims/{id}/start-review` | PENDING → UNDER_REVIEW |
| POST | `/admin/claims/{id}/questions` | `{question, expected_evidence?}` |
| POST | `/admin/claims/{id}/verify` | `{verification_id, status}` |
| POST | `/admin/claims/{id}/approve` | Transactional approval |
| POST | `/admin/claims/{id}/reject` | `{reason}` |
| POST | `/admin/claims/{id}/handover` | `{received_by_prn}` |
| GET | `/admin/users` · POST `/admin/users/{id}/suspend` · `/reset-password` · `/unlock` | User management |
| POST | `/admin/prn-registry/import` | multipart XLSX/CSV + `campus_id` → `{inserted, skipped, invalid}` |
| GET | `/admin/analytics/{summary|locations|categories|trend|campus-compare}` | Charts data |
| GET | `/admin/audit-logs` | Filters: user, action, entity, date |
| CRUD | `/admin/staff` | SUPER_ADMIN only |

### Error shape
`{"error":{"code":"WRONG_CAMPUS","message":"You can only report items in your own campus.","details":{}}}` (code list in the TRD).

## 6. Background Jobs & Management CLI Commands

Management CLI commands implemented in `backend/manage.py`:
- `python manage.py import-prn --file <path> --campus KON|BIB [--dry-run]`: Ingests official PRN registry from Excel/CSV.
- `python manage.py create-admin --username <user> --name <name> --role <role> [--campus KON|BIB]`: Creates administrative accounts.
- `python manage.py seed-demo`: Seeds rich, realistic demo items, claims, and verification steps using real imported PRNs from `student_data/`.
- `python manage.py run-rematch`: Runs nightly item matchmaker across all active reports.
- `python manage.py flag-stale [--days 90]`: Flags active found items unclaimed for > 90 days (Assumption A-8).
- `python manage.py purge-demo-staff`: Deletes development/rehearsal staff accounts before production deployment.

Scheduled background jobs:
| Job | Trigger / Command | Action |
|---|---|---|
| `rematch_nightly` | `python manage.py run-rematch` (02:00 daily) | Re-scores ACTIVE reports per campus |
| `flag_stale_found` | `python manage.py flag-stale --days 90` (03:00 daily) | Flags found items ACTIVE > 90 days for admin review (Assumption A-8) |
| `purge_notifications` | weekly | Deletes read notifications > 180 days |
| `purge_login_attempts` | daily | Deletes attempts > 30 days |

Post-report matcher runs in-process after commit (fast; ≤ few hundred candidates per campus).

## 7. Caching & Performance

- No external cache in v1. Categories, campuses and locations cached in-process (TTL 10 min).
- Dashboard aggregates cached for 60 s per campus.
- Indexes as listed; `EXPLAIN` evidence kept for the report.
- Nginx serves images with long cache headers (UUID names are immutable).

## 8. Security & Data Protection

- Validate and sanitize every field (length, enum, date range); reject unknown fields.
- Parameterized SQL only; no string-built queries.
- **Sliding Window Rate Limiter**: 20 requests/minute for `/api/v1/auth/login` (brute-force / credential stuffing protection); 180 requests/minute for general `/api/*`. Returns HTTP 429 `RATE_LIMITED`.
- **Account Lockout**: 5 consecutive failed login attempts locks account for 15 minutes (HTTP 423 `ACCOUNT_LOCKED`).
- **Privacy Boundary**: Public serializers exclude `private_details`, `storage_location`, `expected_evidence`, answers, reporter PRN/phone.
- **Portal Separation**: Tokens issued for student portal cannot access `/api/v1/admin/*` (HTTP 403 `FORBIDDEN`).
- TLS in deployment; DB user has least privilege (no DDL at runtime); secrets from environment.
- Audit rows for: password change/reset, role/status changes, PRN import, claim review/approval/rejection/handover, item status overrides, staff changes.

## 9. Seed & Import Notes

- `manage.py import-prn` reads the single-column `PRN` sheets in `student_data/` (`Kondhwa PRN.xlsx` and `Bibwewad PRN.xlsx`); validated 10-digit numeric; **Bibwewadi 582 + Kondhwa 513 = 1,095 unique PRNs, no overlap** (checked on the supplied files).
- Each imported PRN creates `prn_registry` + `users` rows (role STUDENT, `password_hash NULL`, `must_change_password = 1`, `profile_completed = 0`).
- Initial login credential is the student's PRN. Upon login, token scope is restricted to `pwd_change`, requiring immediate password update before dashboard access.
