# Security Dashboard — Mini SOC System

A local Security Operations Center demo built with Django REST Framework, SQLite,
and React + Vite. It records login attempts, flags suspicious activity using two
rules, and displays events and counts with five-second polling.

## Run locally

Prerequisites: Python 3.12 or 3.14 with venv support and Node.js 24.15+ (24.x), or 22.22.2+ (22.x) with npm.
Run the backend and frontend in separate terminals from the repository root.

### Backend

```bash
python3.12 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py createsuperuser
python backend/manage.py runserver 127.0.0.1:8000
```

Migrations create `backend/db.sqlite3`. This file persists across local server
restarts and is ignored by Git.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The Vite
development server proxies the API paths to `http://localhost:8000`.
Keep the backend running while using the dashboard.

Sign in with the administrator account created above. In **Accounts**, provision
individual Analyst or Viewer accounts. Password recovery is an operator action:
`python backend/manage.py changepassword <username>`. Accounts are deactivated
rather than deleted so case attribution remains intact.

The default Vite proxy keeps the UI and API on the same browser origin. If using
`VITE_API_BASE` for a separate backend, configure exact `CORS_ALLOWED_ORIGINS` and
`CSRF_TRUSTED_ORIGINS` on Django (comma-separated full UI origins), include
credentials, and use the same hostname for local services. Cross-site hosting
needs an explicit cookie/HTTPS deployment configuration; the defaults are for the
same-origin local proxy. Restart services after changing configuration.

### Record sample activity

With the backend environment active:

```bash
python backend/manage.py seed_demo --scenario brute-force --ip 203.0.113.50
```

This trusted local operator command appends synthetic activity. Network ingestion
at `/login-attempt` requires an administrator session and a CSRF token. It is not
an unauthenticated collector endpoint. The stat cards count events, including
suspicious events (not distinct IPs).

## Detection and API

Each login-attempt request validates its input, stores the event, and evaluates:

- More than five failed attempts from one IP in the last five minutes.
- More than ten total attempts from one IP in the last sixty seconds.

If either rule triggers, all stored events from that IP are flagged, including
older events. Flags are retained; the app does not automatically clear them.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/login-attempt` | Record an attempt: `ip`, `success`, optional `username` |
| GET | `/events` | All events, newest first |
| GET | `/suspicious` | Flagged events, newest first |
| GET | `/stats` | Counts: `total`, `failed`, `succeeded`, `suspicious` |

Invalid input returns HTTP 400. A recorded attempt returns HTTP 201.

## Checks and build

```bash
# From the repository root, with the backend virtual environment active
python backend/manage.py test app --verbosity=2
python backend/manage.py makemigrations --check --dry-run

# Frontend
cd frontend
npm run lint
npm test
npm run build
```

The build output is `frontend/dist`. `npm run preview` serves this output for
local inspection. The development API proxy is also configured for preview.
For a hosted build, configure `VITE_API_BASE` before building or provide a reverse
proxy for the API paths on the hosting server.

## Scope and limitations

This repository contains the backend and frontend only. Docker/Compose,
nginx configuration, and an attack simulator are not included. GitHub Actions
runs automated quality and dependency-security checks.

The backend settings are for local development: DEBUG is enabled, the secret key
is a development value, cookies are configured for local HTTP, and SQLite is the database.
Authentication now uses Django sessions with CSRF checks and explicit workspace roles.
Production deployment remains separate work; supported dependencies and automated
vulnerability checks are now included. The API trusts
the submitted IP field; it is a simulator for reported events, not an authentication
service. SQLite and synchronous detection suit a small local demo. Events are
unpaginated, and the UI polls rather than receiving pushed updates.

## Investigation workspace

The UI supports a saved light/dark theme, hourly authentication activity, top
source IPs, search, outcome/detection/time filters, 25-row pages, event details,
source-IP drilldown, and CSV export of the filtered results. Filters and pagination
currently run in the browser over the complete API response.

The Investigations workspace captures detection evidence and supports case ownership,
notes, New → Investigating → Resolved status changes, dispositions, closure reasons,
and reopening. Case URLs use `#investigations/<id>`. Author and owner labels are
authenticated account identities for new records. Older self-reported labels are
preserved and marked as legacy; migration does not pretend they are verified users.

Detection findings retain the original rule version, threshold, count, time window,
and matching event snapshots. One finding is created per IP/rule cooldown (five
minutes for brute-force; one minute for rate abuse). Later matching activity can
create another finding after the cooldown. Existing event flags are retained;
old flags are not converted into findings without new detection evidence.

Create synthetic activity from the repository root with the backend environment active:

```bash
python backend/manage.py migrate
python backend/manage.py seed_demo --scenario brute-force --ip 203.0.113.50
# Other scenarios: normal, rate-abuse. Re-running appends events; it does not reset data.
```

Open Investigations → Findings, review a finding, and open its investigation.
Assign an analyst, start investigating, add notes, and resolve with a disposition
and closure reason. Reopen a resolved case to continue working while preserving
its previous decision in history.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/findings`, `/findings/<id>` | Finding summaries and frozen evidence |
| GET/POST | `/investigations` | Filter the queue or create a case from a finding |
| GET/PATCH | `/investigations/<id>` | Read a case or change metadata/status |
| POST | `/investigations/<id>/notes` | Append an analyst note |

Case creation requires `finding_id`; duplicate creation returns the
existing case. Updates require the current `revision`; stale edits
return HTTP 409. Resolving requires `status: "resolved"`, `disposition` (one of
`true_positive`, `false_positive`, `benign`), and `closure_reason`. Note creation
requires `text`. Actors/authors are taken from the authenticated session; supplied
identity fields are rejected. Assignment uses `owner_user` (an active analyst/admin
account ID, or null to unassign). Queue filters support `status`, `severity`, `source`,
and exact `owner`. API lists remain unpaginated. Deletion and history-editing
endpoints are not provided.

The next milestone is server-side event queries/pagination. See [the development roadmap](docs/ROADMAP.md)
for the proposed data model, delivery order, and later deployment work.

## Accounts and permissions

| Role | Read events, findings, cases | Change cases / add notes | Manage accounts / ingest via API |
| --- | --- | --- | --- |
| Viewer | Yes | No | No |
| Analyst | Yes | Yes | No |
| Administrator | Yes | Yes | Yes |

Permissions are enforced on the backend, including existing sessions after a role
change or deactivation. At least one active administrator must remain. All roles
share this single workspace; organization/tenant isolation is not implemented.
Administrators correspond to Django staff/superuser accounts; Analysts and Viewers
use the matching Django groups created by migration.

`GET /auth/session` returns the current user (or null) and a CSRF token. Send this
token in `X-CSRFToken` alongside the cookie jar for `POST /auth/login` (username,
password). Login rotates the token and returns its replacement. `POST /auth/logout`
also requires the token. Cookies are HttpOnly; passwords and session tokens are not
saved in browser storage. Session lifetime is 12 hours. `/users/assignable` lists
active analysts/admins. Administrators use `GET/POST /users`, `PATCH /users/<id>`
(role / is_active), and `GET /users/access-history` (latest 100 entries). Account
changes are audited without recording passwords.

Sign-in is limited to 10 attempts per minute per remote IP using process-local
cache. Shared, proxy-aware abuse protection, email recovery/verification, MFA,
HTTPS cookies, and production settings remain deployment
work. Keep this demo local until those requirements are addressed.

## Automated quality and security checks

GitHub Actions runs on pushes, pull requests, manual requests, and a weekly schedule:

- Backend tests on Python 3.12 and 3.14, configuration checks, fresh database
  migrations, and detection of model changes missing a migration.
- Ruff checks Python imports, unused code, syntax issues, and security rules.
- Frontend ESLint, production build, and built-application tests on Node 22 and 24.
- `pip-audit` scans Python runtime/development dependencies; `npm audit` scans
  the complete frontend lockfile and fails for any reported severity.

Dependabot proposes weekly Python, npm, and GitHub Actions updates. Workflow
permissions are read-only, checkout credentials are not persisted, and third-party
Actions are pinned to verified commit hashes. No deployment or repository secrets
are required. Audit findings and audit service failures fail the job.

Install developer checks and run them locally:

```bash
python -m pip install -r backend/requirements-dev.txt
ruff check backend
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py test app --verbosity=2
pip-audit -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend test
npm --prefix frontend audit --audit-level=low
```

To enforce checks before merging, configure a GitHub ruleset for `main` requiring
**Backend / Python 3.12**, **Backend / Python 3.14**, **Frontend / Node 22**,
**Frontend / Node 24**, and **Dependency security** after the workflow has run.
The workflow reports failures; requiring them is a repository setting.

Backend tests use isolated test databases, not the local demo database. Frontend
tests exercise the production bundle in JSDOM with controlled API responses;
they do not replace a real-browser integration or visual review. Static analysis
and known-vulnerability scans reduce risk but do not certify the app for public
hosting. The publicly known development secret is narrowly exempted from Ruff;
test fixture passwords are also exempted. Production secrets, HTTPS, shared
abuse protection, and deployment settings remain a separate milestone.
