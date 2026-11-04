# CampusKhoj Defect Log (BUGS.md)

| Bug ID | Severity | Title | Status | Fixed In Regression Test |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-001** | S2 | Missing parameter count in matcher notification insert queries | **FIXED** | `test_journey_2_and_3_report_lost_and_found_trigger_matcher` |
| **BUG-002** | S2 | Location ID mismatch in `manage.py seed-demo` (Kondhwa 102 vs 1) | **FIXED** | `test_live_mysql.py` |
| **BUG-003** | S2 | Generated column `active_key` passed explicitly in seed SQL | **FIXED** | `test_live_mysql.py` |
| **BUG-004** | S3 | Google Fonts @import in `tokens.css` violated self-hosted font rule | **FIXED** | `shared/fonts.css` + 16 WOFF2 font files downloaded |
| **BUG-005** | S3 | Cached user profile not updated after password change in `api.js` | **FIXED** | `shared/api.js` `changePassword` & `updateProfile` me sync |

## Detailed Defect Records

### BUG-001 (S2 — High): Missing column count in `backend/matcher.py` notification query
- **Steps to reproduce**: Run `seed-demo` or invoke `run_matcher_for_found_item`.
- **Expected**: Match suggestion and notification rows inserted cleanly.
- **Actual**: MySQL error 1136 `Column count doesn't match value count at row 1` (`is_read` column in column list but not in VALUES).
- **Fix**: Removed superfluous `is_read` column from INSERT statement, letting MySQL apply default `0`.
- **Status**: FIXED & verified in live integration tests.

### BUG-002 (S2 — High): Foreign key constraint failure in demo seeding script
- **Steps to reproduce**: Run `python manage.py seed-demo` against live MySQL 8 schema.
- **Expected**: Seeding completes with realistic items.
- **Actual**: `Error 1452: fk_lost_location_campus fails` because demo script passed dummy location IDs `1` and `11` instead of composite keys `102` (Kondhwa) and `203` (Bibwewadi).
- **Fix**: Replaced invalid location IDs with valid seeded location IDs (`102` for Kondhwa Library, `203` for Bibwewadi AI Lab).
- **Status**: FIXED & verified.

### BUG-003 (S2 — High): Stored generated column `active_key` explicitly inserted
- **Steps to reproduce**: Run `seed-demo` inserting into `claims`.
- **Expected**: MySQL evaluates stored generated column `active_key`.
- **Actual**: Script attempted to manually insert a string into `active_key`.
- **Fix**: Removed `active_key` from INSERT column list; MySQL engine calculates value automatically.
- **Status**: FIXED & verified.

### BUG-004 (S3 — Medium): External Google Fonts @import violated self-hosted requirement
- **Steps to reproduce**: Inspect Network tab on initial load.
- **Expected**: All fonts loaded locally from `shared/fonts/` with zero external CDN calls.
- **Actual**: `shared/tokens.css` had `@import url('https://fonts.googleapis.com/...')`.
- **Fix**: Downloaded all 16 WOFF2 font files locally to `shared/fonts/`, generated `shared/fonts.css`, and pointed `tokens.css` to local `./fonts.css`.
- **Status**: FIXED & verified.

### BUG-005 (S3 — Medium): Cached user profile not refreshed after password change
- **Steps to reproduce**: Change password on first login and inspect `api.getUser()`.
- **Expected**: Cached user object reflects `must_change_password: 0` and updated profile.
- **Actual**: Session storage retained initial payload unless explicitly refreshed.
- **Fix**: Updated `ApiClient.changePassword()` and `updateProfile()` to fetch and cache fresh `/auth/me` state.
- **Status**: FIXED & verified.
