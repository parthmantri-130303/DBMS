<!-- File: 03_app_flow_architecture.md -->
# CampusKhoj — App Flow & Architecture Flow

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. High-Level Architecture

```
 ┌───────────────────┐      ┌───────────────────┐
 │  STUDENT PORTAL   │      │   ADMIN PORTAL    │
 │ (cream/green UI)  │      │ (charcoal/amber)  │
 │ Kondhwa | Bibwewadi│     │ campus filter     │
 └─────────┬─────────┘      └─────────┬─────────┘
           │   HTTPS + JWT (scope+role)│
           └────────────┬──────────────┘
                        ▼
              ┌──────────────────┐
              │      NGINX       │  static portals, /media, TLS, gzip
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │ GUNICORN + FLASK │
              │ middleware: CORS, rate-limit, auth, role, scope, campus
              │ blueprints: auth | items | claims | timeline |
              │             notifications | admin | analytics
              │ services:  matcher | claim_workflow | importer
              └───────┬──────────┘
                      ▼
              ┌──────────────────┐        ┌──────────────┐
              │   MySQL 8        │        │ media folder │
              │ tables, views,   │        │ item images  │
              │ triggers, txns   │        └──────────────┘
              └──────────────────┘
```

## 2. Component Descriptions

| Component | Responsibility | Tech | Main interfaces |
|---|---|---|---|
| Student Portal | PRN login, forced password change, campus sections, report/claim, timeline, notifications | HTML, Tailwind, vanilla JS | `/api/v1/*` student routes |
| Admin Portal | All-items view, claim review, handover, user/PRN mgmt, analytics, audit | HTML, Tailwind, vanilla JS | `/api/v1/admin/*` |
| Nginx | TLS, static files, media, reverse proxy | Nginx | 443 → Gunicorn |
| API (Flask) | Validation, auth, business rules, orchestration | Python | REST/JSON |
| Auth module | Login, token issue, scope/role checks, lockout | PyJWT, bcrypt | `/auth/*` |
| Items module | Lost/found CRUD, search, image handling | Flask, Pillow | `/lost`, `/found`, `/campuses/*` |
| Matcher | Score candidates, store suggestions | Python service | internal call after report commit |
| Claim workflow | State machine + transactions | Python + SQL txn | `/claims/*`, `/admin/claims/*` |
| Timeline module | Write/read `item_events` with visibility | SQL | `/items/{t}/{id}/timeline` |
| Notifications | Create/read in-app alerts | SQL | `/me/notifications` |
| MySQL | Source of truth, integrity | InnoDB | SQL |

## 3. User Journey Flows

### J1 — First login (PRN) and forced password change
1. Student opens Student Portal → enters PRN (username) and PRN (password).
2. Frontend `POST /auth/login {username, password, portal:"student"}`.
3. API: lockout check → find user by PRN → `password_hash IS NULL` and password equals PRN → issue `scope=pwd_change` token + `must_change_password=true`.
4. Portal routes straight to **Change Password** (all nav hidden).
5. Student submits new password → `POST /auth/change-password` → validate → bcrypt hash → clear flag → audit → return full token.
6. Portal shows **Complete Profile** (name, phone, optional email) → `PUT /me/profile` → Dashboard with animated welcome and campus badge.

### J2 — File a lost complaint (campus-restricted)
1. Dashboard → **Report Lost** (form shows student's campus; location dropdown loads `GET /campuses/{own}/locations`).
2. Submit multipart → `POST /lost`.
3. API validates → checks campus → saves image → **transaction:** insert `lost_items` + `item_events(REPORTED, public)`.
4. After commit: matcher runs → possible `match_suggestions` + `MATCH_SUGGESTED` event + notification.
5. Response → portal navigates to the item page with the timeline animating its first node.

### J3 — Report a found item
1. Student picks **Report Found**, chooses custody (*I have it* / *Handed to desk*), fills public description and private details.
2. `POST /found` → same pattern as J2 (event `REPORTED`; if AT_DESK, event `RECEIVED_AT_DESK` is added by staff later).
3. Matcher scores ACTIVE lost items of the same campus → notifies matching lost owners.

### J4 — Claim, verify, handover
1. Owner sees a match (or browses) → **This is mine** on a found item → `POST /found/{id}/claims`.
2. API: same campus? not finder? no active claim? → insert claim PENDING + `CLAIM_SUBMITTED` event (private to claimant/staff) + notify staff queue.
3. Staff open Admin Portal → **Claims** → *Start review* (UNDER_REVIEW) → add private question(s) from the item's private details.
4. Student sees "More verification needed" notification → `POST /claims/{id}/answers`.
5. Staff compare answers → mark VERIFIED → **Approve** → one transaction updates claim, found item, linked lost item, events, notification, audit.
6. Student brings PRN/ID card to campus desk → staff **Record handover** → claim COMPLETED, found HANDED_OVER, lost RETURNED, timeline shows final node.

### J5 — Admin overview
1. Staff login at Admin Portal (staff username + password).
2. Dashboard shows counters (animated count-up), recovery rate, top locations/categories, pending claims.
3. **All Items** table: filters (campus, type, status, category, date) → click row for full detail incl. private fields → export CSV.

## 4. State & Session Management

- **Token:** JWT in memory + `sessionStorage` (cleared on tab close); claims: `sub`, `role`, `campus_id`, `scope`, `portal`, `exp`. Never in URL.
- **Portal guard:** every page calls `GET /auth/me`; if `must_change_password`, redirect to Change Password.
- **Portal separation:** token `portal` claim must match the website; a student token is rejected by admin routes and vice-versa.
- **Server state:** none beyond DB (stateless API). Logout = client discards token (optional denylist table for staff tokens).
- **UI state:** campus tab selection and filters stored in `sessionStorage` per portal.

## 5. Event & Data Flow

```
User action → API route → service
   → BEGIN
       write domain rows (item/claim)
       write item_events row(s)
       write notifications row(s)
       write audit_logs row (sensitive actions)
     COMMIT
   → post-commit: matcher (new reports) → match_suggestions + events + notifications
   → portal polls GET /me/notifications/unread_count every 30 s
```

Triggers act as a safety net: a `AFTER UPDATE ON claims` trigger writes an audit row on any status change, so even manual SQL edits are traced.

## 6. Failure & Degradation Paths

| Failure | Behaviour |
|---|---|
| DB down | API returns 503 `INTERNAL`; portals show a friendly "Service is resting, try again" banner with retry; no partial writes |
| Transaction error during approval | Full rollback; staff see error toast; claim stays UNDER_REVIEW |
| Matcher fails | Report is still saved; error logged; nightly job re-runs matching |
| Image upload invalid/oversized | 413/415 with clear field message; form data preserved |
| Token expired | Portal redirects to login, preserving the target page |
| Network offline | Portal shows offline banner; forms keep drafts in memory |
| Account locked | Message with remaining wait time; admin can unlock |
| Media folder unavailable | Cards fall back to category icon placeholder |
