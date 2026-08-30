# CycloneAI Backend

Minimal FastAPI service. Right now it exposes one real feature: an AI chat
endpoint that backs the "CycloBot" widget on every frontend page, powered by
**OpenRouter's free model tier** (no cost, no credit card required). Everything
else described in the top-level README (auth, DB, ML endpoints, etc.) is still
on the roadmap — this is just enough to make the chatbot a genuine AI assistant
instead of a hardcoded keyword matcher.

## Get a free API key

1. Go to [openrouter.ai](https://openrouter.ai) and sign in (Google or email — no card needed).
2. Click your profile icon → **Keys** → **Create Key**.
3. Copy the key (starts with `sk-or-v1-...`). It's only shown once.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste in your OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

The server starts at `http://localhost:8000`. Check `http://localhost:8000/api/health`
to confirm `ai_configured` is `true`.

## Which model does it use?

By default, `meta-llama/llama-3.3-70b-instruct:free` — a stable, long-running
free model on OpenRouter. If that model is rate-limited or gets delisted (the
free lineup rotates often), the backend automatically retries with
`openai/gpt-oss-20b:free`, then `openrouter/free` (OpenRouter's own auto-router
that picks whatever free model is currently working).

You can change any of this in `.env` without touching code:

```bash
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
OPENROUTER_FALLBACK_MODELS=openai/gpt-oss-20b:free,openrouter/free
```

Check the live free-model list any time at
[openrouter.ai/models?max_price=0](https://openrouter.ai/models?max_price=0)
before picking a different primary model.

### Free-tier limits (as of this writing)

- 20 requests/minute per key on any `:free` model.
- 50 requests/day if your account has never added credits; **1,000/day** once
  you've added at least $10 in credits one time (the higher limit persists
  even if your balance drops back to $0 afterward).

These are OpenRouter's limits, not something this backend enforces — check
[openrouter.ai/docs/api/reference/limits](https://openrouter.ai/docs/api/reference/limits)
for the current numbers.

## Endpoint

`POST /api/chat`

```json
{
  "message": "Why do cyclones curve away from the equator?",
  "history": [
    { "role": "user", "content": "What is a cyclone?" },
    { "role": "assistant", "content": "A tropical cyclone is..." }
  ]
}
```

Response:

```json
{ "reply": "Cyclones curve poleward mainly because..." }
```

`history` is optional and capped at the last 12 turns server-side, so the model
keeps conversational context without an unbounded request growing forever.

## Emergency help-request endpoint

`POST /api/help-requests` — used by the **Report / Request Help** form
(`frontend/report.html`). Submissions are validated (name, mobile, state,
district, emergency types, consent, etc.), given a reference id, and appended
to a local JSON-lines file (`data/help_requests.jsonl` by default; override the
path with the `HELP_REQUESTS_FILE` env var).

```json
{
  "full_name": "Asha Devi",
  "mobile": "9876543210",
  "email": null,
  "state": "Odisha",
  "district": "Puri",
  "village_city": "Konark",
  "current_location": "Roof of the panchayat building, near the beach road",
  "people_affected": 12,
  "children": 3,
  "elderly_disabled": 2,
  "emergency_types": ["Rescue Required", "Drinking Water Required"],
  "description": "Water is entering the shelter, we need evacuation.",
  "image": null,
  "consent": true
}
```

On success it returns `{ "status": "ok", "id": "HR-...", "message": "..." }`.

`GET /api/help-requests` returns only **aggregate counts** (total received and
requests grouped by emergency type) — personal details are never exposed
through a public route.

### Offline behaviour on GitHub Pages

The static site is served from GitHub Pages without a live backend. The form
tries this endpoint first; if it is unreachable, the request is stored in the
browser's `localStorage` so a person's emergency data is not lost, and a notice
is shown. Point the frontend at a deployed backend with:

```html
<script>window.CYCLOTRACK_API_BASE = "https://api.example.com";</script>
```

See `frontend/assets/helpreport.js`.

## Pointing the frontend at this server

Open any page (`frontend/index.html`, etc.) and, before the `chatbot.js` script
tag, set:

```html
<script>window.CYCLOBOT_API_URL = "http://localhost:8000/api/chat";</script>
<script src="assets/chatbot.js" defer></script>
```

If you don't set `window.CYCLOBOT_API_URL`, the widget defaults to
`http://localhost:8000/api/chat` for local dev. In production, deploy this
backend and point that URL at its real address (and set `CORS_ORIGINS` in
`.env` to your deployed frontend's origin instead of `*`).

If the backend is unreachable, not configured, or every free model fails, the
widget automatically falls back to its old offline knowledge base so the demo
never breaks — it just becomes less capable until the AI backend is back.

## Notes

- Never commit `.env` — it holds your real API key.
- `max_tokens` is capped at 700 per reply to keep the widget snappy; raise it
  in `app/main.py` if you want longer answers.
- CORS defaults to `*` for easy local testing; lock it down before deploying.
- Free OpenRouter models can be slower or less consistent than paid models —
  that's the trade-off for zero cost. If you later want more reliability,
  swap `OPENROUTER_MODEL` for a paid OpenRouter model ID (drop the `:free`
  suffix) and add credits to your account; no code changes needed.
