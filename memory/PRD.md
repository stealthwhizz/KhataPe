# PRD: Live Transaction Streaming with S2 + Webhook Hardening

## Original Problem Statement
Add real-time transaction streaming using S2.dev.
Whenever a webhook fires (Razorpay payment captured OR WhatsApp invoice parsed), push a live transaction event so the dashboard updates instantly without waiting for the 5-second poll.
Call push logic in both `/webhook/razorpay` and `/webhook/whatsapp` right after `log_transaction()`.
In React dashboard, subscribe to live stream and prepend rows instantly while keeping 5-second polling fallback.
Add `S2_AUTH_TOKEN` and `S2_BASIN=gst-transactions` placeholders in env.

## Architecture Decisions
- Kept existing stack as requested: **Python FastAPI backend + React frontend**.
- Added backend S2 integration with resilient behavior:
  - Initialize stream at startup (`transactions` stream)
  - Push event payload after successful transaction logging in both webhooks
  - Never break webhook processing if S2 is unavailable or token is empty
- Added new Razorpay webhook route and hardened it with signature verification (`X-Razorpay-Signature` + `RAZORPAY_WEBHOOK_SECRET`).
- Added polling API `/api/transactions/recent` for dashboard fallback.
- Frontend dashboard now combines:
  - live subscription path via S2 SDK client utility
  - 5-second polling fallback + manual refresh

## What’s Implemented
- Backend (`/app/backend/server.py`)
  - Added S2 helpers: `init_s2_stream()`, `push_transaction_to_s2()`
  - Added `verify_razorpay_signature()` and secure Razorpay webhook validation
  - Added `/api/webhook/razorpay` + `/webhook/razorpay`
  - Updated WhatsApp webhook to push stream events post-logging
  - Added `/api/transactions/recent?limit=` endpoint
  - Unified transaction persistence into `db.transactions`
- Env updates
  - `backend/.env`: `S2_AUTH_TOKEN`, `S2_BASIN`, `RAZORPAY_WEBHOOK_SECRET`
  - `frontend/.env`: `REACT_APP_S2_AUTH_TOKEN`, `REACT_APP_S2_BASIN`
- Frontend
  - Added S2 stream utility: `/app/frontend/src/lib/stream.js`
  - Replaced starter UI with live transactions dashboard in `/app/frontend/src/App.js`
  - Added responsive styling in `/app/frontend/src/App.css`
  - Added required `data-testid` attributes on interactive and critical UI elements
- Tests
  - Existing and added pytest suites pass (11 total)
  - Verified valid and invalid Razorpay signature behavior via live curl checks
  - Verified dashboard rendering and polling fallback in browser screenshot flow

## Prioritized Backlog
### P0
- Replace placeholder secrets with production values (`S2_AUTH_TOKEN`, `RAZORPAY_WEBHOOK_SECRET`).
- Validate true end-to-end S2 live delivery using a valid token and real webhook traffic.

### P1
- Add WhatsApp/Twilio signature validation parity with Razorpay hardening.
- Add dedupe key strategy across sources for strict idempotency under retries.

### P2
- Add stream health metrics (append success/failure counters, latency stats).
- Add user-level filters/search in dashboard table.

## Next Tasks
1. Set real S2 and Razorpay secrets in env.
2. Fire real Razorpay + WhatsApp webhooks and confirm instant stream prepend behavior.
3. Add Twilio signature verification to complete webhook security baseline.
