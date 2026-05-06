# PHARO × Aceros Ibéricos

Multi-agent BOM procurement automation — pitch deck, agent, and demo artefacts.

---

## What's in this repo

| Path | What it is |
|---|---|
| [`agent/bom-procurement-agent/`](agent/bom-procurement-agent/) | **PHARO** — Python / Google ADK pipeline that turns supplier emails into reconciled, draft purchase orders. The primary technical deliverable. |
| [`business-case/`](business-case/) | The original brief and the pitch deck. |
| [`business-case/deck/index.html`](business-case/deck/index.html) | Self-contained 8-slide pitch deck (16:9). Open in a browser — no build step. |
| [`business-case/deck/deck.pdf`](business-case/deck/deck.pdf) | Printable PDF version of the deck. |
| [`demo/`](demo/) | Sample procurement emails, generated BOM PDFs, and the n8n Gmail → BOM ingestion workflow. |

---

## The pipeline at a glance

```
email ──▶ extract ──▶ validate (loop) ──▶ reconcile to SAP ──▶ HITL gate ──▶ draft PO
```

- **Extractor / validator loop** — re-runs until the validator is satisfied.
- **Reconciler** — matches each line to a SAP material code; low-confidence rows go to the human-in-the-loop queue.
- **HITL gate** — blocks PO creation while any line is pending review.
- **PO drafter** — writes a `DRAFT-*.json` purchase order.

Architecture, prompts, tools, and plugins are documented in the agent's own README.

---

## Run it

### Agent (dev)

```bash
cd agent/bom-procurement-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # add OPENROUTER_API_KEY

DEV_MODE=true adk web .              # interactive UI at :8000
# or
DEV_MODE=true python run_adk.py      # FastAPI server at :8000
```

Full instructions, env vars, and Railway deploy: [`agent/bom-procurement-agent/README.md`](agent/bom-procurement-agent/README.md).

### Pitch deck

```bash
open business-case/deck/index.html
```

Use **← / →** to navigate. Press the **PDF** pill to print one slide per page.

### Demo

Sample emails and the n8n workflow live in [`demo/`](demo/). The workflow watches a Gmail inbox, fires the agent for each new procurement email, and stores the resulting BOM.

---

## Brief recap

The pilot targets three KPIs — **24–48h** procurement cycle time, **15 FTE** of manual processing, **€350K** annual cost-of-error. The 8-week playbook (Discovery → Build → Pilot) is on slide 7 of the deck.
