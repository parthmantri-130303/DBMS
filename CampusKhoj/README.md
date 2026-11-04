# CampusKhoj (कॅम्पसखोज)

> **Two-Campus (Kondhwa + Bibwewadi) Lost & Found Management System**  
> *Course Project for Database Management Systems (DBMS) — Built to production-grade demo state.*

---

## 1. Project Overview & System Architecture

**CampusKhoj** is a centralized lost-and-found system engineered specifically for multi-campus institutions. Designed for **Vishwakarma Institute of Technology (VIT)** across its **Kondhwa** and **Bibwewadi** campuses, the system solves the operational chaos of misplaced valuables, campus isolation, fraudulent claiming, and unverified handovers.

### Dual-Portal Topology
CampusKhoj runs two distinct frontends powered by a single high-performance Python/Flask REST API and MySQL 8 database:
1. **Student Portal (`student-portal/`)**: Mobile-first responsive web application for students. Authenticated exclusively via **PRN** (Permanent Registration Number). Enforces forced password change on first login, profile setup, two-campus partitioned search, lost/found report submission with camera/file image upload, match suggestion review, multi-step ownership claims with verification Q&A, and real-time timeline tracking.
2. **Admin Portal (`admin-portal/`)**: Desktop-first operations command center for Campus Security Desks and Administrators. Provides consolidated KPI dashboards with real-time SVG charts (zero external CDN dependency), searchable item repositories with streaming CSV export, 3-column claim adjudication queue, verification question management, physical handover recording, student account administration (lockout resets, password resets), batch PRN registry ingestion, and an immutable audit trail.

```
                            ┌─────────────────────────────────────────┐
                            │               MySQL 8.0                 │
                            │  - 17 Normalized Tables                 │
                            │  - Composite FKs (Location, Campus)     │
                            │  - Generated Unique Active Claim Key    │
                            │  - 4 ACID Triggers + Stored Procedures  │
                            │  - 8 Materialized/Analytical Views      │
                            └────────────────────▲────────────────────┘
                                                 │ Raw Parameterized SQL
                                                 │ (mysql-connector pool)
                                                 │
                            ┌────────────────────┴────────────────────┐
                            │            Flask REST API               │
                            │  - JWT RBAC (Scope & Portal Bound)      │
                            │  - Sliding Window Rate Limiting         │
                            │  - WebP Image Optimization & EXIF Strip │
                            │  - Weighted Rule-based Matchmaker       │
                            │  - Strict Privacy Redaction Serializer  │
                            └──────────────▲───────────────────▲──────┘
                                           │                   │
                  REST API (JSON)          │                   │ REST API (JSON)
          ┌────────────────────────────────┴──┐             ┌──┴────────────────────────────────┐
          │     Student Portal (Vanilla JS)   │             │     Admin Portal (Vanilla JS)     │
          │  - Mobile-first, Bottom Nav       │             │  - Desktop-first, Sidebar Nav     │
          │  - Kondhwa & Bibwewadi Tabs       │             │  - KPI Count-Up & Inline SVG      │
          │  - Animated Vertical Timeline     │             │  - 3-Column Claim Review Station  │
          │  - Palette: Cream, Forest, Saffron│             │  - Palette: Charcoal Dark Theme   │
          └───────────────────────────────────┘             └───────────────────────────────────┘
```

---

## 2. Hard Constraints & Business Rules (Guaranteed)

- **Pure Python Backend**: Python 3.11 + Flask. Raw parameterized queries using `mysql-connector-python` connection pooling. **Zero ORM** — all SQL transactions, locking semantics, and constraints are explicit.
- **Strict Database Integrity**: MySQL 8 composite foreign keys `(location_id, campus_id)` on `locations(location_id, campus_id)` prevent cross-campus anomalies at the database engine level.
- **PRN-Only Student Identity**: Students log in using only their 10-digit PRN. On initial import, `password_hash IS NULL`. The student logs in using their PRN as their temporary password, receives a scoped token (`scope="pwd_change"`), and is forced to change their password before profile completion or dashboard access. The PRN is never hashed or stored as a password.
- **Campus Isolation Boundary**: Students can publicly browse items from both campuses, but can **report, claim, and match items exclusively within their enrolled campus**. Any cross-campus write attempt triggers HTTP 403 `WRONG_CAMPUS` and is blocked by composite foreign keys.
- **Single Active Claim Rule**: A student cannot file multiple competing active claims on the same found item. Enforced via generated virtual column `active_key` and unique index `uq_claim_active`.
- **Privacy By Design**: Unverified students and public visitors **never** see sensitive fields (`private_details`, `storage_location`, `expected_evidence`, reporter contact numbers). All serialization is filtered through centralized privacy guardrails.
- **Auditable & Atomic Handover**: Claim approval and physical desk handover execute within atomic database transactions (and stored procedure `sp_approve_claim`), updating item statuses, logging timeline milestones, issuing student notifications, and appending immutable audit rows.
- **Institutional Design Tokens**: No AI/futuristic purple or blue gradients, glassmorphism, or neon glows. Built using authentic institutional colors: Warm Cream (`#FAF6EE`), Forest Green (`#1F4D3A`), Saffron (`#E8892B` with dark `#2B2B2B` ink text), Terracotta (`#B8532F`), and Admin Charcoal (`#1E2420`). WCAG 2.2 AA compliant with 44px minimum touch targets and 2px focus rings.

---

## 3. Database Architecture (DBMS Viva Points)

### Schema Highlights (`database/schema.sql`)
1. **Locations & Composite Foreign Key**:
   ```sql
   CREATE TABLE locations (
       location_id INT NOT NULL AUTO_INCREMENT,
       campus_id TINYINT NOT NULL,
       location_name VARCHAR(100) NOT NULL,
       building VARCHAR(100) NOT NULL,
       PRIMARY KEY (location_id, campus_id),
       FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
   );

   -- In lost_items & found_items:
   FOREIGN KEY (location_id, campus_id) 
       REFERENCES locations(location_id, campus_id) ON UPDATE CASCADE
   ```
   *Why for Viva*: If a student tries to submit an item with `campus_id = 1` (Kondhwa) and `location_id = 11` (CS Lab 1 in Bibwewadi), MySQL immediately raises Error 1452: *Cannot add or update child row: foreign key constraint fails*.

2. **Stored Generated Column for Single Active Claim Uniqueness (`active_key`)**:
   ```sql
   active_key TINYINT GENERATED ALWAYS AS (
       CASE WHEN claim_status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED') THEN 1 ELSE NULL END
   ) STORED,
   CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)
   ```
   *Why for Viva*: In MySQL 8, generated columns can be `VIRTUAL` (computed on read) or `STORED` (computed on write and persisted to disk). We define `active_key` as a **stored generated column** so MySQL indexes the generated value directly. When a claim is active, `active_key = 1`, making `(found_id, claimant_id, 1)` unique and enforcing at most one active claim per student per item. When a claim reaches `REJECTED`, `COMPLETED`, or `CANCELLED`, `active_key` evaluates to `NULL`. Since the SQL standard dictates that `NULL != NULL` in unique indexes, history is preserved without blocking future legitimate claims.

3. **Stored Procedure with ACID Rollback (`sp_approve_claim`)**:
   - Location: `database/procedures.sql`
   - Atomically updates target claim to `APPROVED`.
   - Transitions found item to `CLAIMED`.
   - Transitions linked lost report to `CLAIMED`.
   - Automatically rejects competing pending claims with reason: *"Another claim on this item was approved"*.
   - Records timeline events, notifications, and audit log entries.
   - Contains `DECLARE EXIT HANDLER FOR SQLEXCEPTION` executing `ROLLBACK;` on disk or constraint errors.

4. **Triggers (`database/triggers.sql`)**:
   - `trg_claims_status_audit`: Automatically writes an audit row whenever `claim_status` changes, even from direct SQL updates.
   - `trg_lost_status_event` & `trg_found_status_event`: Ensures state transitions record public/private timeline events.
   - `trg_users_pwd_change`: Records cryptographic audit proof when a student transitions from default PRN credential to custom password.

5. **Analytical Views (`database/views.sql`)**:
   - `v_active_lost`, `v_active_found` (redacts confidential private details).
   - `v_pending_claims`, `v_dashboard_stats`, `v_top_locations`, `v_top_categories`, `v_monthly_trend`, `v_campus_comparison`.

### Verification, QR Passport & Noticeboard Features
1. **Digital QR Claim Pickup Passport (`GET /api/v1/claims/<id>/passport`)**:
   - Issued exclusively to claimants whose claim status is `APPROVED`.
   - Generates a tamper-evident cryptographic security token:
     $$\text{sec\_sig} = \text{HMAC-SHA256}(\text{JWT\_SECRET}, \text{"CK-PASSPORT:"} \mathbin{\Vert} \text{claim\_id} \mathbin{\Vert} \text{claimant\_prn} \mathbin{\Vert} \text{found\_id})[0:16]$$
   - Returns embedded QR payload `CK-VERIFY:<claim_id>:<prn>:<signature>` and passport code `CK-PASSPORT-<claim_id>-<signature>`.
   - Desk staff scan or verify the passport via `POST /api/v1/admin/claims/verify-passport`. The endpoint verifies the HMAC signature, confirms status is `APPROVED`, enforces campus isolation, and strictly rejects unsigned or plain numeric codes.
2. **Printable Noticeboard Poster Data (`GET /api/v1/items/<type>/<id>/poster-data`)**:
   - Generates structured metadata and a QR code pointing directly to the item detail page for students to print physical noticeboard flyers.
   - For found items, strictly scrubs `private_details`, `storage_location`, and reporter identity to ensure public posters never leak verification secrets.
3. **Database-Backed SMS & WhatsApp Simulator (`GET /api/v1/me/messages`)**:
   - Backed by the ACID-compliant `message_outbox` table. Messages are committed within the same transaction as item events and approvals (rolling back if the event fails).
   - Displays simulated alerts with masked phone numbers (`+91 98****2255`) and transparently indicates "Simulated: no real SMS or WhatsApp is sent" in the student drawer.

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.11+
- MySQL 8.0 (Local service or Docker)
- Modern web browser (Chrome, Edge, Firefox, Safari)

### Option A: Local Setup (Recommended for Development)

#### 1. Setup Database
Open MySQL command prompt or Workbench:
```sql
CREATE DATABASE campuskhoj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Execute SQL scripts in order:
```bash
mysql -u root -p campuskhoj < database/schema.sql
mysql -u root -p campuskhoj < database/seed.sql
mysql -u root -p campuskhoj < database/views.sql
mysql -u root -p campuskhoj < database/triggers.sql
mysql -u root -p campuskhoj < database/procedures.sql
```

#### 2. Setup Backend
```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```
Ensure `.env` matches your local MySQL credentials:
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=campuskhoj
JWT_SECRET=supersecretcampuskhojjwtkey32byteslong!
```

#### 3. Run Automated Tests
Verify all 30 tests pass before running:
```bash
python -m tests.run_all
```

#### 4. Import Student PRN Registry
Import the official student lists (1,095 students across both campuses):
```bash
# Dry run first to verify clean records:
python manage.py import-prn --file "../student_data/Kondhwa PRN.xlsx" --campus KON --dry-run
python manage.py import-prn --file "../student_data/Bibwewad PRN.xlsx" --campus BIB --dry-run

# Live import:
python manage.py import-prn --file "../student_data/Kondhwa PRN.xlsx" --campus KON
python manage.py import-prn --file "../student_data/Bibwewad PRN.xlsx" --campus BIB
```

#### 5. Seed Realistic Demo Workflow Data
Populate realistic lost reports, found items, matches, verification Q&A, and handovers for both campuses using real imported PRNs:
```bash
python manage.py seed-demo
```

> **Production Note**: Before production deployment, purge the default demo staff accounts:
> ```bash
> python manage.py purge-demo-staff
> # Then create secure production administrators:
> python manage.py create-admin --username desk_kon --name "Kondhwa Desk" --role CAMPUS_ADMIN --campus KON --password "<strong_unique_password>"
> ```

#### 6. Start the API Server
```bash
python run.py
# API health check at http://127.0.0.1:5000/health
```

#### 7. Launch Portals
In a separate terminal, serve the frontends:
```bash
# From the project root directory:
python -m http.server 3000
```
- **Student Portal**: [http://localhost:3000/student-portal/](http://localhost:3000/student-portal/)
- **Admin Portal**: [http://localhost:3000/admin-portal/](http://localhost:3000/admin-portal/)

---

### Option B: Docker Compose
```bash
docker-compose up --build
```
This spins up MySQL 8 with all schema, views, triggers, and procedures pre-loaded, plus the Flask REST API on `http://localhost:5000`.

---

## 5. Pre-Configured Demo Credentials (Demo Database Only)

> [!IMPORTANT]
> **Demo Database Only**: The student credentials below apply exclusively to local academic evaluations and rehearsal on the demo seed database (`seed-demo`). In production environments, PRNs authenticate via institutional identity/first-login temporary tokens, and staff accounts must be initialized via `python manage.py create-admin` with unique NIST-compliant passwords.

| Role | Portal | Username / PRN | Password | Campus | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Enrolled Student** | Student Portal | `1251150353` | `Student@123` *(Demo DB Only)* | Kondhwa | Aarav Sharma (Active Dell laptop claim) |
| **Enrolled Student** | Student Portal | `1251030471` | `Student@123` *(Demo DB Only)* | Bibwewadi | Ananya Kulkarni (Approved Titan watch claim) |
| **New Student (1st Login)**| Student Portal | `1251150269` | `1251150269` | Kondhwa | Real student from registry, triggers forced password change |
| **Super Admin** | Admin Portal | `admin` | `<STAFF_PASSWORD>` | Both / Central | Full oversight across all campuses |
| **Kondhwa Desk Staff** | Admin Portal | `admin_kon` | `<STAFF_PASSWORD>` | Kondhwa | Campus Desk Administrator |
| **Bibwewadi Desk Staff** | Admin Portal | `admin_bib` | `<STAFF_PASSWORD>` | Bibwewadi | Campus Desk Administrator |
| **Security Guard** | Admin Portal | `sec_kon` | `<STAFF_PASSWORD>` | Kondhwa | Security Desk Operator |

---

## 6. Five-Minute Viva Demo Script (Both Campuses)

### **Minute 1: Student First Login & Forced Password Change**
1. Open the **Student Portal** at [http://localhost:3000/student-portal/login.html](http://localhost:3000/student-portal/login.html).
2. Enter real imported PRN `1251150269` and Password `1251150269` (initial temporary credential).
3. Click **Sign In**. Notice immediate redirect to `change-password.html`.
4. Try typing `1251150269` as the new password. Notice the red validation tick: *Cannot equal or contain your PRN*.
5. Enter a strong password: `Student#2026` (all 4 green checkmarks tick live).
6. Click **Set New Password**. Notice seamless redirect to **Profile Setup** (`profile-setup.html`).
7. Enter Full Name: `Rohit Verma`, Phone: `9822334455`, Optional Email: `rohit.1251150269@vit.edu`.
8. Click **Complete Setup** &rarr; arrives on the student dashboard with personalized greeting and Kondhwa campus badge.

### **Minute 2: Public Cross-Campus Browsing vs. Campus-Locked Reporting**
1. From the student dashboard, navigate to **Browse Campuses** (`campuses.html`).
2. Switch between the **Kondhwa** and **Bibwewadi** tabs. Notice students can freely view found items in both locations (e.g. Titan Watch in Bibwewadi, Dell Laptop in Kondhwa).
3. Click **Report Lost** (`report-lost.html`).
4. Note that the Location dropdown only lists Kondhwa buildings (Library, Workshop, Canteen).
5. File a report: *"Sony WH-1000XM5 Headphones"*, Category: *Electronics*, Location: *Central Library*, Date: Today.
6. Submit &rarr; report is immediately active with animated milestone 1 on the item timeline.

### **Minute 3: Automatic Rule-Based Matchmaker**
1. Click **Report Found** (`report-found.html`).
2. Enter *"Sony Wireless Headphones"*, Category: *Electronics*, Location: *Central Library*, Color: *Black*, Private Details: *"Left ear cushion has slight tear, serial ends in 9102"*, Custody: *At Security Desk*.
3. Submit &rarr; the backend matchmaker executes immediately.
4. Go to **My Reports** (`my-reports.html`).
5. Open the newly filed Lost report &rarr; notice a **High Confidence Match Card (90% Similarity)** displayed with calculated match breakdown (Category 30 pts, Name 25 pts, Location 20 pts, Date 10 pts).

### **Minute 4: Claim Adjudication & Desk Verification Q&A**
1. Click **Claim This Item** on the matching found report. Enter proof description: *"These are my noise-canceling headphones left in reading cubicle 3."*
2. Now switch to the **Admin Portal** at [http://localhost:3000/admin-portal/login.html](http://localhost:3000/admin-portal/login.html).
3. Log in as `admin_kon` (Password: `<STAFF_PASSWORD>`).
4. Click **Claims Queue** (`claims.html`). Select the active claim.
5. Review the 3-column adjudication screen:
   - Left: Claimant PRN, Name, Phone.
   - Middle: Secret Private Details logged by finder (*serial ends in 9102*).
   - Right: Verification Questions station.
6. Click **Ask Verification Question**. Enter question: *"What unique physical mark or tear is on the ear cushions?"* and Expected Evidence: *"Left ear cushion has a tear"*. Click **Post Question**.
7. In the Student Portal, go to **My Claims** (`my-claims.html`).
8. Notice the claim displays the pending question (with expected evidence strictly hidden).
9. Student answers: *"The left ear cushion has a small 1cm tear near the seam."*

### **Minute 5: Claim Approval, Physical Handover & Audit Trail**
1. Return to the Admin Portal.
2. In the Claims Queue, review the student's answer. Click **Approve Ownership Claim**.
3. Under the hood, MySQL stored procedure `sp_approve_claim` executes atomically:
   - Claim status becomes `APPROVED`.
   - Found item becomes `CLAIMED`.
   - Competing claims are auto-rejected with notice.
   - Transactionally logs `CLAIM_APPROVED` into `message_outbox` with masked phone number.
4. Student arrives at the Kondhwa security desk with their college ID card.
5. Staff enters the student's PRN in the Handover verification box and clicks **Complete Physical Handover**.
6. Item status transitions to `HANDED_OVER`, lost report transitions to `RETURNED`.
7. Click **Audit Log** (`audit.html`) in the sidebar:
   - Notice the permanent audit trail entries: `CLAIM_APPROVED`, `HANDOVER_COMPLETED` with timestamp, actor `admin_kon`, claimant PRN, and client IP address.

### **Bonus 30-Second Viva Demo: Simulated SMS / WhatsApp Notification Outbox**
1. In the Student Portal, click the **Messages (💬)** icon in the header or bottom navigation.
2. The smooth slide-in Messages drawer opens in warm CampusKhoj cream/forest theme.
3. Observe simulated SMS/chat alerts (e.g. *Match Found*, *Claim Approved*, *Handover Completed*).
4. Point out the honesty badge: **"Simulated: no real SMS or WhatsApp is sent"**, alongside masked phone numbers (`98****4455`) that protect student privacy.
5. In the Admin Portal, click **Message Log** (`messages.html`) in the sidebar:
   - Shows the examiner the real-time database-backed `message_outbox` table with campus, channel, template code, and masked recipient filters. Demonstrates how transaction rollback guarantees zero orphaned messages.

---

## 7. Manual DevTools Privacy Verification Guide

To prove to your evaluator or examiner that private details never leak across the network:
1. Open Google Chrome or Firefox DevTools (`F12` &rarr; **Network** tab &rarr; Filter by `Fetch/XHR`).
2. Log in as any student (e.g. `1251150353`).
3. Click on any public found item card to open `item-detail.html?type=found&id=X`.
4. In DevTools, click on the API request `GET /api/v1/found/X` and inspect the **Response** tab.
5. Verify the following:
   ```json
   {
     "item": {
       "found_id": 1,
       "item_name": "Dell Laptop with Charger",
       "category_name": "Electronics",
       "campus_name": "Kondhwa Campus",
       "location_name": "Central Library Kondhwa",
       "brand": "Dell",
       "color": "Black",
       "description": "Found on study table in library.",
       "private_details": null,
       "storage_location": null,
       "user_id": null
     }
   }
   ```
   - `private_details` is strictly `null`.
   - `storage_location` is strictly `null`.
   - `user_id` (finder ID) is strictly `null` (prevents finder harassment).
6. Next, inspect `GET /api/v1/claims/Y` on `my-claims.html`:
   - Verification questions contain `"question": "..."` and `"answer": "..."`.
   - `expected_evidence` is strictly omitted from the payload.
   *(These checks prove that data security is enforced at the backend serialization layer and cannot be bypassed by inspecting client DOM or scripts).*

---

## 8. Automated Test Suite (30 Comprehensive Tests)

Run the entire automated verification suite with one command:
```bash
cd backend
python -m tests.run_all
```

### Test Coverage Matrix
| ID | Test Category | Description | Status |
| :--- | :--- | :--- | :--- |
| **T-01** | Auth | Login with unregistered PRN returns HTTP 401 generic error | Passed |
| **T-02** | Auth | Valid PRN with initial PRN credential returns `scope="pwd_change"` | Passed |
| **T-03** | Auth | Token with `pwd_change` scope blocked from accessing `/lost` (403) | Passed |
| **T-04** | Auth | Password equal to PRN, containing PRN, or < 8 chars rejected (400) | Passed |
| **T-05** | Auth | After password change, old PRN as password strictly rejected | Passed |
| **T-06** | Auth | 5 consecutive failed logins triggers lockout on 6th attempt (423) | Passed |
| **T-07** | Auth | Student token attempting to call `/api/v1/admin/*` returns 403 | Passed |
| **T-08** | Campus Rules | Kondhwa student reporting Bibwewadi location rejected (`WRONG_CAMPUS`) | Passed |
| **T-09** | Campus Rules | Kondhwa student attempting to claim Bibwewadi item rejected (403) | Passed |
| **T-10** | Campus Rules | Matchmaker calculates 0% score across different campuses | Passed |
| **T-11** | Campus Rules | Cross-campus public lost/found browsing is permitted | Passed |
| **T-12** | Validation | Future incident date in lost report rejected (400) | Passed |
| **T-13** | Validation | Executable or non-image upload rejected with 415 | Passed |
| **T-14** | Privacy | Public `GET /found/<id>` strictly omits `private_details` & `storage_location` | Passed |
| **T-15** | Integrity | Submitting second active claim on same item rejected (409 Conflict) | Passed |
| **T-16** | Integrity | Student claiming an item they reported as found rejected (409) | Passed |
| **T-17** | Privacy | Student fetching claim detail never receives `expected_evidence` | Passed |
| **T-18** | ACID | Forced database exception during claim approval triggers full rollback | Passed |
| **T-19** | Workflow | Recording handover on non-approved claim rejected (409 Conflict) | Passed |
| **T-20** | Timeline | Non-owners see only `is_public=1` timeline events; owners/staff see all | Passed |
| **T-21** | Workflow | Handover updates claim to `COMPLETED` and writes audit log | Passed |
| **T-22** | Validation | Profile update with email digits mismatching PRN rejected (400) | Passed |
| **T-23** | Rate Limit | Sliding window rate limiter rejects excessive requests with 429 | Passed |
| **T-24** | Security | IDOR protection: Student editing another student's report returns 403 | Passed |
| **T-25** | Registry | Batch PRN import validates 10 digits and registers `must_change_password=1`| Passed |
| **J-01** | Journey | Full Journey 1: First login -> forced pwd change -> profile setup | Passed |
| **J-02** | Journey | Full Journey 2 & 3: Report lost -> report found -> matchmaker trigger | Passed |
| **J-03** | Journey | Full Journey 4: Claim filing -> desk verification Q&A -> student answers | Passed |
| **J-04** | Journey | Full Journey 5 & 6: Claim approval -> physical handover -> audit entry | Passed |
| **J-05** | Journey | Full Journey 7: Cross-campus attack attempt strictly blocked (403) | Passed |

---

## 9. DBMS Viva & Oral Examination Reference Sheet

When presenting CampusKhoj to professors and evaluators, highlight these specific relational database design choices:

1. **Why not handle campus validation purely in application code?**  
   *Answer*: Application checks can be bypassed by developer bugs, direct SQL queries, or API misconfigurations. By defining composite foreign key `FOREIGN KEY (location_id, campus_id) REFERENCES locations(location_id, campus_id)` and check constraints in MySQL, the database engine guarantees data integrity regardless of how records are inserted.

2. **How does the system enforce "one active claim per student per item" without blocking future legitimate claims?**  
   *Answer*: We use a MySQL 8 stored generated column with a composite unique index:
   ```sql
   active_key TINYINT GENERATED ALWAYS AS (
       CASE WHEN claim_status IN ('PENDING', 'UNDER_REVIEW', 'APPROVED') THEN 1 ELSE NULL END
   ) STORED,
   CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)
   ```
   Since SQL standard dictates that `NULL != NULL` in unique constraints, rejected or cancelled claims evaluate to `NULL` and do not trigger unique constraint collisions, while active claims evaluate to `1` and reject duplicates via `(found_id, claimant_id, 1)`.

3. **How does `sp_approve_claim` ensure atomic consistency?**  
   *Answer*: It wraps the approval, the found item status transition, the lost report status transition, the bulk rejection of competing claims, notifications, and audit rows inside a single `START TRANSACTION ... COMMIT` block, backed by `DECLARE EXIT HANDLER FOR SQLEXCEPTION` executing `ROLLBACK`. If any step fails, the entire batch rolls back, preventing orphaned claims or items stuck in inconsistent intermediate states.

4. **How are confidential item attributes protected from leaking?**  
   *Answer*: Sensitive attributes (`private_details`, `storage_location`, `expected_evidence`, reporter contact details) are stored in dedicated columns and excluded from public database views (`v_active_lost`, `v_active_found`). Furthermore, the backend serializer enforces role-based masking: only verified desk operators or the original reporter receive unmasked payloads.

---

## 10. Submission Artifacts & Hardening Evidence

All academic submission documents, diagrams, audit reports, and query outputs are available in the repository:

| Artifact | Location | Description |
|---|---|---|
| **Comprehensive Project Report** | [`docs/submission/REPORT.md`](docs/submission/REPORT.md) | Full DBMS project report with problem statement, architecture, schema, normalization, and evaluation |
| **Presentation Slides** | [`docs/submission/SLIDES.md`](docs/submission/SLIDES.md) | 14 presentation slides with complete speaker notes for viva demonstration |
| **Viva Examination Q&A** | [`docs/submission/VIVA_QA.md`](docs/submission/VIVA_QA.md) | 30 grounded questions and answers across schema, normalization, optimization, and security |
| **Test Execution & Traceability** | [`docs/submission/test_results.md`](docs/submission/test_results.md) | 35 automated tests (100% passing) with FR-1..FR-30 requirements traceability matrix |
| **Normalization Analysis** | [`docs/submission/normalization.md`](docs/submission/normalization.md) | 1NF $\rightarrow$ 2NF $\rightarrow$ 3NF $\rightarrow$ BCNF proofs, candidate keys, and intentional denormalization justifications |
| **Live Relational Schema** | [`docs/submission/relational_schema.md`](docs/submission/relational_schema.md) | Auto-extracted schema tables, types, keys, and DDL directly from live MySQL 8 `INFORMATION_SCHEMA` |
| **Live ER Diagram** | [`docs/submission/ER_diagram.md`](docs/submission/ER_diagram.md) | Complete Mermaid ER diagram and relational constraint documentation |
| **Viva Queries with Output** | [`docs/submission/queries_with_output.md`](docs/submission/queries_with_output.md) | Live execution outputs of all 6 viva demonstration SQL queries |
| **EXPLAIN Plan Analysis** | [`docs/explain_plans.md`](docs/explain_plans.md) | MySQL 8 `EXPLAIN FORMAT=TREE` analysis of the 5 heaviest production queries |
| **Security Audit Report** | [`docs/security_report.md`](docs/security_report.md) | Static AST scan (`bandit`), vulnerability audit (`pip-audit`), and AST SQL parameterization verification |
| **Load Test Benchmark** | [`docs/load_test.md`](docs/load_test.md) | 100-user concurrent load test achieving 293 RPS and 228 ms median latency |
| **Accessibility Audit** | [`docs/a11y_report.md`](docs/a11y_report.md) | WCAG 2.2 AA audit via `axe-core` across 10 portal views (0 critical violations) |
| **Browser QA Screenshots** | [`docs/screenshots/`](docs/screenshots/) | 35 high-resolution screenshots across Desktop (1280px), Mobile (390px), and Admin portals |

---

## 11. Quick Start & One-Click Viva Demo

To run the entire system in one command:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1
```
This automatically checks MySQL connectivity, starts the Flask API on port 5000, starts the web portal server on port 3000, and opens both the Student and Admin portals in your browser.

### 5-Minute Viva Demo Walkthrough
1. **First-Login Enclave**: Open `http://localhost:3000/student-portal/login.html`. Sign in with unactivated Kondhwa PRN `1251150269` / Password: `1251150269`. Show that the portal locks to `change-password.html` and blocks all other pages. Enter `NewPassword@123`, complete profile setup with matching VIT email `student.1251150269@vit.edu`, and enter dashboard.
2. **Campus Isolation**: Click on the **Bibwewadi** tab. Show that student can browse Bibwewadi items, but report and claim buttons are disabled.
3. **Report Lost & Found**: Submit a lost report for a "Logitech Wireless Mouse" in Kondhwa. Submit a found report with private details (e.g., serial number). Show the animated activity timeline stepper.
4. **Matching Engine**: View the match suggestion card and score breakdown with in-app notification badge.
5. **Claim & Verification**: Submit an ownership claim. In `http://localhost:3000/admin-portal/` (login: `admin_kon` / `<STAFF_PASSWORD>`), review the claim, issue a verification question ("What color is the scroll wheel?"), answer it as student, approve via `sp_approve_claim`, and record physical handover at the desk.

---

## 12. Known Limitations & Phase 2 Roadmap

- **External SMTP / SMS Gateway**: Notifications currently deliver in-app via the notification drawer. Phase 2 will integrate college SMTP for automated email receipts and Twilio/SMS alerts upon claim approval.
- **Dynamic QR Handover**: Handover currently verifies student PRN at the security desk. Phase 2 will introduce dynamic time-expiring QR tokens on the student's mobile screen for barcode scanning at the desk.
- **Biometric / Smartcard Desks**: Integration with campus RFID turnstiles to automatically verify student identity upon physical collection.

---

## 13. License & Credits

Developed for the Database Management Systems (DBMS) coursework at **Vishwakarma Institute of Technology, Pune**.  
Built strictly adhering to the architectural requirements, security constraints, and UI/UX design brief in `Docs/`.

