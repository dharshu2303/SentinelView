TRACK_ID=PS6

SentinelView is a transaction risk investigation assistant for a bank fraud desk demo. It analyzes one customer’s historical transactions with deterministic risk rules, then (optionally) uses Gemini to produce a grounded narrative for investigators.

## What this project does
- Loads synthetic transaction histories for 7 customers (3–6 months, 50–150 tx each).
- Runs deterministic rules for:
  1. unusually large transfers,
  2. burst to a newly added payee,
  3. odd-hours activity based on customer-specific activity hours,
  4. pattern-break behavior (unseen channel/region).
- Produces a report where the first finding clearly states whether attention is needed.
- Keeps every cited transaction traceable to source row IDs.
- Never declares fraud; it flags activity for investigator review.
- Serves backend + frontend from one process at `http://localhost:8000`.

## Run (fresh clone)
```bash
pip install -r requirements.txt
copy .env.example .env  # or edit the provided .env file directly
python app.py
```
Then open: `http://localhost:8000`

## Gemini setup
- Open `.env` in the project root.
- Paste your Gemini API key into `GEMINI_API_KEY=`.
- Leave it blank to run the app in deterministic fallback mode.
- Optional: set `GEMINI_NARRATIVE_MODEL` or `GEMINI_EMBEDDING_MODEL` if you need to override the defaults.

## API
- `GET /api/customers`
- `GET /api/customers/{id}/transactions`
- `POST /api/customers/{id}/investigate`
  - optional payload: `{ "simulate_gemini_failure": true }` to demo graceful fallback

## How this is engineered
### 1) Deterministic layer (no LLM)
- File: `/home/runner/work/transaciq/transaciq/src/rules_engine.py`
- Pure, deterministic rule functions return structured results:
  - `rule_id`, `rule_name`, `triggered`, `matched_transaction_ids`, `baseline_stats`, `severity`
- This layer alone decides clean vs flagged (`rule_engine_verdict`).

### 2) LLM reasoning layer (Gemini only)
- File: `/home/runner/work/transaciq/transaciq/src/gemini_narrator.py`
- Uses Gemini for:
  - embeddings (`gemini-embedding-001`) to rank supporting context,
  - narrative generation (`gemini-2.0-flash`) from deterministic findings + provided transaction rows.
- System guardrails in prompt + code enforcement:
  - only reference provided transactions,
  - no speculation,
  - never state fraud has occurred.
- If Gemini fails/timeouts/malformed response, app returns deterministic fallback with explicit notice:
  - `AI narrative unavailable — showing rule-engine findings directly.`

## Data generated
- `/home/runner/work/transaciq/transaciq/data/generate_data.py` (deterministic generation via `random.seed(42)`)
- `/home/runner/work/transaciq/transaciq/data/transactions.csv`
- `/home/runner/work/transaciq/transaciq/data/customers.json`
- `/home/runner/work/transaciq/transaciq/data/README.md`

Profiles included:
- `C001`, `C002`: clean routine activity
- `C003`: large transfer only
- `C004`: new payee burst only
- `C005`: odd-hours only
- `C006`: pattern-break only
- `C007`: multiple rules overlap

## Frontend
Prebuilt files served directly by Flask:
- `/home/runner/work/transaciq/transaciq/frontend/dist/index.html`
- `/home/runner/work/transaciq/transaciq/frontend/dist/app.js`
- `/home/runner/work/transaciq/transaciq/frontend/dist/style.css`

Includes:
- dark fintech operations UI,
- animated investigation loading state,
- section-by-section report reveal,
- clickable narrative claims that highlight cited transaction rows,
- timeline with flagged transaction markers.

## Validation key
`VALIDATION_KEY_HERE`

## Demo video
`DEMO_VIDEO_LINK_HERE`
