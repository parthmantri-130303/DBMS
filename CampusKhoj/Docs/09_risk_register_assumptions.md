<!-- File: 09_risk_register_assumptions.md -->
# CampusKhoj — Risks, Assumptions, Dependencies & Open Questions

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation / contingency |
|---|---|---|---|---|
| R-1 | PRN used as first password is guessable (PRNs are not secret) | High | High | Restricted first-login token; lockout + rate limit; no PRN-derived hash stored; forced change; admin can lock accounts; v2 option: email OTP on first login |
| R-2 | Student claims item that isn't theirs | Medium | High | Private verification questions, staff approval, audit, desk handover with ID check |
| R-3 | Cross-campus data mix-up (item in wrong campus) | Medium | High | Campus from registry (not form), API check, composite FK, matcher campus filter, tests T-08…T-10 |
| R-4 | PRN lists incomplete/outdated (e.g., other batches missing) | Medium | Medium | Admin can add/import PRNs with audit; unknown PRN gets generic failure and a "contact desk" help text |
| R-5 | Two frontends exceed team capacity | Medium | Medium | Shared tokens/components, vanilla JS, cut admin analytics charts before cutting core flow |
| R-6 | Over-animation hurts performance/usability | Low | Medium | Motion budget, reduced-motion support, test on a low-end phone |
| R-7 | Private details leak through a public endpoint | Low | High | Separate serializers, automated leak tests, code review checklist |
| R-8 | Claim approval partially applied | Low | High | Single transaction/stored procedure, rollback tests |
| R-9 | Low adoption / desk staff don't use Admin Portal | Medium | High | Short training, make desk workflow faster than paper, pilot with one class |
| R-10 | No hosting available at viva time | Medium | Medium | Docker Compose laptop demo + screenshots/video backup |
| R-11 | Personal data handling concerns (PRN, phone, email) | Medium | Medium | Collect minimum, restrict admin access, retention rules, institutional approval before pilot |
| R-12 | Schedule slip during exams | Medium | Medium | Front-load core flow, freeze scope at week 7, keep stretch items optional |
| R-13 | C backend requirement enforced by faculty | Low | Medium | Python chosen; fallback to C module (matcher/CLI) via subprocess or CGI |
| R-14 | Matcher noise (many weak suggestions) | Medium | Low | Hard category filter, tunable threshold, show breakdown |

## 2. Assumptions

| ID | Assumption |
|---|---|
| A-1 | Team of 3–4 students, ~10 weeks, part-time. |
| A-2 | Students may **browse** both campus sections but may **report, claim and receive matches only in their own campus** (derived from PRN registry). |
| A-3 | Frontends use HTML + Tailwind + vanilla JS (no React/Vue). |
| A-4 | Item images are stored on the server disk (Cloudinary optional later); one image per report. |
| A-5 | Notifications are in-app only in v1; email delivery comes later using the email data file. |
| A-6 | The two PRN Excel files are the authoritative list of student accounts for v1: Bibwewadi 582 PRNs, Kondhwa 513 PRNs, all 10-digit, unique, no overlap. |
| A-7 | Staff accounts (security, campus admin, super admin) are created manually by the super admin, not from PRN lists; they log in with a staff username. |
| A-8 | Found items unclaimed for 90 days are flagged for admin review; actual disposal policy comes from the institution. |
| A-9 | Deployment is a single VM or a laptop-based demo. |
| A-10 | Email is **not** used for login; email data (arriving later) is stored against the PRN and must contain the same 10 digits as the PRN. |
| A-11 | Initial credential rule: a user with `password_hash = NULL` can sign in only with PRN as password and is forced to change it. |
| A-12 | UI language is English. |
| A-13 | Success-metric targets (activation, recovery rate) are pilot targets, not commitments. |
| A-14 | The project follows institutional data policy and general data-protection principles (DPDP Act 2023: minimal data, purpose limitation); formal legal review is out of scope. |
| A-15 | A found item is physically held by the finder or at the campus desk; **handover always happens at the item's campus desk**. |
| A-16 | One student belongs to exactly one campus at a time; a campus change is an admin action recorded in audit logs. |

## 3. Dependencies

| Type | Dependency | Owner | Needed by |
|---|---|---|---|
| Data | `Kondhwa_PRN.xlsx`, `Bibwewad_PRN.xlsx` (received) | Student/team | Sprint 0 |
| Data | Email/name data file per PRN | Student/team | Post-v1 (nice to have) |
| Data | Location lists for both campuses | Campus admin/team | Sprint 2 |
| People | Security desk staff for UAT and handover | Campus admin | Sprint 6 |
| Software | Python 3.12, MySQL 8, Nginx, Node (Tailwind build only) | Team | Sprint 0 |
| Infra | Server/VPS or laptop for demo | Team | Sprint 9 |
| Approval | Institutional OK to use PRNs in a pilot | Faculty/admin | Before real import |

## 4. Open Questions

| ID | Question | Suggested option |
|---|---|---|
| Q-1 | Should students be able to browse the other campus, or only their own? | Allow browse-only (A-2); toggle with `ALLOW_OTHER_CAMPUS_BROWSE` |
| Q-2 | The example PRN used in the original requirement note (`1251071045`) is **not present** in either supplied list. Are the lists complete, or are other batches/branches still to come? | Confirm; if more lists exist, import them with the same script |
| Q-3 | How many security/admin staff accounts per campus, and who creates them? | Super admin creates via CLI/Admin Portal |
| Q-4 | What is the official disposal/retention policy for unclaimed items? | 90-day flag, then admin decision |
| Q-5 | Will the email file also contain student names? | If yes, auto-fill profile names to cut onboarding time |
| Q-6 | Can a student report a found item and keep it, or must it go to the desk within a time limit? | Allow custody `WITH_FINDER` for 24 h, then nudge to hand over |
| Q-7 | Should found items be visible to everyone, or hidden until a lost report exists? | Visible, with private details hidden |
| Q-8 | Where will the system be hosted for the viva? | Local Docker demo + optional VPS |
| Q-9 | Do students who study at both campuses need access to both? | Admin can change campus; no dual-campus accounts in v1 |
| Q-10 | Is a C component specifically required, or is Python acceptable end-to-end? | Python-only; C module as fallback (R-13) |
