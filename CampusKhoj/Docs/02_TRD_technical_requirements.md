<!-- File: 02_TRD_technical_requirements.md -->
# CampusKhoj — Technical Requirements Document (TRD)

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Introduction

**Purpose:** define how CampusKhoj is built so the team can start implementation.
**Scope:** one Python backend, one MySQL database, two static frontends (Student Portal, Admin Portal).
**Audience:** project team, professor. Terms: see `10_glossary_references.md`.

## 2. System Overview

```
Student Portal (static site)   Admin Portal (static site)
          \                         /
           \--- HTTPS + JSON ------/
                      |
              Flask REST API  (/api/v1)
        auth | items | claims | timeline | notifications | admin | analytics
                      |
                 MySQL 8 (InnoDB)
                      |
        local media folder (item images, served by Nginx)
```

Boundaries: the portals never touch the database; all rules (campus, role, claim state) live in the API and are backed by database constraints.

## 3. Architecture Principles

1. **Database-first integrity** — constraints, composite FKs, transactions; the API is not the only guard.
2. **Layered backend** — routes → services → repositories (raw parameterized SQL).
3. **Secure by default** — deny unless a role check passes; private data never serialised to public endpoints.
4. **Two portals, one API** — role/portal claim in the token; admin routes reject student tokens.
5. **Simple over clever** — transparent rule-based matching, no AI services.
6. **Explainable** — every status change is an `item_events` row and, where sensitive, an `audit_logs` row.

## 4. Functional Technical Requirements

| ID | Maps to | Technical behaviour |
|---|---|---|
| TR-FR-1 | FR-1 | `POST /auth/login {username, password, portal}`. Student portal: username = 10-digit PRN. Looks up `users` by PRN. If `password_hash IS NULL`, accept only when `password == prn` (constant-time compare, `hmac.compare_digest`); otherwise bcrypt verify. Generic error on any failure. |
| TR-FR-2 | FR-2 | If `must_change_password = 1`, issue JWT with `scope="pwd_change"` (15 min). Middleware allows only `POST /auth/change-password` and `GET /auth/me` for this scope; all else → 403 `PASSWORD_CHANGE_REQUIRED`. On success: bcrypt (cost 12) hash stored, flag cleared, full token (`scope="full"`) issued, audit row written. |
| TR-FR-3 | FR-3 | `PUT /me/profile {name, phone, email?}`; email, if given, must match `^[a-z]+\.\d{10}@vit\.edu$` **and** its 10 digits must equal the user's PRN. |
| TR-FR-4 | FR-4 | Decorator `@require_role(...)` + `@require_scope("full")`. Roles from token and re-checked against DB status (SUSPENDED users rejected). |
| TR-FR-5 | FR-5 | `POST /admin/users/{id}/reset-password` sets `password_hash = NULL`, `must_change_password = 1`, writes audit. |
| TR-FR-6 | FR-6 | `users.campus_id` set only by PRN import / admin change (audited). Never read from request body for students. |
| TR-FR-7 | FR-7 | `GET /campuses/{cid}/lost|found` — any authenticated student may read any campus's **public** listings. |
| TR-FR-8 | FR-8 | Service layer compares `current_user.campus_id` with target campus on create/claim → 403 `WRONG_CAMPUS`. |
| TR-FR-9 | FR-9 | `locations(campus_id)`; items store `(location_id, campus_id)` with composite FK to `locations(location_id, campus_id)` so a mismatch is impossible at DB level. |
| TR-FR-10/11 | FR-10/11 | `POST /lost`, `POST /found` (multipart). Validate required fields, date ≤ today, time optional; set `campus_id` from user; insert item + `REPORTED` event + run matcher, all in one transaction (match failure must not roll back the report — matcher runs after commit). |
| TR-FR-12 | FR-12 | Accept JPEG/PNG/WebP ≤ 3 MB; verify with Pillow, re-encode, strip EXIF, rename to UUID, store path in `image_url`. |
| TR-FR-13 | FR-13 | `PATCH /lost/{id}`, `POST /lost/{id}/close` allowed only for owner while status ACTIVE/MATCHED; writes `EDITED`/`CLOSED` events. |
| TR-FR-14 | FR-14 | Search uses indexed filters (`campus_id, status, category_id, location_id, date`) plus `FULLTEXT(item_name, description, brand)` for keywords; pagination `page`, `page_size ≤ 50`. |
| TR-FR-16/17 | FR-16/17 | Matcher (see 05 §Matching) inserts into `match_suggestions` (UNIQUE lost+found), creates a `MATCH_SUGGESTED` event and notification for the lost owner. |
| TR-FR-18 | FR-18 | Claim creation checks: found item ACTIVE/MATCHED, same campus, claimant not the finder, no active claim (unique key trick, see 05). |
| TR-FR-19/20 | FR-19/20 | Staff endpoints add questions, mark verification, approve/reject. Approval runs in one transaction (claim, found item, lost item if linked, event, notification, audit). |
| TR-FR-21 | FR-21 | `POST /admin/claims/{id}/handover` requires claim APPROVED; sets claim COMPLETED, found → HANDED_OVER, lost → RETURNED; records `handed_over_by`, `received_by_prn`, timestamp. |
| TR-FR-22/23 | FR-22/23 | `GET /items/{type}/{id}/timeline`: owner/staff get all events; others get only `is_public = 1`. Claim timeline visible to claimant and staff only. |
| TR-FR-24 | FR-24 | Notifications paginated, `unread_count` endpoint, mark read / read-all. |
| TR-FR-26 | FR-26 | Admin list endpoint with campus/type/status/category/date filters; CSV export streams rows. Campus admins forced to own campus. |
| TR-FR-27 | FR-27 | Import endpoint accepts XLSX/CSV with a `PRN` column (+ campus selector); validates 10 digits, skips duplicates, returns a report (inserted/skipped/invalid). |
| TR-FR-28 | FR-28 | Analytics read from SQL views (`v_dashboard_stats`, `v_top_locations`, `v_top_categories`, `v_monthly_trend`). |
| TR-FR-29/30 | FR-29/30 | Read-only audit endpoint with filters; staff CRUD only for SUPER_ADMIN. |

**Error contract (all endpoints):**
`{"error": {"code": "STRING_CODE", "message": "human text", "details": {...}}}`
Codes: `VALIDATION_ERROR` 400 · `AUTH_REQUIRED` 401 · `INVALID_CREDENTIALS` 401 · `PASSWORD_CHANGE_REQUIRED` 403 · `FORBIDDEN` 403 · `WRONG_CAMPUS` 403 · `NOT_FOUND` 404 · `CONFLICT` 409 · `PAYLOAD_TOO_LARGE` 413 · `UNSUPPORTED_MEDIA` 415 · `ACCOUNT_LOCKED` 423 · `RATE_LIMITED` 429 · `INTERNAL` 500.

## 5. Non-Functional Technical Requirements

| Area | Requirement |
|---|---|
| Performance | p95 ≤ 300 ms for search/list at 10k items; ≥ 200 concurrent users; connection pool size 10–20 |
| Security | bcrypt cost 12; JWT HS256 with 32+ byte secret from env; access token 60 min (full), 15 min (pwd_change); parameterized SQL only; CORS allow-list of the two portal origins; security headers (CSP, X-Content-Type-Options, Referrer-Policy); HTTPS in any deployed environment |
| Brute-force defence | 5 failed logins per PRN/IP in 15 min → 15-min lock (`ACCOUNT_LOCKED`); counters in `login_attempts`; Flask-Limiter 60 req/min/IP default |
| Reliability | Target 99% during campus hours (pilot); transactions for approval/handover/report+event; health endpoint `/health` |
| Scalability | Stateless API (scale with more Gunicorn workers); reference tables for category/location; indexes designed for per-campus queries |
| Maintainability | PEP 8 via `ruff`; type hints; blueprint-per-module; SQL kept in `repositories/`; schema in versioned `.sql` files |
| Observability | JSON logs with request id; log level via env; metrics: request count/latency/error rate (simple log-derived for v1); no PRNs/passwords in logs |

## 6. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Backend language | **Python 3.12** | Meets "C or Python only" rule; fast to build, readable for viva |
| Web framework | **Flask 3** + Blueprints | Small, explicit, easy to explain |
| DB driver | `mysql-connector-python` with pooling | Official driver, raw SQL shows DBMS skills |
| Database | **MySQL 8 (InnoDB)** | Transactions, FKs, triggers, views, FULLTEXT |
| Auth | PyJWT + `bcrypt` | Standard, lightweight |
| Validation | `marshmallow` or `pydantic` | Clear request schemas |
| Images | Pillow | Verify/re-encode/strip EXIF |
| Import | `openpyxl` | Read the supplied `.xlsx` PRN files |
| Rate limiting | Flask-Limiter | Simple per-IP limits |
| Server | Gunicorn behind Nginx | Production-style, serves media + static portals |
| Frontend | HTML + **Tailwind CSS** + vanilla JS (ES modules) — two separate apps | No framework overhead; animations via CSS + Web Animations API (Assumption A-3) |
| Tests | pytest, Playwright, Locust | See `07_test_strategy_qa_plan.md` |
| CI/CD | GitHub Actions | Free, integrates with repo |

*Why not C?* A C backend would require hand-rolling HTTP, JWT, bcrypt and MySQL bindings; risk is high for a semester project. If faculty insist on C, the fallback is a C command-line/CGI component for one module (e.g., the matcher) called from Python.

## 7. Integration & Interfaces

- **Frontend ↔ API:** REST/JSON over HTTPS, `Authorization: Bearer <token>`.
- **API ↔ DB:** pooled connections, explicit transactions via a `with transaction():` context manager.
- **External:** none required in v1 (email delivery deferred). Fonts self-hosted for offline demo.
- **File inputs:** `Kondhwa_PRN.xlsx`, `Bibwewad_PRN.xlsx` (single column `PRN`); later an email data file.

## 8. Data Architecture Overview

- **Ingestion:** PRN import (admin/CLI) → `prn_registry` + `users` (password NULL, must_change = 1, campus from file). Later email import joins on PRN.
- **Processing:** report creation → matcher → events/notifications.
- **Storage:** MySQL for records; filesystem for images (`media/YYYY/MM/uuid.webp`).
- **Consumption:** portals via API; analytics via views.
- **Retention:** closed items kept 1 year then archived (Assumption); audit logs kept 2 years; notifications purged after 180 days.
- **Backup:** nightly `mysqldump`, 14 daily copies.

## 9. Security & Compliance

**Threat highlights**
| Threat | Control |
|---|---|
| Guessing first password (PRN) | Restricted token, lockout, forced change, generic errors |
| Account takeover via stolen token | Short expiry, HTTPS, no token in URL, suspend check on each request |
| SQL injection | Parameterized queries only |
| IDOR (viewing others' claims/verifications) | Ownership/role check in service layer; tests per endpoint |
| Cross-campus tampering | API check + composite FK |
| Malicious upload | MIME sniffing, Pillow re-encode, size cap, random names, no execution from media dir |
| Information leakage | Separate public/private serializers; `private_details`, `storage_location`, verification data never in public JSON |
| XSS | Escape on render (no `innerHTML` with user text), CSP |

**Compliance:** store minimum personal data; PRN is the key identifier; access to PRN registry limited to admins; follow institutional policy and DPDP Act 2023 principles (Assumption A-14).

## 10. Technical Risks & Mitigations

| Risk | Mitigation / fallback |
|---|---|
| Two frontends double the UI work | Shared CSS tokens + shared JS utility modules (`/shared`) |
| Composite FK / generated-column syntax errors | Prototype early in Sprint 1; fallback to triggers |
| Matcher too noisy | Configurable threshold, hard category filter, tune with seed data |
| bcrypt slowness during load test | Cost 12 only on login/change; tune workers |
| Large timeline queries | Index `(item_type, item_id, created_at)` |

## 11. References
See `10_glossary_references.md`.
