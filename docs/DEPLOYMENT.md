# Portfolio demo deployment

The supported deployment shape is one HTTPS origin serving the built React UI and
Django API, behind a trusted hosting ingress, with PostgreSQL for persistent data.
The container runs Gunicorn as a non-root user. No frontend API-origin setting is
needed: browser requests use the same origin, with secure HttpOnly session cookies
and CSRF checks.

This milestone supplies the deployment foundation. Choosing/provisioning a host,
TLS, database backups, monitoring, and public demo credentials are operator tasks.

## Environment

Use `deployment.env.example` as a checklist for your hosting provider's environment
settings. The application reads the process environment; it does not load `.env`
files automatically. Keep actual environment files and credentials out of Git.

| Variable | Meaning |
| --- | --- |
| `DJANGO_ENV` | `production` for hosting; development is the local default |
| `DJANGO_SECRET_KEY` | Private random value, at least 50 characters; development keys are rejected |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated explicit hosts, without schemes or wildcards |
| `DB_ENGINE` | `postgresql` in production; local default is SQLite |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` | Required PostgreSQL connection settings |
| `DB_PORT` | Defaults to 5432 |
| `DB_SSLMODE` | Defaults to `require`; use your provider's certificate settings where available. `disable` is only for an isolated local database |
| `DJANGO_TRUST_PROXY` | Defaults to false; trust forwarded HTTPS information only behind a controlled ingress |
| `DJANGO_PROXY_COUNT` | Defaults to 0, so throttle identity uses the direct peer. Set to the exact trusted proxy count when your ingress supplies a sanitized `X-Forwarded-For` chain |
| `DJANGO_HSTS_INCLUDE_SUBDOMAINS` | Defaults to false; enable only if all subdomains use HTTPS |
| `PORT` | Gunicorn listening port, default 8000 |
| `WEB_CONCURRENCY` | Gunicorn workers, default 2 |

Generate a secret privately with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
and place it in your host's secret settings. Production always disables DEBUG,
requires PostgreSQL, redirects HTTP to HTTPS, and enables secure cookies and
one-year HSTS for the application host. HSTS preload is deliberately disabled.

The ingress must terminate TLS, preserve the public Host header, reject unknown
hosts, replace client-supplied forwarded headers with trusted values, and prevent
direct public access to Gunicorn. Only then enable `DJANGO_TRUST_PROXY=true`.
An incorrect proxy configuration can cause redirect loops or forged client identities.
Behind a proxy with proxy count 0, users may share the ingress's throttle bucket.

## Build and release

Docker commands below also work with Podman by replacing `docker` with `podman`.
Build from the repository root:

```bash
docker build -t security-dashboard:portfolio .
```

The image contains the production frontend build, backend dependencies, and
collected Django static files. No passwords, local databases, or demo data are
baked into it. It starts with Gunicorn; the Django development server and Vite
preview are not the hosted servers.

Before starting a new release, run these one-off commands using the same private
runtime environment and database network as the web service:

```bash
docker run --rm --env-file /private/path/portfolio.env security-dashboard:portfolio python manage.py migrate --noinput
docker run --rm --env-file /private/path/portfolio.env security-dashboard:portfolio python manage.py createcachetable
docker run --rm --env-file /private/path/portfolio.env security-dashboard:portfolio python manage.py check --deploy
```

The database cache table shares login throttle state between workers. It must exist
before sign-in is used. This throttle remains best-effort under concurrent requests;
use hosting-ingress rate limits for stronger abuse protection. The health check tests
database connectivity, not whether release commands or all migrations have completed.

Run migrations once as a release job, rather than in every web worker's startup.
Back up the database before schema changes. `check --deploy` may report warnings
for intentionally disabled HSTS subdomains/preload; review these domain decisions.
Do not silence all deployment warnings.

Start the image with your private environment and connect it to the ingress:

```bash
docker run --env-file /private/path/portfolio.env -p 127.0.0.1:8000:8000 security-dashboard:portfolio
```

Configure your platform's readiness probe to GET **`/health/`** with an allowed Host
and the same trusted HTTPS forwarding as public requests. A successful response is
`{"status":"ok"}`; unavailable database connectivity returns 503 without internal
connection details. Plain HTTP probes are redirected by the HTTPS policy. Use an
HTTPS probe or configure the internal probe to match the trusted ingress contract.

For hosting without containers, build with `npm --prefix frontend ci` and
`npm --prefix frontend run build`, install `backend/requirements.txt`, export the
same environment, then run release commands plus `collectstatic --noinput`.
From `backend/`, launch `gunicorn --config gunicorn.conf.py config.wsgi:application`.
Keep the built `frontend/dist` alongside `backend` in the deployed directory.

## Prepare the demo

Create your private administrator through an interactive one-off command:

```bash
docker run --rm -it --env-file /private/path/portfolio.env security-dashboard:portfolio python manage.py createsuperuser
```

Use Accounts to create a separate **Viewer** for portfolio visitors. Share only that
Viewer's demo credentials with reviewers; keep Administrator and Analyst credentials
private. Viewer access is enforced by the backend and cannot change cases or accounts.
There is no public registration. Visitors share one synthetic workspace.

Populate synthetic events using one-off `python manage.py seed_demo` commands for
`normal`, `brute-force`, and `rate-abuse`, as described in the root README. Prepare
an investigating case and a resolved case with clear demo notes. These commands
append records; running them on each startup would duplicate your dataset.

## Verify before sharing

1. Open the public HTTPS URL and confirm the sign-in screen and assets load.
2. Sign in as the Viewer and inspect events, a finding, and a resolved case.
3. Confirm write actions and account management are unavailable to the Viewer.
4. Sign in privately as an Analyst and verify a synthetic case can be updated.
5. Confirm an unauthenticated API request is denied, unknown hosts are rejected,
   HTTP redirects to HTTPS, and session cookies have Secure and HttpOnly attributes.
6. Restart the service and confirm records remain in PostgreSQL.
7. Confirm the health probe works, failed responses reach your monitoring, and
   the PostgreSQL backup schedule and restore procedure are configured.

The CI portfolio job builds the image, applies migrations and creates the cache
table against PostgreSQL, then runs `scripts/check_portfolio.py` against the
assembled application. This checks assets, health, host validation, HTTPS
redirects, CSRF bootstrap cookies, and anonymous API restrictions using internal
ingress headers; it does not validate a public TLS certificate.

Run `python manage.py clearsessions` periodically through a provider-scheduled job.
Monitor web errors and database storage; dependency CI audits do not monitor uptime.
Use only synthetic data. Email recovery, MFA, server-side pagination, independent
visitor sandboxes, and an atomic distributed abuse-control mechanism remain later
milestones.

## References

- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django proxy HTTPS settings](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header)
- [WhiteNoise Django integration](https://whitenoise.readthedocs.io/en/stable/django.html)
