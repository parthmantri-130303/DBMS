<!-- File: 08_deployment_devops_plan.md -->
# CampusKhoj — Deployment & DevOps Plan

Version 1.0 · 1 November 2026 · AI-generated for the project team

*Scale note: this is a college course project with ≤ 1,095 student accounts. The plan is deliberately light — production-style habits without enterprise overhead.*

## 1. Environments

| Env | Purpose | Access |
|---|---|---|
| `dev` | Each developer's laptop (Docker Compose: MySQL + API; portals via simple static server) | Own machine |
| `test` | CI containers, DB reset every run, generated PRNs only | CI only |
| `demo` / `prod` | Single server for viva and pilot; real PRN import; HTTPS | Team (SSH), staff & students (web) |

Ports in dev: API `5000`, Student Portal `3001`, Admin Portal `3002`. In `demo`: `student.<domain>` and `admin.<domain>` (two origins) or `/` and `/admin/` paths on one domain — origin list goes into the CORS allow-list.

## 2. CI/CD Pipeline (GitHub Actions)

| Stage | Steps |
|---|---|
| Lint | `ruff`, `bandit`, HTML/CSS lint |
| Test | Start MySQL service → apply `schema.sql`/`views.sql`/`triggers.sql` → pytest (unit, DB, API) |
| Build | Tailwind CSS build for each portal; collect static bundles |
| Package | Build Docker image for the API (optional) |
| Deploy (manual approval) | SSH/rsync portals + API to `demo`, run DB migrations, restart Gunicorn, smoke test `/health` |

**Branching:** `main` = releasable, `develop` = integration, `feature/<name>` per task; PRs need 1 review + green CI; tags `v0.x` per sprint, `v1.0` final.

**DB changes:** numbered migration files `database/migrations/001_*.sql`; never edit applied files; keep `schema.sql` as the full current snapshot.

## 3. Infrastructure Overview

Single Linux VM (college server or low-cost VPS — Assumption A-9):

```
Internet/Campus LAN → Nginx (TLS, static portals, /media, gzip)
                         → Gunicorn (3–4 workers) → Flask API
                         → MySQL 8 (same VM; separate DB user per app)
```

- **Compute:** one VM, 2 vCPU / 4 GB RAM is ample.
- **Storage:** `media/` on disk (≈ 3 MB max per image; 10k items ≈ ≤ 30 GB worst case; typical far less); DB on SSD.
- **Networking:** only 80/443 open; MySQL bound to localhost; SSH key-only.
- **TLS:** Let's Encrypt (public host) or college certificate; HTTP → HTTPS redirect.
- **Config:** `.env` outside web root (`JWT_SECRET`, DB creds, CORS origins, `MEDIA_ROOT`).
- **Process mgmt:** `systemd` units for Gunicorn and the scheduled jobs (or APScheduler inside the app).
- **Fallback:** if no server is available, run Docker Compose on a laptop at the viva (documented in README).

## 4. Release Strategy

1. Merge to `develop` → CI green → tag release candidate.
2. Deploy RC to `demo`; run smoke script (login with seeded PRN, report, claim, approve, handover).
3. UAT sign-off → merge to `main`, tag `vX.Y`.
4. Deploy during a low-traffic window; keep previous release folder for **one-command rollback** (`ln -sfn releases/<prev> current`; restore DB backup only if a migration was destructive).
5. Feature flags (simple `.env` booleans): `ENABLE_MATCHING`, `ENABLE_CSV_EXPORT`, `ALLOW_OTHER_CAMPUS_BROWSE`.
6. First real-student rollout: invite one department/class first (canary), then campus-wide.

## 5. Monitoring & Alerting

| Signal | How |
|---|---|
| Availability | `/health` checked every minute by UptimeRobot-style pinger or a cron `curl` |
| Latency / error rate | Gunicorn + Nginx access logs; weekly summary script (p95, 5xx count) |
| Business metrics | SQL views (logins, reports/day, pending claims age) on the admin dashboard |
| Security | Count of `ACCOUNT_LOCKED`, 401 spikes, failed admin logins from `login_attempts` |
| Logs | JSON logs with request id, no PRNs/passwords/tokens; `logrotate` 14 days |

Alerts (v1): email/WhatsApp message to the team when `/health` fails 3 times in a row, disk > 80%, or 5xx rate > 5% over 5 minutes. Escalation: backend lead first, then DB lead.

## 6. Backup & Disaster Recovery

| Item | Policy |
|---|---|
| Database | Nightly `mysqldump --single-transaction`, keep 14 days, copy weekly off-server |
| Media | Nightly `rsync` of `media/` to a second location |
| Config/secrets | Stored separately in a password manager; not in Git |
| Restore test | Perform one full restore rehearsal before the viva |
| Targets (Assumption) | **RPO 24 h**, **RTO 4 h** for the pilot |

Disaster plan: provision new VM → install packages → restore `.env` → restore DB + media → point DNS → run smoke test.

## 7. Operational Checklist Before Go-Live

- [ ] Default/test accounts removed; real SUPER_ADMIN created via `manage.py create-admin`.
- [ ] PRN lists imported (expect 582 Bibwewadi + 513 Kondhwa = 1,095 rows; no duplicates).
- [ ] Locations for both campuses reviewed by staff.
- [ ] HTTPS valid; CORS lists only the two portal origins.
- [ ] Rate limits and lockout verified in `demo`.
- [ ] Backup + restore tested; logs rotating.
- [ ] Desk staff trained on the claim-review and handover screens.
