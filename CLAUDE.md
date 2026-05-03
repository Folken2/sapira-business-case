# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

This repo contains the deliverables for the **Sapira AI × Aceros Ibéricos** Client Founder business case. It is a **multi-project** workspace with three independent top-level pieces:

- `agent/bom-procurement-agent/` — Python Google ADK multi-agent pipeline that ingests procurement emails, extracts BOMs, reconciles to SAP material codes, and drafts purchase orders. This is the primary technical deliverable.
- `frontend/` — Next.js 15 demo console (`bom-console`) that visualises the pipeline end-to-end: incoming email → extractor → validator → reconciler → PO creator OR HITL gate. Reads pre-recorded run JSON from `src/data/runs/*.json` (TypeScript types in `src/lib/types.ts` mirror the agent's Pydantic models in `agent/bom-procurement-agent/bom_procurement_agent/models.py`).
- `business-case/` — assignment artefacts and the pitch deck:
  - `business-case/Client founder _ FDE business case.pdf` — original brief (Spanish/English).
  - `business-case/email.md` — context email; read this first.
  - `business-case/deck/index.html` — self-contained pitch deck (8 slides, 16:9) presented at the pilot kickoff. See [Pitch Deck](#pitch-deck-business-casedeck) below.

The two code projects share data shapes (Pydantic ↔ TypeScript) but are otherwise decoupled: separate dependencies, separate run loops, no shared runtime. The frontend currently reads pre-baked JSON; swapping to a live agent would require replacing the GET handler in `frontend/src/app/api/run/route.ts`.

### Brand identity (don't mix these up)

- **Sapira AI** is the *company* that delivers the engagement (Client Founder = Albert Folch).
- **PHARO** is the *product* — the multi-agent procurement automation platform Sapira AI sells.

In any client-facing artefact (decks, READMEs, public docs), the engaging party is "Sapira AI" and the technology is "PHARO". Internally the codebase is named after the platform.

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

# Tests (record/replay — no LLM cost on replay; recordings under tests/recordings/)
python -m pytest tests/test_agent.py -v                  # replay
RECORD=true python -m pytest tests/test_agent.py -v      # re-record (hits LLM)
python -m pytest tests/test_agent.py -v -k test_golden   # filter to one test
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

Cross-cutting plugins are registered globally (see `bom_procurement_agent/plugins/` and `scripts/run_all_emails.py` for which subset each entry-point uses): `CostGuardPlugin`, `TracePlugin`, `StatePlugin`, `ConsoleLoggerPlugin`, `ToolEventsPlugin`, `ContextFilterPlugin`, `CachePlugin`, `ResiliencePlugin`, `ReflectAndRetryToolPlugin`, `SaveFilesAsArtifactsPlugin`, `MemoryPlugin`. Pricing for `CostGuardPlugin` is data-driven via `plugins/pricing.json` — add new models there, no code changes.

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

## Pitch Deck (`business-case/deck/`)

A self-contained, single-file HTML deck (`index.html`, no build step, no dependencies). Used at the Aceros Ibéricos pilot kickoff (15-min present + 30-min Q&A). Open it directly in a browser — no server needed.

### Design language

Mirrors the **sapira.ai** editorial-minimalist aesthetic:

- **Palette**: bone background (`#F5F5F3`), near-black ink (`#1a1a1a`), monochrome accent. Operational colors only (`--warn` burnt amber for friction, `--ok` green for milestones, `--hitl` ochre for human-in-the-loop). No brand blue.
- **Type**: light-weight Geist for display, italic *Source Serif 4* for editorial accents (the `<em>` words in titles), Geist Mono for small-caps tags and captions.
- **Stage**: every slide is locked to **16:9** via `aspect-ratio` on a `.stage` wrapper. Type sizes use `cqi` (container-query inline-size) units so headlines, code, and tables scale with the slide, not the viewport — content can never overflow.
- **Reference**: `docs/training-agents-venn.html` was used as the structural reference for the slide pager, dot navigation, mono-caps tags, and dark/light toggle. The CSS architecture mirrors it but the visual language is pure Sapira.

### Slide structure (8 slides — within the brief's 6–8 limit)

1. **Title** — Multi-agent BOM procurement automation (Aceros Ibéricos · prepared by Albert Folch, Client Founder, Sapira AI)
2. **The bet** — three KPIs: 24–48h cycle time · 15 FTE · €350K cost-of-error
3. **As-Is** — four manual handoffs (combined Monitor & Triage), friction strip 1:1 aligned per step
4. **To-Be** — PHARO pipeline (extractor → validator loop → reconciler → HITL gate → PO drafter) + automated/HITL/out-of-scope triptych
5. **Data & reconciliation** — `LineItem` Pydantic schema mirrored from `models.py` + the 4-step Friction #2 flow: ground-truth map (from labelled corpus) → reconciler agent reasons → HITL gate → **self-learning loop** (every HITL decision feeds the map)
6. **Week-1 IT readiness** — 5 concrete asks + 1 design-decision note ("no parallel auth system" — audit lives in SAP)
7. **8-week playbook** — three proportional phase blocks (Discovery W1–2 / Build W3–4 / Pilot W5–8) with gates: 95% extraction accuracy → 90% auto-drafted correctly → 90% auto-approved live
8. **Project communication** — daily/weekly/bi-weekly cadence + 4 success metrics (cycle time, auto-approved rate, wrong SAP codes, procurement hours freed)

### Controls

- **← / →** or PageUp/PageDown or Space — navigate
- **Home / End** — jump to first / last slide
- **Dark** pill (top-right) — toggles theme; persists to `localStorage`
- **PDF** pill — triggers `window.print()` with one-slide-per-page styling for the PDF deliverable the brief asks for (24h before the live defense)
- **Hash routing** — `index.html#data` deep-links to a specific slide (useful for live presenting and for screenshots)

### Editing principles (learned the hard way during this session)

- **Schema on Slide 5 must mirror `agent/bom-procurement-agent/bom_procurement_agent/models.py`.** If `models.py` changes, update the slide. Never invent fields the codebase can't back up — the IT Director will check.
- **Plain English over enterprise jargon.** No "SME", "SSO", "RAID", "Sev-1", "steerco", "smell-tests", "straight-through", "FTE re-deployed". Each was rewritten this session.
- **No embeddings in the messaging.** Reconciliation is described as agent reasoning + tool lookup + ground-truth map + self-learning loop. Pure agent story.
- **Audit lives in SAP, not in our console.** Slide 6 explicitly pre-empts the SSO question — we don't introduce a parallel auth system; SAP's existing identity signs every DRAFT → live PO confirmation.
- **Footers must align across blocks.** On Slide 7, the gate dashed-rule is a separate `::after` pseudo-element pinned to a fixed `bottom` Y, *not* attached to the gate content (which has variable height). Don't undo this.

### What's intentionally out of scope on the deck

- A closing "thank you / Q&A" slide. The deck ends on Slide 8 (Project communication) so the success metrics stay visible during Q&A.
- Live SAP commit. The pilot writes DRAFT POs only; live commit is post-pilot.
- Any non-steel commodity, CAD-drawing OCR beyond exported PDF text, or live SSO discussion.
