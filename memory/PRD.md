# PRD: WhatsApp Invoice Image Parsing with Unsiloed

## Original Problem Statement
Add invoice image parsing to the existing WhatsApp webhook.
When a Twilio WhatsApp message comes in with an image attachment (NumMedia > 0), call the Unsiloed AI API before anything else to extract invoice fields.
Wire it into /webhook/whatsapp and pass amount/payer into log_transaction() and GST calculator.
Add UNSILOED_KEY to .env. If Unsiloed fails or returns no amount, fall back to parsing raw message text as before.

## Architecture Decisions
- Implemented webhook processing in `backend/server.py` with both routes:
  - `/webhook/whatsapp` (direct backend path)
  - `/api/webhook/whatsapp` (router-prefixed path for external app URL testing)
- Added `parse_invoice_image()` using `requests.post` to Unsiloed extraction endpoint and env key `UNSILOED_KEY`.
- Added resilient fallback flow:
  1) If image media exists, try Unsiloed extraction first.
  2) If API fails or amount missing, parse raw message text.
- Added `log_transaction()` persistence to MongoDB and `calculate_gst()` calculation.
- Added helper parsing utilities for amount normalization and text extraction.

## What’s Implemented
- `UNSILOED_KEY` added to `backend/.env`.
- New invoice extraction helper:
  - Calls `https://api.unsiloed.ai/v1/extraction`
  - Extract fields: amount, payer, date, gstin
- WhatsApp webhook endpoint now:
  - Reads `NumMedia`, `MediaUrl0`, `MediaContentType0`, `Body`
  - Calls Unsiloed first when image present
  - Falls back to raw text parsing on Unsiloed failure/no amount
  - Logs transaction and returns GST summary in response
- Verified via curl on external API URL that:
  - Text-only flow works
  - Image flow with missing key safely falls back to text parsing

## Prioritized Backlog
### P0
- Set real `UNSILOED_KEY` in backend env for production extraction.
- Validate end-to-end with actual Twilio WhatsApp image payloads.

### P1
- Improve payer extraction regex to avoid over-capturing long trailing text.
- Add webhook signature verification for Twilio security.
- Add response formatting compatible with TwiML if required by upstream flow.

### P2
- Add structured audit logs (extraction latency, failure reasons, fallback cause).
- Add automated tests for: image success, image failure fallback, no-media text parse.

## Next Tasks
1. Configure live Unsiloed key and test with real invoice images.
2. Tighten parsing quality and add test coverage for edge cases.
3. Add Twilio request validation and harden webhook reliability.
