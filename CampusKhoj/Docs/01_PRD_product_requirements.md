<!-- File: 01_PRD_product_requirements.md -->
# CampusKhoj — Product Requirements Document (PRD)

| Field | Value |
|---|---|
| Project name | CampusKhoj — Two-Campus Lost & Found Management System (earlier working title: FindBack) |
| Document version | 1.0 |
| Date | 1 November 2026 |
| Author | AI-generated (Claude) for the project team |
| Audience | Course professor and classmates (academic, professional tone) |
| Course | Database Management System (DBMS) — Course Project, 2026–27 |

---

## 1. Executive Summary

CampusKhoj is a database-driven lost-and-found platform for a college with **two campuses: Kondhwa and Bibwewadi**. It replaces scattered WhatsApp groups, notice boards and paper registers with one searchable system. It ships as **two separate websites on one backend**: a **Student Portal** (browse lost/found items per campus, file a lost complaint, report a found item, claim an item, follow a timeline) and an **Admin Portal** (see every item, review claims, record handovers, run analytics, read audit logs).

Students sign in with their **PRN only**. Their first login uses the PRN as both username and password, and the very first screen forces a password change. A lost item is always declared in the student's own campus (a Kondhwa student's lost item is a Kondhwa item; a Bibwewadi student's is a Bibwewadi item), which keeps matching and physical handover simple and realistic.

The project is deliberately *database-centred*: relational design with composite foreign keys, normalization, views, triggers, transactions, indexed search, a per-item event timeline and an audit trail — all demonstrable in a viva.

## 2. Problem Statement

Students lose ID cards, calculators, earphones, chargers, bottles, books and keys. Found items end up in class groups or with security, and owners rarely know where to look — especially with two physically separate campuses.

Why current solutions fall short:

1. **Fragmented** — each class group/community holds a slice of reports.
2. **Unsearchable** — old posts get buried; no filters by category, place or date.
3. **Unverified** — anyone can say "that's mine"; there is no evidence step.
4. **No history** — nobody can see what happened to an item between "reported" and "returned".
5. **Campus-blind** — nothing ties a report to the campus where the item physically is.

## 3. Goals & Success Metrics

**Business (institutional) goals**
- One authoritative record of lost/found items for both campuses.
- Reduce time security staff spend answering "did anyone find my X?".
- Provide campus-wise data on where and what students lose.

**User goals**
- Student: report in under 2 minutes, find a match quickly, see exactly where my item is in the process.
- Admin/security: verify genuine owners, hand over safely, keep a defensible record.

**Success metrics** *(targets are Assumptions for a pilot semester)*

| Metric | Target |
|---|---|
| PRN accounts activated (password changed) within first month | ≥ 60% of 1,095 listed PRNs |
| Median time to submit a lost/found report | ≤ 2 minutes |
| Claims reviewed (decision recorded) | within 48 hours |
| Recovery rate (lost reports ending RETURNED) | ≥ 35% |
| Search p95 response time | ≤ 300 ms at 10,000 items |
| Fraudulent/incorrect handovers | 0 (every handover has an approved, verified claim) |

## 4. Target Users & Personas

| Persona | Role | Goals | Pain points | Typical scenario |
|---|---|---|---|---|
| **Riya** (primary) | Student, Kondhwa campus | Get her calculator back; help return a found ID card | Doesn't know whom to ask; posts get buried | Logs in with PRN, files lost complaint for "Casio fx-991", gets a possible-match notification two days later |
| **Aman** (primary) | Student, Bibwewadi campus | Report a wallet he found in the library | Doesn't want to be blamed or spammed | Reports found item, hands it to the desk, watches the timeline move to "Handed over" |
| **Mr. Patil** (secondary) | Security staff, one campus | Receive found items, verify claimants, record handover | Paper register, repeat questions | Opens claim, asks a private verification question, records handover |
| **Dr. Joshi** (secondary) | Campus admin | Oversee one campus, see stats, handle disputes | No data on what is lost where | Checks dashboard, exports CSV, reads audit log |
| **Super admin** (secondary) | Project/IT owner | Manage staff accounts, PRN registry, both campuses | Manual user management | Imports the PRN list, creates security accounts |

## 5. How the System Works (Decided Working Model)

1. **PRN registry.** The two supplied lists (Bibwewadi: 582 PRNs; Kondhwa: 513 PRNs; 1,095 total, no duplicates, no overlap) are imported into `prn_registry` with their campus. Only listed PRNs can sign in to the Student Portal.
2. **First login.** Username = PRN. Password = PRN *only while the account has never set a password*. The API issues a restricted token; the portal shows **Change Password** as the first and only reachable page. After a valid new password, the user completes a short profile (name, phone, optional email) and enters the portal.
3. **Campus binding.** A student's campus comes from the registry, not from a form field. The Student Portal has two sections — **Kondhwa** and **Bibwewadi** — each listing that campus's lost and found items. A student can *browse* both sections but can *report, claim and receive matches* only in their own campus (Assumption A-2).
4. **Reporting.** Lost complaint and found report are stored with the student's campus; the selected location must belong to the same campus (enforced by a composite foreign key).
5. **Matching.** After each new report the backend scores opposite-type ACTIVE reports **of the same campus** using transparent rules and notifies the owner of a lost report when a score passes the threshold.
6. **Claim → verification → handover.** A student claims a found item; security/admin asks private questions, compares answers with private details, approves or rejects, and records the physical handover at that campus's desk.
7. **Timeline.** Every significant step writes an `item_events` row; students see it as an animated vertical timeline on their own reports and claims (a reduced public version appears on public item pages).
8. **Admin Portal.** Separate website, separate login (staff username, not PRN). Campus admins/security see their campus; super admin sees both.

## 6. Scope

**In scope — v1**
- Two websites (Student Portal, Admin Portal) on one Python backend and one MySQL database.
- PRN login, forced first-login password change, profile completion.
- Campus sections, campus-restricted reporting and claiming.
- Lost complaint, found report (with custody status), single image upload.
- Search + filters, item detail, rule-based matching, claims, verification, approval/rejection, handover.
- Per-item and per-claim timeline.
- In-app notifications, student dashboard.
- Admin: all-items view with campus filter, claim review, user/PRN management, analytics, audit log, CSV export.
- Warm, non-"AI-looking" visual theme with purposeful animations.

**Out of scope — v1**
- Email/SMS/push delivery (in-app only), mobile apps, QR handover, AI/image matching, map view, payments, multi-college support.

**Future phases**
- **v2:** email notifications using the email data file, QR handover receipt, CSV email import, TOTP for admins.
- **v3:** image similarity assistance, hostel-level locations, suspicious-claim detection, campus risk heat-map.

## 7. User Stories & Acceptance Criteria

| ID | Story |
|---|---|
| US-1 | As a student, I want to log in with my PRN so that I don't need a separate registration. |
| US-2 | As a first-time student, I want to be made to set my own password so that my account is not left on the default. |
| US-3 | As a student, I want to file a lost complaint for my campus so that others and security can find it. |
| US-4 | As a student, I want to report a found item so that the owner can reclaim it. |
| US-5 | As a student, I want to see a timeline of my item so that I know its current stage. |
| US-6 | As a student, I want to browse Kondhwa and Bibwewadi sections so that I can see where items are. |
| US-7 | As security staff, I want to verify a claimant with private questions so that only the real owner gets the item. |
| US-8 | As an admin, I want to see all items across campuses so that I can monitor and report. |

**Critical acceptance criteria**

*US-1 / US-2 — first login*
- **Given** a PRN present in the registry with no password set, **when** the student signs in with PRN/PRN, **then** the API returns a restricted token and the portal opens the Change Password page; no other page is reachable.
- **Given** the restricted token, **when** the student submits a new password that is ≥ 8 chars, not the PRN, and not containing the PRN, **then** the password is saved and a full token is issued.
- **Given** a PRN not in the registry, **when** it is used to sign in, **then** login fails with a generic "Invalid PRN or password".

*US-3 — campus rule*
- **Given** a Kondhwa student, **when** they open the lost form, **then** only Kondhwa locations are offered; **and when** a crafted request sends a Bibwewadi location, **then** the API rejects it with `WRONG_CAMPUS` (and the DB constraint also rejects it).

*US-7 — verification*
- **Given** a claim in UNDER_REVIEW, **when** staff mark verification VERIFIED and approve, **then** claim → APPROVED, found item → CLAIMED, a notification and audit row are created in one transaction; if any step fails nothing changes.

*US-5 — timeline*
- **Given** a lost report with a claim approved, **when** the owner opens the timeline, **then** it lists Reported → Match suggested → Claim submitted → Approved in time order with timestamps.

## 8. Functional Requirements (Product View)

**Accounts & Access**
- FR-1 PRN login for students; separate staff login in the Admin Portal.
- FR-2 First-login forced password change (restricted token until done).
- FR-3 Profile completion (name, phone, optional email) after first password change.
- FR-4 Role-based access: STUDENT, SECURITY, CAMPUS_ADMIN, SUPER_ADMIN; enforced in the backend.
- FR-5 Admin-assisted password reset (returns account to first-login state).

**Campus**
- FR-6 Student's campus derived from the PRN registry; students cannot change it.
- FR-7 Student Portal shows two sections: Kondhwa and Bibwewadi.
- FR-8 Reporting and claiming limited to the student's own campus.
- FR-9 Locations are campus-specific; category list is shared.

**Reporting**
- FR-10 Lost complaint (item, category, brand, colour, location, date/time, description, optional image).
- FR-11 Found report (same fields + custody: WITH_FINDER / AT_DESK, public description, private distinguishing details).
- FR-12 One image per report; type/size validated; EXIF stripped.
- FR-13 Owner can edit or close their own ACTIVE report.

**Discovery & Matching**
- FR-14 Keyword search and filters (category, location, colour, date range, status) within a campus section.
- FR-15 Item detail page.
- FR-16 Rule-based match scoring within the same campus.
- FR-17 Notify the lost-report owner when a match passes the threshold.

**Claims & Verification**
- FR-18 Submit a claim on an ACTIVE found item in own campus; one active claim per student per item.
- FR-19 Staff add private verification questions; claimant answers.
- FR-20 Staff approve/reject with reason; rejected claims stay in history.
- FR-21 Record handover (who received, when, by which staff).

**Timeline & Notifications**
- FR-22 Timeline for every lost report, found report and claim.
- FR-23 Public vs private events: public item pages show only public events.
- FR-24 In-app notifications with read/unread state.

**Dashboards & Admin**
- FR-25 Student dashboard (my reports, my claims, unread notifications).
- FR-26 Admin all-items view with campus, type, status, category filters and CSV export.
- FR-27 User and PRN-registry management (import lists, suspend, reset).
- FR-28 Analytics per campus: counts, recovery rate, top locations/categories, monthly trend.
- FR-29 Audit-log viewer.
- FR-30 Staff account management (super admin only).

## 9. Non-Functional Requirements (Product View)

- **Performance:** list/search p95 ≤ 300 ms; pages interactive in ≤ 2.5 s on campus Wi-Fi.
- **Usability:** report form ≤ 8 fields visible by default; mobile-first; clear empty/error states.
- **Visual & motion:** warm cream/forest-green/saffron theme (not a purple/blue gradient "AI" look); animations meaningful and short (≤ 400 ms typical); `prefers-reduced-motion` honoured.
- **Accessibility:** WCAG 2.2 AA target (contrast, keyboard, labels).
- **Reliability:** claim approval and handover are atomic; graceful errors if DB/API fails.
- **Security:** hashed passwords, rate limiting, role checks on every protected route, private data never in public responses.
- **Compliance:** minimal personal data (PRN, name, phone, optional email); follows institutional data policy and DPDP Act 2023 principles of purpose limitation (Assumption A-14).

## 10. Constraints & Assumptions

- Course-project timeline (~10 weeks, 3–4 students) — Assumption A-1.
- Backend must be **Python** (or C); Python chosen. Database: MySQL.
- Full assumption list: see `09_risk_register_assumptions.md`.

## 11. Dependencies

| Type | Dependency |
|---|---|
| Internal | PRN lists (Kondhwa_PRN.xlsx, Bibwewad_PRN.xlsx); email data file (to arrive later); campus location list; security-desk staff for handover |
| External | MySQL 8, Python packages (Flask, PyJWT, bcrypt, Pillow), Google Fonts (or self-hosted fonts) |

## 12. Product Risks & Mitigations

| Risk | Mitigation |
|---|---|
| PRN is a guessable first password | Restricted first-login token, rate-limit + lockout, forced change, no stored PRN-derived hash |
| False claims | Private verification questions, staff approval, audit trail |
| Low adoption | 2-minute report, notification on match, desk staff trained to use Admin Portal |
| PRN lists incomplete | Admin can add a PRN with campus manually (audited) |
| Over-animated UI feels slow | Motion budget ≤ 400 ms, reduced-motion support |

## Appendix — Research Insights

*(Based on general domain knowledge; no live sources were queried for this document.)*
- Typical campus lost items: ID/library cards, calculators, earphones/chargers, bottles, wallets, keys, notebooks.
- Established lost-and-found products share a common pattern: structured item log + photo + matching + proof-of-ownership + handover record.
- Weak point in informal systems is ownership verification; strong systems keep private identifying details out of public listings.
- NIST SP 800-63B recommends length and blocklist checks over arbitrary composition rules for passwords — applied to the change-password rule.
