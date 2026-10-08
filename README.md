# Security Dashboard — Mini SOC System

A local Security Operations Center demo built with Django REST Framework, SQLite,
and React + Vite. It records login attempts, flags suspicious activity using two
rules, and displays events and counts with five-second polling.

## Run locally

Prerequisites: Python 3.12 with venv support and Node.js 24.15+ (24.x), or 22.22.2+ (22.x) with npm.
Run the backend and frontend in separate terminals from the repository root.

### Backend

```bash
python3.12 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
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
development server proxies the four API paths to `http://localhost:8000`.
Keep the backend running while using the dashboard.

To target another backend, set `VITE_API_BASE` in `frontend/.env.local`, for example:

```dotenv
VITE_API_BASE=http://localhost:8000
```

Restart Vite after changing this value. The variable is embedded at build time;
it must not contain secrets.

### Record sample activity

```bash
curl -X POST http://localhost:8000/login-attempt \
  -H 'Content-Type: application/json' \
  -d '{"ip":"192.168.1.1","username":"admin","success":false}'
```

Repeat the request six times within five minutes to trigger the brute-force rule.
The Events tab shows all login events; the Suspicious tab shows flagged events.
The stat cards count events, including suspicious events (not distinct IPs).

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
nginx configuration, an attack simulator, and GitHub Actions are not included.

The backend settings are for local development: DEBUG is enabled, the secret key
is a development value, CORS allows all origins, and the API has no authentication.
Production deployment and dependency maintenance are separate work. The API trusts
the submitted IP field; it is a simulator for reported events, not an authentication
service. SQLite and synchronous detection suit a small local demo. Events are
unpaginated, and the UI polls rather than receiving pushed updates.

## Investigation workspace

The UI supports a saved light/dark theme, hourly authentication activity, top
source IPs, search, outcome/detection/time filters, 25-row pages, event details,
source-IP drilldown, and CSV export of the filtered results. Filters and pagination
currently run in the browser over the complete API response.

The next milestone is persistent investigations with rule evidence, ownership,
notes, status changes, and recorded outcomes. See [the development roadmap](docs/ROADMAP.md)
for the proposed data model, delivery order, and later deployment work.
