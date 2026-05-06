# PHARO — BOM Procurement Agent

Multi-agent pipeline that turns supplier procurement emails into reconciled, draft purchase orders. Built on Google ADK for the Aceros Ibéricos pilot.

```
extract → validate (loop) → reconcile to SAP → HITL gate → draft PO
```

---

## Setup (once)

```bash
cd agent/bom-procurement-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add OPENROUTER_API_KEY
```

---

## Run it

### 1. ADK web UI — interactive dev

The fastest way to poke the agent: open a chat, paste an email, watch every tool call and state mutation in the side panel.

```bash
DEV_MODE=true adk web .
```

Then open http://localhost:8000 and pick `bom_procurement_agent` from the agent dropdown.

### 2. FastAPI server — programmatic access

Same agent, exposed as HTTP. Use this from n8n, scripts, or the front-end.

```bash
DEV_MODE=true python run_adk.py
```

- Server: `http://localhost:8000`
- Streaming endpoint: `POST /run_sse/`
- Health: `GET /health`

### 3. Batch driver — run the full sample corpus

```bash
.venv/bin/python scripts/run_all_emails.py            # all sample emails
.venv/bin/python scripts/run_all_emails.py email_001  # one email
```

Outputs land in `output/` (`DRAFT-*.json` POs, `trace-*.json` snapshots).

---

## Deploy to Railway

Ships with `Dockerfile` + `railway.json` — no extra config needed.

```bash
brew install railway        # or: npm install -g @railway/cli
railway login
railway init                # "Empty Project"
railway up                  # build + deploy
```

### Required env vars

Set in the Railway dashboard (or `railway variables --set KEY=VALUE`):

| Variable | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | OpenRouter key |
| `API_KEY` | recommended | Bearer auth on every endpoint except `/health` |
| `DEV_MODE` | optional | `true` = in-memory sessions, no DB |
| `SESSION_SERVICE_URI` | optional | Postgres URL for persistent sessions |

### Persistent sessions (optional)

1. Add the Postgres plugin in Railway.
2. Copy its `DATABASE_URL` into `SESSION_SERVICE_URI` on the agent service.
3. Set `DEV_MODE=false`.

Railway polls `/health` to gate traffic — public, no auth, defined in `railway.json`.

---

## Tests

Recordings live under `tests/recordings/` — replay is free, no LLM calls.

```bash
python -m pytest tests/test_agent.py -v          # replay
RECORD=true python -m pytest tests/test_agent.py # re-record (hits the LLM)
```

---

## Where things live

```
bom_procurement_agent/
  agent.py        # SequentialAgent: extract→validate loop, reconcile, PO
  prompt/         # one prompt constant per sub-agent
  tools/          # FunctionTools (HITL flagging, PO writer, loop control)
  skills/         # SKILL.md folders, auto-discovered
  contexts/       # .md domain knowledge, auto-injected into prompts
  callbacks/      # hitl_gate, pydantic validators
  plugins/        # cost guard, trace, cache, resilience, memory, …
  config/llm.py   # FAST_MODEL / REASONING_MODEL
  models.py       # Pydantic schemas (LineItem, Extraction, …)
```

Adding capability:

- **Tool** → write a function in `tools/`, wrap with `FunctionTool`, register in `agent.py`.
- **Skill** → create `skills/<name>/SKILL.md`. Auto-loaded.
- **Domain knowledge** → drop a `.md` in `contexts/`. Auto-injected.
- **Model pricing** → edit `plugins/pricing.json` (no code change).

See `.env.example` for the full env-var reference.
