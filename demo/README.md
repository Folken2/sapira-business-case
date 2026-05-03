# Demo pack — three live emails for the Sapira pitch

Three runs that exercise the three pipeline outcomes the agent is designed for.

| #   | Email body file  | BOM (attach)                     | Expected outcome    |
|-----|------------------|----------------------------------|---------------------|
| 001 | `email_001.txt`  | `bom_001_harbour9_v1.pdf`        | **DRAFT PO**        |
| 002 | `email_002.txt`  | `bom_002_coast3_v2.pdf`          | **HITL REVIEW**     |
| 003 | `email_003.txt`  | `bom_001_harbour9_v1.pdf` (reused) | **DUPLICATE**     |

All BOMs map to materials in the agent's SAP master so the reconciler hits real codes.

## Files

```
demo/
├── README.md                              ← this file
├── _template.css                          ← shared CSS for both BOM PDFs
├── bom_001_harbour9_v1.html / .pdf        ← clean BOM
├── bom_002_coast3_v2.html / .pdf          ← revision with margin notes (rendered red, hand-written font)
├── email_001.txt                          ← email body for run #1
├── email_002.txt                          ← email body for run #2
└── email_003.txt                          ← forwarded version of #1 (no new PDF — reuse 001's)
```

## Re-rendering the PDFs after edits

The PDFs are generated from the HTMLs via Chrome headless. After tweaking either BOM:

```bash
cd /Users/albertfolch/Documents/Cursor/sapira/demo
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for f in bom_001_harbour9_v1 bom_002_coast3_v2; do
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$(pwd)/${f}.pdf" \
    --virtual-time-budget=4000 \
    "file://$(pwd)/${f}.html"
done
```

`--virtual-time-budget=4000` waits for the Google Fonts (Inter, Caveat) to load before rendering.

## Run #1 — Clean BOM (→ DRAFT PO)

Send `email_001.txt` body with `bom_001_harbour9_v1.pdf` attached.

**Expected:**
- `email_type`: `NEW_BOM` · `project`: `HARBOUR-9` · `bom_revision`: `v1`
- 4 line items extracted, all 4 reconcile cleanly to SAP codes (>0.85 confidence)
- `hitl_queue`: empty
- `draft_purchase_order`: created
- Reply email: `[BOM Pipeline] Draft PO ready: DRAFT-...`

## Run #2 — Revision with margin notes (→ HITL REVIEW)

Send `email_002.txt` body with `bom_002_coast3_v2.pdf` attached.

**Expected:**
- `email_type`: `REVISION` · `project`: `COAST-3` · `bom_revision`: `v2`
- 5 line items extracted; lines 1–4 reconcile cleanly
- Line 5 ("cold-rolled ~1.2mm premium") has no exact match in SAP master (only 1.0mm and 1.5mm) → low confidence → flagged via `flag_for_hitl_tool`
- `hitl_queue` non-empty → `hitl_gate` blocks PO creation
- `draft_purchase_order`: **null**
- Reply email: `[BOM Pipeline] Review needed (1 lines)`

This is the demo's highlight — the system **doesn't blindly automate**.

## Run #3 — Forwarded duplicate (→ DUPLICATE)

Send `email_003.txt` body with `bom_001_harbour9_v1.pdf` re-attached (same file, deliberately).

**Expected:**
- `email_type`: `DUPLICATE`
- `line_items`: empty (per the prompt's DUPLICATE rule)
- `global_notes`: dedup reason
- `draft_purchase_order`: **null**, `hitl_queue`: empty
- Reply email: `[BOM Pipeline] Email classified as duplicate / non-BOM`

This proves the system **won't double-order**.

## Demo running order (5–6 min total)

1. **Set the stage (30s):** "Aceros Ibéricos gets messy procurement emails. Three real ones."
2. **Run #1 — DRAFT PO (90s):** Send Email 001. Watch n8n → agent → reply with the DRAFT PO. *"Clean email, clean output, zero human time."*
3. **Run #2 — HITL (120s):** Send Email 002. Show the agent **stops before PO creation** and asks for review. *"This is the part that wins trust — the agent knows what it doesn't know."*
4. **Run #3 — DUPLICATE (60s):** Send Email 003. Show the forward is recognised. *"The boring failure mode that costs companies real money — solved."*
5. **Wrap (30s):** "Same prompt chain, three different judgments, all correct."

## Pre-demo dress rehearsal

Send #001 first as a smoke test **before** the real pitch. If it returns a DRAFT PO, the whole pipeline is healthy.
