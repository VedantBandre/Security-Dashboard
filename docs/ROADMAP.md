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
browser. The backend still returns unpaginated lists. Investigation metadata,
rule explanations, ownership, and analyst actions are not implemented yet.

## Next milestone: a persistent investigation loop

Ship one useful end-to-end story before expanding the number of screens:

1. Generate repeated failed logins for one source in a demo dataset.
2. Produce a detection finding with the triggering rule and its evidence window.
3. Open that finding and see the source's ordered login history.
4. Create an investigation; add a note and assign an analyst.
5. Move it from New to Investigating to Resolved.
6. Record a disposition (true positive, false positive, or benign) and closure reason.
7. Reopen the page and verify the complete record remains available.

Suggested backend records:

| Record | Purpose | Important fields |
| --- | --- | --- |
| LoginEvent | Immutable reported evidence | Existing fields; later add source and ingestion timestamp |
| DetectionFinding | Explain why activity was flagged | IP, rule identifier/version, threshold, observed count, window, detection time, related event IDs |
| Investigation | Track analyst work | Title, severity, status, owner, linked findings, timestamps, disposition, closure reason |
| InvestigationNote | Preserve reasoning | Investigation, author, text, creation time |
| AuditEntry | Record changes | Actor, action, target, before/after values, timestamp |

Change detection from a boolean-only result to structured findings. Store the
rule parameters and evidence at detection time so later events do not rewrite the
explanation. Deduplicate findings for the same source/rule/window. Give severity
an explicit rule-based meaning; avoid invented risk scores.

Expose validated API actions for notes, assignment, status changes, and resolution.
Use database transactions for related state changes. Resolving an investigation
must preserve the original events, findings, and history.

The UI should add an investigation queue and detail page with a chronological
evidence timeline. Provide meaningful filters for status, severity, source, and
owner. Prioritize keyboard operation and a clear empty/error state.

## Following milestone: multi-user and larger datasets

- Authentication and analyst/admin permissions, enforced by the backend.
- Server-side search, time filters, ordering, and pagination. Define whether
  summary counts apply to the selected filters or the whole dataset.
- Indexed source/timestamp queries and PostgreSQL when needed.
- Rule configuration with validation and a history of changes.
- Deterministic demo scenarios: normal traffic, brute-force, and rate abuse.
- Saved searches and investigation export.
- Validation for detection boundaries, deduplication, transitions, permissions,
  and the complete ingestion-to-resolution workflow.

Keep the current polling approach until data volume or responsiveness warrants
WebSockets. Add background processing only when measured ingestion load needs it.

## Later: realistic integrations and deployment

- Additional event sources with a defined ingestion schema and trusted source identity.
- IP/entity enrichment with provider provenance and explicit unavailable states.
- Notifications linked to actionable findings, with deduplication.
- Production settings, supported dependencies, secret management, request limits,
  backups, structured logs, and health monitoring before public hosting.
- A simulated containment action with a visible demo label and an audit entry.
  Real containment requires an integration that actually enforces the action.

The current ingestion endpoint records claimed login outcomes. It does not
perform authentication or block IPs. A polished UI should keep that distinction clear.

## Reference workflows

- [Elastic: alert detail and investigation actions](https://www.elastic.co/docs/solutions/security/detect-and-alert/view-detection-alert-details)
- [Microsoft Sentinel: incident investigation](https://learn.microsoft.com/en-us/azure/sentinel/investigate-incidents)

These inform the workflow direction; they are not claims of equivalent capability.
