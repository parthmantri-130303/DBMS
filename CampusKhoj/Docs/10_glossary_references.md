<!-- File: 10_glossary_references.md -->
# CampusKhoj — Glossary & References

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Glossary

| Term | Definition |
|---|---|
| **CampusKhoj** | Project name; *khoj* = search/find. Earlier working title: FindBack. |
| **PRN** | Permanent Registration Number — 10-digit student identifier used as the student username; first-time password until changed. |
| **Kondhwa / Bibwewadi** | The two campuses; each has its own locations, items, desk and handover. |
| **PRN registry** | Table of allowed student PRNs and their campus, imported from the Excel lists. |
| **Student Portal** | Website for students (browse, report, claim, timeline). |
| **Admin Portal** | Separate website for security staff and admins. |
| **First-login flow** | PRN/PRN sign-in → restricted token → forced password change → profile setup. |
| **Restricted (pwd_change) token** | Short-lived JWT that only allows changing the password. |
| **Scope** | JWT claim: `pwd_change` or `full`. |
| **Lost complaint / lost report** | A student's record of a missing item. |
| **Found report** | Record of an item someone found. |
| **Custody** | Where a found item physically is: `WITH_FINDER` or `AT_DESK`. |
| **Private details** | Staff-only identifying information of a found item, used for verification. |
| **Claim** | A student's request to receive a found item. |
| **Verification** | Staff questions and the claimant's answers proving ownership. |
| **Handover** | Recorded physical return of the item at the campus desk. |
| **Timeline** | Ordered list of `item_events` showing an item's or claim's history. |
| **Public event** | Timeline event visible on public item pages. |
| **Match suggestion** | System-generated possible lost↔found pair with a score. |
| **Matching score** | 0–100 rule-based similarity (category, name, colour, location, date). |
| **RBAC** | Role-Based Access Control. |
| **JWT** | JSON Web Token, signed token carrying identity and role. |
| **bcrypt** | Slow password-hashing function. |
| **IDOR** | Insecure Direct Object Reference — accessing others' records by changing an ID. |
| **ER diagram** | Entity-Relationship diagram of the database. |
| **1NF / 2NF / 3NF / BCNF** | Normal forms removing redundancy and update anomalies. |
| **Composite foreign key** | FK on two columns (e.g., `location_id, campus_id`) that enforces campus consistency. |
| **Generated column** | Column computed by the database; here used to enforce "one active claim". |
| **View / Trigger / Transaction** | Saved query / automatic action on data change / all-or-nothing group of statements. |
| **Audit log** | Immutable record of sensitive actions. |
| **DPDP Act 2023** | India's Digital Personal Data Protection Act, 2023. |
| **WCAG 2.2 AA** | Web accessibility guideline level targeted. |
| **RPO / RTO** | Recovery Point / Recovery Time Objective. |
| **UAT** | User Acceptance Testing. |

## 2. References

*Compiled from general technical knowledge; no live sources were queried while writing these documents. Verify links before citing them in the final report.*

1. Course specification: *FindBack — Campus Lost & Found Management System, CP Project Documentation* (uploaded Word document).
2. Supplied data: `Kondhwa_PRN.xlsx` (513 PRNs), `Bibwewad_PRN.xlsx` (582 PRNs).
3. OWASP Top 10 — https://owasp.org/www-project-top-ten/
4. OWASP Cheat Sheet Series (Authentication, Password Storage, File Upload) — https://cheatsheetseries.owasp.org/
5. NIST SP 800-63B, Digital Identity Guidelines: Authentication — https://pages.nist.gov/800-63-3/sp800-63b.html
6. W3C, Web Content Accessibility Guidelines (WCAG) 2.2 — https://www.w3.org/TR/WCAG22/
7. Flask documentation — https://flask.palletsprojects.com/
8. MySQL 8.0 Reference Manual (InnoDB, foreign keys, generated columns, triggers, FULLTEXT) — https://dev.mysql.com/doc/refman/8.0/en/
9. PyJWT documentation — https://pyjwt.readthedocs.io/
10. Tailwind CSS documentation — https://tailwindcss.com/docs
11. MDN Web Docs: Web Animations API, `prefers-reduced-motion` — https://developer.mozilla.org/
12. Digital Personal Data Protection Act, 2023 (India) — official text via the Government of India (meity.gov.in).
13. Elmasri & Navathe, *Fundamentals of Database Systems* — ER modelling and normalization.
