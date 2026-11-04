<!-- File: 07_test_strategy_qa_plan.md -->
# CampusKhoj — Test Strategy & QA Plan

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Testing Objectives

Quality means: (1) only valid PRN holders get in and everyone changes the default password; (2) **no item, claim or match ever crosses campuses**; (3) private data never leaks; (4) claim approval/handover is atomic and fully traced; (5) the timeline always matches reality; (6) the UI is usable on a phone and accessible.

## 2. Test Levels

| Level | Scope | Tools |
|---|---|---|
| Unit | Matcher scoring, validators, password rules, JWT helpers, state-machine transitions | pytest |
| Database | Constraints, composite FK, unique claim key, triggers, views, `sp_approve_claim`, rollback | pytest + MySQL test schema, SQL scripts |
| Integration/API | Every endpoint incl. auth, scope, role, campus | pytest + Flask test client |
| End-to-end | Full journeys on both portals (mobile + desktop viewports) | Playwright |
| Performance | Search, login, report under load | Locust |
| Security | Dependency, static, dynamic checks | pip-audit, bandit, OWASP ZAP baseline scan |
| Accessibility | Keyboard, contrast, screen reader smoke | axe-core, manual |
| UAT | Real students + security desk staff | Scripted scenarios |

## 3. Test Ownership

| Type | Owner |
|---|---|
| Unit + DB | DB lead & backend lead (author of the code) |
| API | Backend lead; reviewed by QA lead |
| E2E + accessibility | QA lead with portal leads |
| Load + security | QA lead |
| UAT coordination | Whole team; professor/desk staff as testers |

## 4. Test Data & Environments

- **Data:** anonymised seed — the real PRN files are imported only in the demo environment; automated tests use generated PRNs (e.g., `1251000001…`) split across both campuses so real PRNs never appear in test code.
- Seed set: 2 campuses, ~12 locations each, 8 categories, 40 lost / 40 found per campus with known matches, 10 claims in varied states, 1 SUPER_ADMIN, 1 CAMPUS_ADMIN and 1 SECURITY per campus.
- **Environments:** `dev` (local), `test` (CI MySQL container, reset per run), `demo` (prod-like, real PRN import).

## 5. Automation Strategy

**Automate:** all unit, DB, API and the 6 critical E2E journeys (J1–J5 + cross-campus attack).
**Manual:** visual/animation feel, accessibility screen-reader pass, UAT, exploratory testing.
CI runs unit + DB + API on every pull request; E2E nightly.

## 6. Key Test Cases

| ID | Area | Test | Expected |
|---|---|---|---|
| T-01 | Login | PRN not in registry | 401 generic message |
| T-02 | Login | Valid PRN with PRN password, never changed | 200, `scope=pwd_change`, `must_change_password=true` |
| T-03 | Scope | pwd_change token calls `GET /lost` | 403 `PASSWORD_CHANGE_REQUIRED` |
| T-04 | Password | New password equals PRN / contains PRN / < 8 chars | 400 `VALIDATION_ERROR` |
| T-05 | Password | After change, PRN no longer works as password | 401 |
| T-06 | Lockout | 5 wrong passwords | 6th attempt 423 `ACCOUNT_LOCKED` for 15 min |
| T-07 | Portal | Student token on `/admin/*` | 403 |
| T-08 | Campus | Kondhwa student posts lost with Bibwewadi location | 403 `WRONG_CAMPUS`; DB insert directly also fails (composite FK) |
| T-09 | Campus | Kondhwa student claims Bibwewadi found item | 403 `WRONG_CAMPUS` |
| T-10 | Campus | Matcher run | Never links Kondhwa lost with Bibwewadi found |
| T-11 | Browse | Student views other campus section | Public fields only, no claim button |
| T-12 | Report | Missing required field / future date | 400 with field errors |
| T-13 | Upload | `.exe` renamed `.jpg`, 10 MB image | 415 / 413; nothing stored |
| T-14 | Privacy | Public `GET /found/{id}` | No `private_details`, `storage_location`, reporter PRN |
| T-15 | Claim | Duplicate active claim by same student | 409 `CONFLICT` (unique key) |
| T-16 | Claim | Claim on own found report | 409/403 |
| T-17 | Verification | Student reads `expected_evidence` | Never present in student JSON |
| T-18 | Approval | Approve with forced failure at notification insert | Full rollback; claim still UNDER_REVIEW |
| T-19 | Handover | Handover before approval | 409 |
| T-20 | Timeline | Full journey | Events in correct order with timestamps; public vs private respected |
| T-21 | Timeline | Other student requests private events | Only `is_public` events |
| T-22 | Audit | Approve, reject, reset password, PRN import | One audit row each |
| T-23 | Trigger | Manual SQL update of claim status | `trg_claims_status_audit` writes a row |
| T-24 | Admin | Campus admin requests other campus data | 403 or forced to own campus |
| T-25 | Import | Excel with duplicate/invalid PRNs | Report shows inserted/skipped/invalid; no partial corruption |
| T-26 | UI | 360 px layout, keyboard-only flow | No horizontal scroll; all actions reachable |
| T-27 | UI | `prefers-reduced-motion` on | No movement animations |
| T-28 | Injection | `' OR 1=1 --` in search/login | No effect (parameterized) |
| T-29 | XSS | `<script>` in item description | Rendered as text |
| T-30 | Reset | Admin resets password | User returns to first-login flow |

## 7. Performance & Load Testing

| Scenario | Load | Target |
|---|---|---|
| Search/list with filters | 200 concurrent users, 10k items | p95 ≤ 300 ms, error < 1% |
| Login (bcrypt) | 50 logins/s burst (class-start rush) | p95 ≤ 1.2 s |
| Report submit with image | 30 concurrent | p95 ≤ 1.5 s |
| Dashboard aggregates | 20 concurrent admins | p95 ≤ 500 ms |
| First-login rush | 300 students in 5 min | No lockout false positives, no 5xx |

Capture `EXPLAIN` plans for the 5 heaviest queries and attach to the report.

## 8. Security Testing

- `bandit` and `ruff` on every PR; `pip-audit` weekly.
- OWASP Top 10 checklist walk-through (auth, access control, injection, misconfiguration, logging).
- ZAP baseline scan against `demo`.
- Manual IDOR tests: swap IDs across users and campuses for claims, verifications, timeline.
- Verify security headers, CORS allow-list, no secrets in repo.

## 9. Acceptance Criteria & UAT

| Criterion | Evidence |
|---|---|
| All FR-1…FR-30 demonstrated | Traceability sheet FR → test ID → result |
| Critical tests (T-01…T-25) pass | CI report |
| 0 critical / 0 high open defects | Defect log |
| 5 students + 2 desk staff complete scripted tasks | UAT sheet with timings and comments |
| Both campuses demonstrated end-to-end | Demo script |

**Defect severity:** S1 data leak/cross-campus/security · S2 broken core flow · S3 minor · S4 cosmetic. Release blocked by any S1/S2.
