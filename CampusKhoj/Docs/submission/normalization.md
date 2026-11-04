# Relational Normalization & Functional Dependency Analysis

**Course**: Database Management Systems (DBMS)  
**Project**: CampusKhoj — Two-Campus Lost & Found Relational System  
**Database**: MySQL 8.0.46 InnoDB  

---

## 1. Executive Summary & Normal Form Achievement

The CampusKhoj relational database schema achieves **Boyce-Codd Normal Form (BCNF)** across all master entities, lookup dictionaries, and event/audit ledgers. Four primary operational relations (`lost_items`, `found_items`, `claims`, `match_suggestions`) are intentionally maintained in **Second Normal Form (2NF)** due to deliberate transitive dependencies on `{campus_id}`. This is an explicit engineering design trade-off that enables MySQL InnoDB's storage engine to enforce kernel-level composite foreign key constraints (`FOREIGN KEY (location_id, campus_id)`) and perform sub-millisecond campus-partitioned query filtering.

| Table Name | Highest Normal Form | Primary / Candidate Keys | Intentional Design Trade-Off & Engineering Justification |
|---|---|---|---|
| `campuses` | BCNF | `{campus_id}`, `{code}`, `{campus_name}` | None — strictly normalized master dictionary. |
| `roles` | BCNF | `{role_id}`, `{role_name}` | None — canonical system role definition. |
| `prn_registry` | BCNF | `{prn}` | None — pristine 10-digit PRN enrollment authority. |
| `users` | BCNF | `{user_id}`, `{prn}`, `{staff_username}`, `{email}` | None — all non-prime attributes functionally depend on candidate superkeys. |
| `categories` | BCNF | `{category_id}`, `{category_name}` | None — item classification lookup. |
| `locations` | BCNF | `{location_id}`, `{campus_id, location_name}` | Composite Superkey `{location_id, campus_id}` exposed to act as composite foreign key target. |
| `lost_items` | 2NF | `{lost_id}` | Contains transitive dependency $\text{lost\_id} \rightarrow \text{location\_id} \rightarrow \text{campus\_id}$ to enforce `(location_id, campus_id)` composite FK. |
| `found_items` | 2NF | `{found_id}` | Contains transitive dependency $\text{found\_id} \rightarrow \text{location\_id} \rightarrow \text{campus\_id}$ to enforce `(location_id, campus_id)` composite FK. |
| `match_suggestions` | 2NF | `{match_id}`, `{lost_id, found_id}` | Includes `{campus_id}` to avoid 3-way cross-joins during real-time matcher execution. |
| `claims` | 2NF | `{claim_id}`, `{found_id, claimant_id, active_key}` | Includes `{campus_id}` for indexing, and `{active_key}` stored generated column to enforce partial uniqueness. |
| `claim_verifications` | BCNF | `{verification_id}` | None — sequential question-and-answer ledger. |
| `claim_messages` | BCNF | `{message_id}` | None — communication exchange ledger. |
| `item_events` | BCNF | `{event_id}` | None — append-only lifecycle event trail. |
| `notifications` | BCNF | `{notification_id}` | None — in-app student and staff alerts. |
| `message_outbox` | BCNF | `{message_id}` | None — atomic SMS/WhatsApp communication outbox. |
| `audit_logs` | BCNF | `{log_id}` | None — append-only regulatory staff audit trail. |
| `login_attempts` | BCNF | `{attempt_id}` | None — time-series credential security tracking. |

---

## 2. Formal Normalization Walkthrough (1NF $\rightarrow$ BCNF)

### Step 1: First Normal Form (1NF)
A relation $R$ is in 1NF if and only if:
1. Every attribute contains only atomic (indivisible) values.
2. There are no repeating groups or multi-valued arrays.
3. Each record is uniquely identifiable by a primary key.

**Verification in CampusKhoj**:
- Free-form comma-separated tags were eliminated; structured categorization is achieved via `category_id` referencing `categories`.
- Contact numbers and emails are scalar `VARCHAR` strings rather than repeating multi-field groups.
- Item events, claims messaging, and verification questions are separated into independent relation rows (`item_events`, `claim_verifications`, `claim_messages`, `message_outbox`) rather than JSON lists or embedded arrays.
- JSON attributes (`audit_logs.details`, `match_suggestions.breakdown`) store structured diagnostic metadata that is never part of relational join keys or search predicates.

### Step 2: Second Normal Form (2NF)
A relation $R$ is in 2NF if and only if:
1. It is in 1NF.
2. Every non-prime attribute is **fully functionally dependent** on the whole candidate key (no partial dependencies on a composite key).

**Analysis of Composite Keys**:
- In `locations`, the primary key is `location_id`. While `{location_id, campus_id}` forms an alternate candidate key, all location attributes (`location_name`, `building`, `floor`, `room_or_spot`, `sort_order`, `is_active`) depend on `location_id` alone.
- In `found_items`, all attributes including spot attributes (`room_no`, `specific_spot`, `custody`) depend on the single primary key `found_id`.
- In `claims`, candidate key `{found_id, claimant_id, active_key}` enforces unicity of active claims. All non-prime attributes (`claim_description`, `claim_status`, `submitted_at`) depend on the surrogate primary key `claim_id`.
- Therefore, no partial functional dependency exists on any non-prime attribute. $\therefore$ The schema is strictly in **2NF**.

### Step 3: Third Normal Form (3NF)
A relation $R$ is in 3NF if and only if:
1. It is in 2NF.
2. No non-prime attribute is transitively dependent on any candidate key (no $X \rightarrow Y \rightarrow Z$ where $X$ is a candidate key and $Y$ is non-prime).

**Transitive Dependency Resolution in Design**:
- *Anti-pattern avoided*: Storing `campus_name` or `building_address` inside `lost_items` would create the transitive dependency:
  $$\text{lost\_id} \rightarrow \text{location\_id} \rightarrow \text{building} \rightarrow \text{campus\_name}$$
  This was resolved by creating distinct normalized entities: `locations` and `campuses`.
- *Anti-pattern avoided*: Storing student name or degree inside `claims` would create:
  $$\text{claim\_id} \rightarrow \text{claimant\_id} \rightarrow \text{name}$$
  This was strictly normalized into `users`.

### Step 4: Boyce-Codd Normal Form (BCNF)
A relation $R$ is in BCNF if and only if for every non-trivial functional dependency $X \rightarrow Y$, **$X$ is a superkey**.

**Case Study: `users` relation**:
- Functional dependencies:
  1. $\text{user\_id} \rightarrow \{\text{prn}, \text{staff\_username}, \text{name}, \text{email}, \text{phone}, \text{role\_id}, \text{campus\_id}, \dots\}$
  2. $\text{prn} \rightarrow \{\text{user\_id}, \text{name}, \text{email}, \dots\}$ (for students)
  3. $\text{staff\_username} \rightarrow \{\text{user\_id}, \text{name}, \text{email}, \dots\}$ (for staff)
  4. $\text{email} \rightarrow \{\text{user\_id}, \text{prn}, \dots\}$
- Every determinant on the left-hand side ($\text{user\_id}$, $\text{prn}$, $\text{staff\_username}$, $\text{email}$) is a **candidate key** protected by a `UNIQUE` constraint.
- $\therefore$ The `users` relation satisfies **BCNF**.

---

## 3. Rigorous Analysis of Functional Dependencies (FDs)

### A. Entity: `locations`
- Attributes: $\{ \text{location\_id}, \text{campus\_id}, \text{location\_name}, \text{building}, \text{floor}, \text{description} \}$
- Functional Dependencies:
  $$F_1: \text{location\_id} \rightarrow \{ \text{campus\_id}, \text{location\_name}, \text{building}, \text{floor}, \text{description} \}$$
  $$F_2: \{ \text{campus\_id}, \text{location\_name} \} \rightarrow \{ \text{location\_id}, \text{building}, \text{floor}, \text{description} \}$$
- Candidate Keys:
  $$CK_1 = \{ \text{location\_id} \}$$
  $$CK_2 = \{ \text{campus\_id}, \text{location\_name} \}$$
  $$SK_1 = \{ \text{location\_id}, \text{campus\_id} \} \quad (\text{Composite Superkey})$$
- **BCNF Proof**: The determinants in $F_1$ and $F_2$ are candidate keys. $SK_1$ is a valid superkey created to serve as the target for the composite foreign key.

### B. Entity: `lost_items` & `found_items`
- Attributes of `found_items`: $\{ \text{found\_id}, \text{user\_id}, \text{campus\_id}, \text{category\_id}, \text{location\_id}, \text{item\_name}, \text{brand}, \text{color}, \text{description}, \text{date\_found}, \text{custody}, \text{status} \}$
- Functional Dependencies:
  $$F_1: \text{found\_id} \rightarrow \{ \text{user\_id}, \text{campus\_id}, \text{category\_id}, \text{location\_id}, \dots \}$$
  $$F_2: \text{location\_id} \rightarrow \text{campus\_id} \quad (\text{inherited from } \text{locations})$$
- Determinants: $\{ \text{found\_id} \}$ is the Primary Key. However, because $F_2$ exists and $\text{location\_id}$ is not a superkey of `found_items`, `campus_id` introduces a transitive functional dependency ($\text{found\_id} \rightarrow \text{location\_id} \rightarrow \text{campus\_id}$).
- **Normal Form Classification**: `found_items` and `lost_items` strictly satisfy **2NF**. They do not satisfy 3NF (nor BCNF) because of the transitive functional dependency $\text{found\_id} \rightarrow \text{location\_id} \rightarrow \text{campus\_id}$ where $\text{location\_id}$ is not a superkey. This deliberate design trade-off is implemented in the physical schema to allow MySQL InnoDB to enforce cross-campus integrity at the storage engine layer via `FOREIGN KEY (location_id, campus_id) REFERENCES locations(location_id, campus_id)`.

---

## 4. Intentional Denormalizations & Academic Justifications

### 1. `lost_items.campus_id` and `found_items.campus_id`
- **Theory**: The campus can be inferred transitively via $\text{item} \rightarrow \text{location} \rightarrow \text{campus}$.
- **Engineering Justification**: Standard foreign keys in SQL cannot inspect multi-hop transitive paths during `INSERT`. If `lost_items` did not include `campus_id`, a malicious client could insert an item on Campus 1 with a `location_id` belonging to Campus 2. By including `campus_id` and applying:
  ```sql
  CONSTRAINT fk_lost_location_campus 
      FOREIGN KEY (location_id, campus_id) 
      REFERENCES locations(location_id, campus_id)
  ```
  MySQL InnoDB enforces cross-campus geographic integrity at the database kernel level with zero trigger overhead.

### 2. `claims.active_key` (Stored Generated Column)
- **Theory**: Derived state based on `claim_status` violates strict 3NF attribute independence.
- **Engineering Justification**:
  ```sql
  active_key TINYINT GENERATED ALWAYS AS (
      CASE WHEN claim_status IN ('PENDING','UNDER_REVIEW','APPROVED') THEN 1 ELSE NULL END
  ) STORED
  ```
  MySQL does not support partial unique indexes (e.g., `WHERE status = 'ACTIVE'`). By projecting active statuses to `1` and inactive statuses (`REJECTED`, `COMPLETED`, `CANCELLED`) to `NULL`, the compound unique index:
  ```sql
  CONSTRAINT uq_claim_active UNIQUE (found_id, claimant_id, active_key)
  ```
  relies on the ANSI SQL standard that multiple `NULL` values do not conflict. This guarantees at the storage engine level that a student can never submit two competing active claims for the same found item.

### 3. `claims.campus_id` & `match_suggestions.campus_id`
- **Engineering Justification**: High-frequency dashboard filtering and campus-admin authorization queries require partitioning by campus. Storing `campus_id` directly avoids joining through `found_items` or `lost_items`, transforming an expensive 3-way join into an index range scan on `idx_claims_search (campus_id, claim_status, submitted_at)`.

