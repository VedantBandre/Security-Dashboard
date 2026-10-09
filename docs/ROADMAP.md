# Security Dashboard direction

## Product goal

Build a small SOC investigation workspace around a complete analyst workflow:
**ingest → detect → inspect → investigate → resolve**.
The portfolio demo should make each step usable and show where decisions come from.

An event is an observation, an alert is a detection finding, and an investigation
(or case) is the analyst's work record. Keep these as separate concepts.
The current boolean event flag is useful for exploration but is not an alert lifecycle.

## Current foundation

- Login-event ingestion and two time-window detection rules.
- Live polling, totals, hourly activity, and top source IPs.
- Event search; outcome, detection, and time filters; local pagination.
- Event inspection, raw evidence, exact source-IP drilldown, and CSV export.
- Responsive light/dark workspace with a saved theme preference.

Filters, pagination, charts, and export currently operate on events loaded by the
browser. The backend still returns unpaginated lists. Sign-in and backend workspace permissions are implemented.

## Delivered: persistent investigation loop

- Structured findings freeze the rule version, threshold, observed count, time
  window, severity, and chronological matched-event snapshots at detection time.
- Each IP/rule has a cooldown equal to its detection window. Repeated matching
  events reuse the finding during that cooldown; later activity can create a new
  finding. Frozen evidence is not extended or rewritten.
- One investigation per finding, with owner label, severity, notes, status,
  disposition, closure reason, and append-only API history.
- Lifecycle: New → Investigating → Resolved; resolved cases can be reopened to
  Investigating. Reopening clears the current resolution but retains it in history.
- Revision checks reject stale case edits with HTTP 409. Notes and history are
  retained in the same local SQLite database across restarts.
- Finding review, case queue filters, source-event drilldown, and case deep links.
- A non-destructive demo command creates normal, brute-force, or rate-abuse traffic.

Historical self-reported labels remain preserved as legacy records; new authors
and assignments refer to authenticated accounts.
Existing boolean flags are preserved without fabricating historical findings.
Queue lists remain unpaginated. Grouping multiple findings into one case and
organization-level isolation is not implemented yet.

## Reference acceptance story for the delivered milestone

Ship one useful end-to-end story before expanding the number of screens:

1. Generate repeated failed logins for one source in a demo dataset.
2. Produce a detection finding with the triggering rule and its evidence window.
3. Open that finding and see the source's ordered login history.
4. Create an investigation; add a note and assign an analyst.
5. Move it from New to Investigating to Resolved.
6. Record a disposition (true positive, false positive, or benign) and closure reason.
7. Reopen the page and verify the complete record remains available.

Backend records:

| Record | Purpose | Important fields |
| --- | --- | --- |
| LoginEvent | Immutable reported evidence | Existing fields; later add source and ingestion timestamp |
| DetectionFinding | Explain why activity was flagged | IP, rule identifier/version, threshold, observed count, window, detection time, related event IDs |
| Investigation | Track analyst work | Title, severity, status, owner, finding, timestamps, disposition, closure reason |
| InvestigationNote | Preserve reasoning | Investigation, author, text, creation time |
| AuditEntry | Record changes | Actor, action, target, before/after values, timestamp |

Detection produces structured findings in addition to retaining event flags. Rule
parameters and evidence are stored at detection time so later events do not rewrite
the explanation. Findings are deduplicated for each source/rule cooldown. Severity
is rule-based: High for brute-force and Medium for rate abuse; analysts can override
case severity with the change recorded in history.

Validated API actions cover notes, assignment, status changes, and resolution.
Related writes use database transactions. Resolving an investigation
preserves the original events, findings, and history.

The UI includes an investigation queue and detail page with a chronological
evidence timeline, queue filters for status and severity, and search by title,
source, or owner. The source-history action opens the event explorer with an exact IP filter.

## Delivered: authenticated workspace access

- Session sign-in/sign-out, CSRF-protected login and mutations, HttpOnly cookies.
- Backend-enforced Viewer, Analyst, and Administrator roles.
- Account-backed ownership, note authors, and decision actors; forged labels rejected.
- Administrator account provisioning, role/activation controls, last-admin protection,
  and access-change history. Deactivation preserves attribution.
- Login throttling for the local demo and real-cookie permission/CSRF tests.
- Legacy records retained without attributing unverified labels to real accounts.

This is a single shared workspace. HTTPS configuration,
shared abuse protection, recovery, and MFA remain separate deployment work.

## Delivered: continuous quality and dependency security

- PR/push CI on Python 3.12/3.14 and Node 22/24: tests, lint, build,
  configuration checks, and fresh migrations with migration-drift detection.
- Python security lint rules and runtime/development dependency audits.
- Supported Django 5.2 LTS plus patched backend/frontend dependencies.
- Weekly audit runs and Dependabot update PRs for Python, npm, and Actions.
- Read-only workflow permissions, commit-pinned Actions, and no deployment secrets.

Requiring passing checks before merge needs a GitHub ruleset. Public hosting,
real-browser integration tests, secret provisioning, and production settings remain
separate work; these checks do not establish production security.

## Delivered: portfolio deployment foundation

- Production settings require a private secret, explicit hosts, and PostgreSQL.
- Secure cookies, HTTPS redirects, host validation, and opt-in trusted-proxy handling.
- Shared database cache for login throttling across web workers; ingress limits still needed.
- One-origin non-root container with Gunicorn and the built React frontend.
- Minimal database health endpoint and deployment configuration tests.
- Release, demo Viewer provisioning, proxy, backup, and monitoring instructions.

See [the deployment guide](DEPLOYMENT.md). Actual hosting, TLS, backups, monitoring,
and public Viewer credentials are operator setup; the repository does not provision them.

## Next milestone: larger datasets

- Server-side search, time filters, ordering, and pagination. Define whether
  summary counts apply to the selected filters or the whole dataset.
- Indexed source/timestamp queries and PostgreSQL when needed.
- Rule configuration with validation and a history of changes.
- Broader demo datasets covering mixed traffic, cooldowns, and concurrent sources.
- Saved searches and investigation export.
- Validation for detection boundaries, deduplication, transitions, permissions,
  and the complete ingestion-to-resolution workflow.

Keep the current polling approach until data volume or responsiveness warrants
WebSockets. Add background processing only when measured ingestion load needs it.

## Later: realistic integrations and deployment

- Additional event sources with a defined ingestion schema and trusted source identity.
- IP/entity enrichment with provider provenance and explicit unavailable states.
- Notifications linked to actionable findings, with deduplication.
- Production settings, secret management, request limits,
  backups, structured logs, and health monitoring before public hosting.
- A simulated containment action with a visible demo label and an audit entry.
  Real containment requires an integration that actually enforces the action.

The current ingestion endpoint records claimed login outcomes. It does not
perform authentication or block IPs. A polished UI should keep that distinction clear.

## Reference workflows

- [Elastic: alert detail and investigation actions](https://www.elastic.co/docs/solutions/security/detect-and-alert/view-detection-alert-details)
- [Microsoft Sentinel: incident investigation](https://learn.microsoft.com/en-us/azure/sentinel/investigate-incidents)

These inform the workflow direction; they are not claims of equivalent capability.
