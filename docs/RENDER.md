# Host the portfolio trial on Render

The root `render.yaml` defines one Docker web service in Frankfurt on the free
plan. It deploys the repository's `main` branch after CI checks pass. **It does
not create a database.** Database provisioning is deferred: supply a dedicated
PostgreSQL connection before applying this Blueprint.

Free web services can sleep and share the workspace's free instance-hour allocation.
A free web plan does not make an external database free. Review the chosen database
provider's lifetime, capacity, and cost separately. If considering Render's free
PostgreSQL later, it expires after 30 days and only one active free database is
allowed per workspace. Never delete another project's database to make room.

Sources: [Render free-tier limits](https://render.com/docs/free) and
[deployment lifecycle](https://render.com/docs/deploys).

## Apply the Blueprint

1. Merge the hosting branch so `render.yaml` is on GitHub's `main` branch.
2. Open [Create Render Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/VedantBandre/Security-Dashboard).
3. Choose the intended Render workspace and connect GitHub if prompted.
4. Supply the environment values marked `sync: false`:
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`: a dedicated
     PostgreSQL connection. TLS is required by default.
   - `DJANGO_SECRET_KEY`: a private random value of at least 50 characters.
   - `PORTFOLIO_ADMIN_PASSWORD`: a strong private password.
   - `PORTFOLIO_VIEWER_PASSWORD`: a different strong password for the fallback Viewer sign-in.
5. Review the web service's **free** plan, then apply only after the database
   settings are available. Without them, production startup deliberately fails.
6. Wait for the deploy to become live, then open its `onrender.com` URL.

Generate private random values with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
Never share the secret key or administrator password. Visitors use **Explore demo**
without entering credentials; keep the fallback Viewer password private too.

## First startup and restarts

Free web services do not support pre-deploy commands. This Blueprint overrides
the Docker command with `sh bin/start_portfolio.sh` for a single web instance.
The command runs `release_portfolio` before launching Gunicorn:

- A PostgreSQL session advisory lock serializes release preparation.
- Migrations run and the shared login cache table is created.
- With `PORTFOLIO_PROVISION=true`, an empty database is initialized once.
- The successful `portfolio-v1` marker prevents repeated seeding or password changes.
- Any pre-existing user or event data causes initial provisioning to fail without
  changing that data. Provisioning errors roll back the complete demo transaction.

The initialized workspace contains **71 synthetic events, three findings, and
three cases** in New, Investigating, and Resolved states. The demo uses reserved
documentation IP ranges. Case titles and notes explicitly identify synthetic work.
The `demo-analyst` attribution account has an unusable password and cannot sign in.

| Account | Access | Password |
| --- | --- | --- |
| `portfolio-viewer` | Public read-only visitor | `PORTFOLIO_VIEWER_PASSWORD` from first initialization |
| `portfolio-admin` | Private account and case administration | `PORTFOLIO_ADMIN_PASSWORD` from first initialization |

Passwords are stored as Django password hashes. Changing an environment variable
later does not reset an existing password. Use the Accounts workflow or an operator
`changepassword` command as appropriate. The Blueprint sets `PORTFOLIO_MODE=true`,
which enables **Explore demo** only after initialization and while `portfolio-viewer`
is active with the Viewer role. Its role cannot be promoted through the account API
in portfolio mode. Deactivating the account removes public access; disabling
`PORTFOLIO_MODE` also ends existing public guest sessions on their next request.
An out-of-band privilege change revokes those sessions rather than granting visitors
write access. Normal private staff sign-in remains available.

The public entry is CSRF-protected and shares the existing sign-in rate limit.
The walkthrough labels the synthetic dataset, explains read-only access, and guides
visitors through event details, detection evidence, and case decisions. Visitors
can hide or reopen it; only that preference is saved in their browser.

Synthetic timestamps reflect initialization time. This is a retained example
workspace, not an external live monitoring feed. After 24 hours, the recent-activity
chart can be empty even though the all-time event explorer and cases remain populated.

## HTTPS, health, and access

The Blueprint derives its allowed host from Render's `RENDER_EXTERNAL_HOSTNAME`.
If you later attach a custom domain, add it explicitly to `DJANGO_ALLOWED_HOSTS`.
The app trusts Render's forwarded HTTPS scheme. Keep `DJANGO_PROXY_COUNT=0` until
the exact sanitized ingress chain is verified; this may make visitors share the
proxy's login-throttle bucket. Confirm this behavior before broad public sharing.

Readiness checks use `/health/`. This minimal status endpoint allows HTTP probes
so a redirect cannot mask database failure. Authentication and workspace routes
still redirect to HTTPS, and all routes validate the Host header. The supplied PostgreSQL connection requires TLS. Configure the provider
allowlist and network access for this web service; the Blueprint does not change
the external database's access policy.

After the deploy is live, verify sign-in as both accounts, Viewer write restrictions,
case evidence, CSV export, secure cookies, the health check, and persistence through
a restart. Share the demo URL plus the Viewer credentials, and link the GitHub
repository for source and screenshots. Do not publish credentials until the Viewer
permissions have been checked on the hosted service.

Database lifetime and hosting availability remain operator decisions.
See [the general deployment guide](DEPLOYMENT.md) for operational requirements.
