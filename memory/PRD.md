# PRD: SafeDep Security Scan Integration + Dashboard Security Badge

## Original Problem Statement
Run a SafeDep security scan on backend requirements, add scan tooling to project, generate JSON report, add `safedep_scan.sh` at project root, add `safedep_report.json` to `.gitignore`, and display a small Security badge in dashboard footer:
- Green: no critical vulnerabilities
- Red: any critical vulnerabilities
The app must not fail startup if scanning/report generation fails.

## Architecture Decisions
- Target manifest confirmed: `/app/backend/requirements.txt`.
- Script location confirmed: `/app/safedep_scan.sh`.
- Frontend badge reads security status via backend API (`/api/security/status`) instead of direct file access.
- Runtime constraints handled safely:
  - `pip install safedep-cli` unavailable in this environment
  - Docker unavailable in this environment
  - Added tertiary fallback to SafeDep `vet` binary (`/app/bin/vet`) in script
- Security status endpoint is defensive: missing/malformed report returns stable `red` status and never breaks app flow.

## What’s Implemented
- Scanning and report generation:
  - Installed SafeDep `vet` CLI binary locally (`/app/bin/vet`) for fallback scanning
  - Executed scan against `/app/backend/requirements.txt`
  - Generated `/app/safedep_report.json`
- New script:
  - Added `/app/safedep_scan.sh` (executable)
  - Flow: `safedep` command first → Docker fallback → local `vet` fallback
  - Uses non-fatal behavior (`|| true`) so scan failures do not block app runtime
- Backend:
  - Added `GET /api/security/status` in `backend/server.py`
  - Parses `/app/safedep_report.json` and counts critical risks
  - Returns `{ status: green|red, critical_count, scan_available }`
- Frontend:
  - Added footer security badge in `frontend/src/App.js`
  - Badge color/text driven by `/api/security/status` response
  - Added styles in `frontend/src/App.css` for green/red badge
- Repo hygiene:
  - Added `safedep_report.json` to `/app/.gitignore`

## Verification Completed
- Script execution verified from `/app/safedep_scan.sh`.
- API verified:
  - With current report: returns `red` and `critical_count=1`
  - With missing report: returns `red`, `critical_count=0`, `scan_available=false`
- Frontend verified via browser automation:
  - Footer badge renders and matches backend status
- Full backend tests pass: 18/18.

## Prioritized Backlog
### P0
- Resolve critical vulnerability flagged in `python-jose` by upgrading and validating compatibility.
- Re-run scan after dependency updates to move badge from red to green.

### P1
- Add a “last scanned at” timestamp to `/api/security/status` and badge tooltip.
- Add optional endpoint to trigger non-blocking scan job from admin UI.

### P2
- Add trend/history of vulnerability counts for security monitoring over time.

## Next Tasks
1. Upgrade vulnerable dependencies in `backend/requirements.txt` (especially critical findings).
2. Re-run `/app/safedep_scan.sh` and verify badge becomes green when no critical issues remain.
3. Optionally expose scan summary details in a dedicated security page.
