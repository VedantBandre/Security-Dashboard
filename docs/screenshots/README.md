# README screenshots

These PNGs were captured from the application's production frontend build served
locally through Vite preview, connected to a Django backend and a separate SQLite
database prepared only for documentation. Capture viewport: 1440 × 1000 CSS pixels,
with a device scale factor of 1. Case pages include their full scrollable content.

All accounts, notes, cases, and login events shown are synthetic. Source addresses
use the documentation ranges `198.51.100.0/24` and `203.0.113.0/24`. Password fields
are empty in the screenshots; no session cookies or credentials are included.
The documentation database is not part of the repository.

| Image | Screen |
| --- | --- |
| `sign-in.png` | Sign-in form |
| `events.png` | Events overview and explorer, light mode |
| `event-details.png` | Event inspection and raw record |
| `suspicious.png` | Flagged activity |
| `findings.png` | Detection findings queue |
| `finding-evidence.png` | Captured rule evidence |
| `cases.png` | Investigation queue |
| `investigation.png` | Active case, notes, assignment, and history |
| `resolution.png` | Resolved case with a recorded decision |
| `accounts.png` | Account administration and access history |
| `events-dark.png` | Events overview and explorer, dark mode |

To refresh screenshots, start the application using the root README, provision
synthetic accounts, generate demo activity, and prepare one investigating case
and one resolved case. Capture each screen after its data has loaded; keep the
same viewport, leave password fields empty, and review images before committing.
Use a separate disposable database if you want to preserve your working dataset.
