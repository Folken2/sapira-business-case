# bom-console

Demo console for the **Sapira BOM procurement pipeline** (PHARO Client Founder
business case — Aceros Ibéricos pilot).

A single-page Next.js app that visualises the multi-agent BOM pipeline
end-to-end: incoming email → extractor → validator → reconciler → PO creator
or HITL gate. Reads pre-recorded run JSON so the demo never depends on a live
LLM call during the presentation.

## Stack

- Next.js 15 (App Router) · React 19 · TypeScript 5.9
- Tailwind CSS 4
- `lucide-react` icons; `clsx` + `tailwind-merge` for class composition
- No backend, no auth, no DB — runs read from `src/data/runs/*.json`

## Run it

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
```

## Layout

```
src/
├── app/
│   ├── api/run/route.ts    GET /api/run?email_id=… → returns one Run JSON
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx            three-column UI: inbox · trace · outcome
├── components/
│   ├── EmailInbox.tsx      left column — sample email list
│   ├── EmailPreview.tsx    centre top — raw email + attachments
│   ├── PipelineSteps.tsx   centre bottom — staggered agent step playback
│   └── ResultPanel.tsx     right column — DRAFT PO, HITL review, or DUPLICATE
├── data/runs/              pre-recorded pipeline outputs (one JSON per email)
└── lib/
    ├── runs.ts             typed access to data/runs/*.json
    ├── types.ts            TypeScript mirror of the agent's Pydantic models
    └── utils.ts            cn(), formatMs(), formatRelative()
```

## Sample emails

| email_id                  | scenario                                   | outcome      |
| ------------------------- | ------------------------------------------ | ------------ |
| `email_001_clean_pdf`     | New BOM, PDF attachment, all clean         | DRAFT PO     |
| `email_002_messy_body`    | Revision + new line + margin note (HITL)   | HITL REVIEW  |
| `email_003_duplicate`     | Forwarded copy of email_002                | DUPLICATE    |

## Connecting to a live agent run

Today: pre-recorded JSON in `src/data/runs/` is the source of truth.

To swap to live data, replace the GET handler in `src/app/api/run/route.ts`
with one that either (a) shells out to the Python agent and waits for the
output trace under `agent/bom-procurement-agent/output/`, or (b) hits the
ADK FastAPI server at `:8000` and converts ADK events into the `Step[]` shape
defined in `src/lib/types.ts`.
