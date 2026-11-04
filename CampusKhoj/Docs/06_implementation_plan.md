<!-- File: 06_implementation_plan.md -->
# CampusKhoj — Implementation Plan & Roadmap

Version 1.0 · 1 November 2026 · AI-generated for the project team

*Timeline is an Assumption (A-1): 10 weeks, team of 3–4 students, ~10–12 hours per person per week. Shift dates to your submission calendar.*

## 1. Project Phases

| Phase | Name | Duration | Objective |
|---|---|---|---|
| 0 | Discovery & Setup | Week 1 | Freeze scope, ER diagram, repo, tokens, database skeleton |
| 1 | MVP Core | Weeks 2–5 | PRN login + forced change, campus rules, report lost/found, search, timeline, both portals' shells |
| 2 | Enhanced Features | Weeks 6–8 | Matching, claims, verification, handover, notifications, admin analytics, animations |
| 3 | Hardening & Delivery | Weeks 9–10 | Tests, security pass, performance, docs, viva prep, demo data |

## 2. Milestones & Deliverables

**Phase 0 — Discovery & Setup (Week 1)**
- Deliverables: these 10 docs reviewed; ER diagram; relational schema; `schema.sql` v0 with composite FK and generated-column claim key prototyped; repo + folder layout; `tokens.css`; PRN import script validated on both Excel files (582 + 513).
- Exit: team can run API "hello", MySQL, and both empty portals locally.

**Phase 1 — MVP Core (Weeks 2–5)**
- Auth: login, lockout, `pwd_change` scope, change-password, profile setup.
- Campus data: campuses, locations (seed per campus), categories.
- Lost/found create/list/detail with image upload; campus enforcement (API + DB).
- Search + filters + FULLTEXT; student campus sections (Kondhwa | Bibwewadi).
- `item_events` writer + timeline component (v1 animation).
- Admin Portal shell: login, all-items table with campus filter.
- Exit: a student can log in with PRN, change password, report an item in own campus, and see the timeline; admin sees it.

**Phase 2 — Enhanced Features (Weeks 6–8)**
- Matcher + `match_suggestions` + notifications.
- Claims state machine, verification questions/answers, approve/reject, handover (transaction + `sp_approve_claim`).
- Views, triggers, audit logs; admin claim-review UI; dashboard + charts; CSV export; PRN import UI.
- Animation polish (timeline, counters, tabs, skeletons) + reduced-motion.
- Exit: full lost → match → claim → verify → handover → returned flow works end-to-end on both campuses.

**Phase 3 — Hardening & Delivery (Weeks 9–10)**
- Unit/API/E2E tests, load test, security checks (OWASP list), accessibility pass.
- Seed realistic demo data (both campuses), screenshots, ER diagram final, `queries.sql`, normalization write-up.
- Report + presentation; viva rehearsal using Appendix C talking points of the course spec.
- Exit: tagged release `v1.0`, demo script rehearsed twice.

## 3. Team & Roles *(suggested for 4 members; merge for 3)*

| Role | Responsibilities |
|---|---|
| **DB lead** | ER, schema, constraints, views, triggers, procedures, seed data, `queries.sql`, normalization doc |
| **Backend lead** | Flask app, auth, services, matcher, transactions, tests |
| **Student Portal lead** | Student UI, theme/tokens, animations, accessibility |
| **Admin Portal + QA lead** | Admin UI, analytics, CSV, test plan execution, load test, docs/screenshots |

Everyone: code review via pull requests; each member must be able to explain the DB design in the viva.

## 4. Sprint Breakdown (1-week sprints)

| Sprint | Week | Theme |
|---|---|---|
| S0 | 1 | Setup, ER/schema, tokens, PRN import proof |
| S1 | 2 | Auth backend + login/change-password UI |
| S2 | 3 | Campuses/locations/categories, lost report API + form |
| S3 | 4 | Found report, image upload, listings, campus sections |
| S4 | 5 | Search/filters, item detail, timeline v1, admin items table |
| S5 | 6 | Matcher, notifications, student dashboard |
| S6 | 7 | Claims + verification + admin review UI |
| S7 | 8 | Approval/handover transaction, audit, analytics, CSV |
| S8 | 9 | Animation polish, security/accessibility fixes, tests |
| S9 | 10 | Load test, docs, demo data, release, viva rehearsal |

## 5. Technical Setup Tasks

1. Git repo (`campuskhoj/`) with branches `main` (stable) and `develop`; protect `main`.
2. Layout:
```
campuskhoj/
├── backend/        (app/, routes/, services/, repositories/, middleware/, tests/, manage.py)
├── student-portal/ (index.html, pages/, js/, css/)
├── admin-portal/   (index.html, pages/, js/, css/)
├── shared/         (tokens.css, api.js, ui-utils.js)
├── database/       (schema.sql, seed.sql, views.sql, triggers.sql, procedures.sql, queries.sql)
├── prn/            (Kondhwa_PRN.xlsx, Bibwewad_PRN.xlsx)   ← kept out of Git if policy requires
├── docs/           (the 10 documents)
└── README.md
```
3. `.env` template (DB creds, `JWT_SECRET`, CORS origins); `.gitignore` excludes `.env`, `media/`, `prn/`.
4. `docker-compose.yml` (MySQL + API) for identical dev environments (optional).
5. CI: lint, tests on pull request.
6. Logging config, `/health` endpoint, seed script, `manage.py create-admin`, `manage.py import-prn`.

## 6. Dependencies & Critical Path

**Critical path:** schema (campus + composite FK) → auth/PRN import → report APIs → timeline → matcher → claims → handover → analytics.

| Dependency | Needed by | Note |
|---|---|---|
| Final campus location lists (Kondhwa, Bibwewadi) | S2 | Placeholder lists until supplied |
| Email data file | after v1 | Not blocking; email optional |
| Security-staff accounts list | S6 | Needed for demo |
| Hosting decision | S9 | Local demo is the fallback |

**Biggest schedule risks:** two-frontend workload; claim transaction edge cases; late design tokens; exam weeks.

## 7. Definition of Done (per feature)

- Code merged via reviewed PR; lint passes.
- Unit + API tests written and green; negative/authorization cases included.
- Database changes captured in versioned SQL files and reflected in docs.
- Campus rule verified (cannot cross campuses) where relevant.
- UI works at 360 px and ≥ 1280 px; keyboard accessible; reduced-motion respected.
- Timeline/audit/notification side-effects verified.
- Demonstrated on the staging/demo environment and ticked in the test sheet.
