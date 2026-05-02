# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

This repo contains the deliverables for the PHARO Sapira / Aceros Ibéricos FDE business case. It is a **multi-project** workspace with three independent top-level pieces:

- `agent/bom-procurement-agent/` — Python Google ADK multi-agent pipeline that ingests procurement emails, extracts BOMs, reconciles to SAP material codes, and drafts purchase orders. This is the primary deliverable.
- `frontend/` — Next.js 15 demo console (`bom-console`) that visualises the pipeline end-to-end: incoming email → extractor → validator → reconciler → PO creator OR HITL gate. Reads pre-recorded run JSON from `src/data/runs/*.json` (TypeScript types in `src/lib/types.ts` mirror the agent's Pydantic models in `agent/bom-procurement-agent/bom_procurement_agent/models.py`).
- `business-case/` — PDF brief and email defining the assignment (Spanish). Read `business-case/email.md` for context on what is being built and why.

The two code projects share data shapes (Pydantic ↔ TypeScript) but are otherwise decoupled: separate dependencies, separate run loops, no shared runtime. The frontend currently reads pre-baked JSON; swapping to a live agent would require replacing the GET handler in `frontend/src/app/api/run/route.ts`.

## BOM Procurement Agent (`agent/bom-procurement-agent/`)

### Commands

All commands run from `agent/bom-procurement-agent/`:

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENROUTER_API_KEY

# Run the agent server (FastAPI on :8000)
DEV_MODE=true python run_adk.py

# Or the ADK web UI
DEV_MODE=true adk web .

# Drive the pipeline against every sample email and print a summary table
.venv/bin/python scripts/run_all_emails.py
.venv/bin/python scripts/run_all_emails.py email_001 email_002   # subset

# Tests (record/replay — no LLM cost on replay)
python -m pytest tests/test_agent.py -v                  # replay
RECORD=true python -m pytest tests/test_agent.py -v -k test_golden  # re-record
```

### Architecture

The root agent is a `SequentialAgent("bom_pipeline")` defined in `bom_procurement_agent/agent.py`:

```
SequentialAgent("bom_pipeline")
  ├── LoopAgent("extract_validate_loop", max_iterations=3)
  │     ├── LlmAgent("extractor")   output_key="extraction"
  │     └── LlmAgent("validator")   (calls exit_validation_loop OR
  │                                  request_extraction_revision)
  ├── LlmAgent("reconciler")        output_key="reconciliation"
  └── LlmAgent("po_creator")        output_key="po_summary"
```

Key behaviors that span multiple files:

- **Validation loop**: the validator LLM exits the loop by calling `exit_validation_loop_tool`, or pushes feedback into session state via `request_extraction_revision_tool`; the extractor reads that feedback on the next iteration. Both tools live in `tools/bom_tools.py`.
- **HITL gate**: `po_creator` has a `before_agent_callback=hitl_gate` (`callbacks/hitl_gate.py`) that **blocks PO creation when any reconciled line is on the HITL queue**. This is intentional — see commit `9a773fe`. The reconciler routes low-confidence SAP matches to HITL via `flag_for_hitl_tool`.
- **Pydantic validation**: `after_agent_callback=validate_agent_output(...)` (extractor, reconciler) and `before_tool_callback=validate_tool_args(...)` (po_creator) enforce schemas from `models.py`. If extractor output fails `Extraction` validation, the loop retries.
- **State seeding**: `seed_volume_if_empty()` runs at import time to load `data/sap_material_master.json` and sample emails into the in-memory volume.
- **Prompts** live in `prompt/sub_agents.py` (one constant per sub-agent). `contexts/` `.md` files are auto-injected into prompts. `skills/` subdirectories with `SKILL.md` are auto-discovered via `SkillToolset`.
- **Models**: `FAST_MODEL` and `REASONING_MODEL` are configured in `config/llm.py` — extractor/reconciler use the reasoning model, validator/po_creator use fast.

### Plugin chain

10 cross-cutting plugins are registered globally (see `bom_procurement_agent/plugins/` and `scripts/run_all_emails.py` for which subset each entry-point uses): `CostGuardPlugin`, `TracePlugin`, `ConsoleLoggerPlugin`, `ToolEventsPlugin`, `ContextFilterPlugin`, `CachePlugin`, `ResiliencePlugin`, `ReflectAndRetryToolPlugin`, `SaveFilesAsArtifactsPlugin`, `MemoryPlugin`. Pricing for `CostGuardPlugin` is data-driven via `plugins/pricing.json` — add new models there, no code changes.

### Outputs

- `output/DRAFT-*.json` — drafted purchase orders (written by `create_purchase_order_tool`)
- `output/trace-*.json` — consolidated per-run state snapshots (StatePlugin)
- `traces/*.jsonl` + `traces/conversations/*.json` — raw event stream and conversation export (TracePlugin)
- `memory/AGENT_MEMORY.md` — long-term markdown memory (MemoryPlugin)

### Adding capability

- **Tool**: write a function in `tools/`, wrap with `FunctionTool`, register in the relevant agent's `tools=[...]` list in `agent.py`.
- **Skill**: create `skills/<name>/SKILL.md` (frontmatter + body). Auto-discovered.
- **Domain knowledge**: drop a `.md` file in `contexts/`. Auto-injected into the system prompt.

### Deployment

Railway-ready: `Dockerfile` + `railway.json`. `railway up` from the agent directory. Health check is `/health` (public, no auth). See the agent's `README.md` for the full env-var reference.

## Frontend (`frontend/` — `bom-console`)

Single-page Next.js 15 / React 19 / Tailwind 4 demo. No auth, no DB, no
backend — it reads pre-recorded run JSON from `src/data/runs/`. See
`frontend/README.md` for the file-by-file map.

Commands (from `frontend/`):
```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

Layout in one breath:
```
src/
├── app/
│   ├── api/run/route.ts    GET /api/run?email_id=… → one Run JSON
│   ├── layout.tsx · page.tsx · globals.css · favicons
├── components/    EmailInbox · EmailPreview · PipelineSteps · ResultPanel
├── data/runs/     email_001 · email_002 · email_003 (JSONs)
└── lib/           runs.ts · types.ts · utils.ts
```

Three sample emails cover the three demo outcomes: clean → DRAFT PO,
revision-with-margin-note → HITL REVIEW, forwarded copy → DUPLICATE.

To go live: replace the GET handler in `src/app/api/run/route.ts` with one
that either shells out to the Python agent and reads
`agent/bom-procurement-agent/output/trace-*.json`, or talks to the ADK
FastAPI server on `:8000` and converts ADK events into the `Step[]` shape
defined in `src/lib/types.ts`.
