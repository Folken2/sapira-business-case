"""Drive the BOM pipeline against every sample email and summarise results.

Usage:
    .venv/bin/python scripts/run_all_emails.py [email_id ...]

With no arguments: runs every JSON file in
`bom_procurement_agent/data/sample_emails/`.
With ids: runs only those (e.g. `email_001 email_002`).

Each run:
  - Spawns a fresh in-memory session (no cross-email state contamination).
  - Drives the SequentialAgent end-to-end via InMemoryRunner.
  - Lets the StatePlugin write `output/trace-*.json` and the PO tool write
    `output/DRAFT-*.json` (their normal side-effects).
  - Captures a one-line summary per email for the table at the end.

Run-time prerequisites:
  - `.env` with `OPENROUTER_API_KEY` (or whatever provider FAST/REASONING_MODEL use).
  - `pip install -r requirements.txt` (already done in .venv).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

# Make the package importable when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bom_procurement_agent.agent import root_agent  # noqa: E402
from bom_procurement_agent.plugins import (  # noqa: E402
    cost_guard,
    state as state_plugin,
    tool_events,
    trace as trace_plugin,
)

load_dotenv()
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(name)-30s  %(levelname)-7s  %(message)s",
)

EMAILS_DIR = (
    Path(__file__).resolve().parent.parent
    / "bom_procurement_agent"
    / "data"
    / "sample_emails"
)


def _discover_email_ids() -> list[str]:
    """Return sorted email ids (filename stem) found on disk."""
    return sorted(p.stem for p in EMAILS_DIR.glob("*.json"))


async def _run_one(runner: InMemoryRunner, email_id: str) -> dict:
    """Run the pipeline for a single email and return a summary dict."""
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="bench",
    )
    prompt = f"Process {email_id}."
    final_state: dict = {}
    final_text: str = ""
    error: str | None = None

    try:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
        ):
            # Capture the last textual output from the pipeline (po_creator's summary).
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and not part.thought:
                        final_text = part.text
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"

    # Refresh session to get final committed state
    refreshed = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    if refreshed is not None:
        final_state = dict(refreshed.state)

    extraction = _safe_parse_json(final_state.get("extraction"))
    reconciliation = _safe_parse_json(final_state.get("reconciliation"))
    hitl_queue = final_state.get("hitl_queue") or []
    po = _safe_parse_json(final_state.get("draft_purchase_order"))

    return {
        "email_id": email_id,
        "error": error,
        "email_type": (extraction or {}).get("email_type"),
        "project": (extraction or {}).get("project"),
        "bom_revision": (extraction or {}).get("bom_revision"),
        "n_lines": len((extraction or {}).get("line_items", []) or []),
        "n_reconciled": len(
            (reconciliation or {}).get("reconciled_lines", []) or []
        ),
        "n_hitl": len(hitl_queue),
        "po_number": (po or {}).get("po_number"),
        "summary_text": final_text.strip()[:240],
    }


def _safe_parse_json(value):
    if not value:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _print_summary(results: list[dict]) -> None:
    print()
    print("─" * 100)
    print(
        f"{'email_id':<14} {'type':<10} {'project':<14} "
        f"{'lines':>5} {'recon':>5} {'hitl':>4}  po_number"
    )
    print("─" * 100)
    for r in results:
        if r["error"]:
            print(f"{r['email_id']:<14} ERROR  {r['error']}")
            continue
        print(
            f"{r['email_id']:<14} "
            f"{(r['email_type'] or '-'):<10} "
            f"{(r['project'] or '-'):<14} "
            f"{r['n_lines']:>5} "
            f"{r['n_reconciled']:>5} "
            f"{r['n_hitl']:>4}  "
            f"{r['po_number'] or '-'}"
        )
    print("─" * 100)
    for r in results:
        if r["error"] or not r["summary_text"]:
            continue
        print(f"\n[{r['email_id']}] {r['summary_text']}")


async def main(argv: list[str]) -> None:
    email_ids = argv[1:] or _discover_email_ids()
    if not email_ids:
        print(f"No emails found in {EMAILS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Running pipeline against {len(email_ids)} email(s): {email_ids}\n")

    runner = InMemoryRunner(
        agent=root_agent,
        app_name="bom_pipeline_bench",
        plugins=[trace_plugin, state_plugin, tool_events, cost_guard],
    )

    results: list[dict] = []
    for email_id in email_ids:
        print(f"━━━ {email_id} ━━━")
        result = await _run_one(runner, email_id)
        results.append(result)

    _print_summary(results)


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
