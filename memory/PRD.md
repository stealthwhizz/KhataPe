# PRD — Real-time GST Billing Tracker

## Original Problem Statement
Build a React dashboard with a dark theme for a real-time GST billing tracker.
- Top summary cards: **March GST Total** (prominent green), **Total Collected**, **Net (excl. GST)**
- Full-width transactions table with columns: Time | Payer | Amount | GST | Net
- Rows flash green briefly when new rows appear
- Fetch from `GET http://localhost:8000/transactions` every 5 seconds
- If unreachable, show small **Offline** badge at top-right without breaking UI
- Style constraints: bg `#0f0f0f`, card `#1a1a1a`, accent `#22c55e`, white primary text, muted gray secondary text, monospace numbers, minimal borders, no gradients
- Alternating subtle row shades
- Animated green dot next to **Live** in header
- No hardcoded dummy data; start with “Waiting for transactions…” empty state

## User Choices
- API strategy: **automatic fallback** (localhost source + backend fallback endpoint)
- Table order: **newest transactions at top**

## Architecture Decisions
- Frontend: React app with a single dashboard route (`/`), Shadcn UI Card/Table/Badge primitives.
- Polling: client-side polling every 5s.
- Data source fallback order:
  1) `http://localhost:8000/transactions`
  2) `${REACT_APP_BACKEND_URL}/api/transactions`
- Backend: FastAPI added `/api/transactions` proxy endpoint to local upstream (`http://localhost:8000/transactions`) and returns HTTP 503 when upstream is unavailable.
- Visual system implemented in `App.css` with exact requested palette and lightweight animations.

## User Personas
1. Billing Operator — monitors incoming GST transactions live.
2. Finance Reviewer — tracks GST totals and net values quickly.
3. Team Lead — checks system status via Live/Offline indicators.

## Core Requirements (Static)
- Real-time-ish refresh via 5-second polling.
- Stable UI in offline/unreachable scenarios.
- Accurate aggregate totals from incoming records.
- New-row visual emphasis via temporary green flash.
- Dark theme with strict color/font style requirements.

## What’s Implemented (with dates)
### 2026-03-14
- Replaced starter frontend with GST tracker dashboard UI.
- Implemented three summary cards with required labels and hierarchy.
- Implemented full-width transactions table with required columns and empty state message.
- Added newest-first sorting and row flash animation for newly detected rows.
- Added Live indicator with animated green dot.
- Added Offline badge logic when all configured sources fail.
- Added robust data normalization for possible transaction payload shapes.
- Added backend endpoint `GET /api/transactions` as fallback proxy to localhost upstream.
- Added `data-testid` attributes across critical/interactive UI for testability.
- Verified via self-tests (screenshot + curl) and testing agent report (`iteration_1.json`) with no blocking issues.

## Prioritized Backlog
- Validate with a real active transaction feed to observe real row flashes in production-like timing.
- Optional: reduce browser console noise from expected failed localhost attempts in HTTPS preview contexts.
- Optional: add pagination/virtualization for very large transaction volumes.

## Remaining Features by Priority
### P0 (Critical)
- None in current requested scope.

### P1 (Important)
- Add stronger runtime validation for unexpected transaction schemas (if upstream format changes).

### P2 (Nice to Have)
- Filter/search by payer and time window.
- Export transactions as CSV.
- Lightweight sound cue on new row arrival.

## Next Tasks List
1. Connect or start a real upstream feed at `http://localhost:8000/transactions` in target environment.
2. Validate real transaction inserts trigger row flash and aggregate changes live.
3. Optionally tune polling retry/backoff behavior for quieter network logs.
