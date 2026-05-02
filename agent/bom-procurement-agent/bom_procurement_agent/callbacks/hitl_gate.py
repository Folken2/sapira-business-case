"""HITL gate — prevents the PO creator from running when any reconciled line
needs human review.

Wired as a `before_agent_callback` on the `po_creator` agent. If
`state["hitl_queue"]` is non-empty (set by `flag_for_hitl` during
reconciliation), this callback:

  1. Writes a `REVIEW-<project>-<ts>.json` artifact under output/ containing
     the reconciliation, the HITL queue, and a one-line reason per item.
  2. Returns Content to short-circuit the agent — no LLM call burned, no PO
     drafted. The pipeline finishes cleanly with a human-readable message.

If the HITL queue is empty, returns None and the PO creator proceeds normally.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path(
    os.getenv("PO_OUTPUT_DIR")
    or Path(__file__).resolve().parent.parent.parent / "output"
)


def _safe_parse(value):
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def hitl_gate(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """before_agent_callback for po_creator. Halts when HITL queue is non-empty."""
    state = callback_context.state
    hitl_queue = state.get("hitl_queue") or []

    if not hitl_queue:
        # Clear path — let the PO creator run.
        return None

    reconciliation = _safe_parse(state.get("reconciliation")) or {}
    project = reconciliation.get("project", "UNKNOWN")
    bom_revision = reconciliation.get("bom_revision", "v?")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    review_path = _OUTPUT_DIR / f"REVIEW-{project}-{bom_revision}-{timestamp}.json"

    review_payload = {
        "status": "pending_human_review",
        "project": project,
        "bom_revision": bom_revision,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reason": (
            f"{len(hitl_queue)} line(s) require human verification before a "
            "Purchase Order can be drafted."
        ),
        "hitl_queue": hitl_queue,
        "reconciliation": reconciliation,
        "next_action": (
            "Review each flagged line in your procurement console. After "
            "approval, re-trigger the pipeline with `approve_hitl: true` "
            "(or call create_purchase_order directly with the corrected "
            "line_items)."
        ),
    }
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review_payload, indent=2), encoding="utf-8")

    # Save the path on state so downstream tooling / UI can find it.
    state["review_artifact_path"] = str(review_path)

    logger.warning(
        "[hitl_gate] PO drafting halted — %d line(s) need review. Artifact: %s",
        len(hitl_queue),
        review_path,
    )

    bullet_lines = "\n".join(
        f"  • {item.get('line_ref', '?')}: {item.get('reason', 'no reason')}"
        for item in hitl_queue
    )
    summary = (
        f"PO drafting halted for project {project} (BOM {bom_revision}).\n\n"
        f"{len(hitl_queue)} line(s) require human verification before a "
        f"Purchase Order can be drafted:\n\n{bullet_lines}\n\n"
        f"Review payload written to: {review_path}\n\n"
        f"Once a human reviewer approves the flagged lines, re-run this "
        f"pipeline (or invoke create_purchase_order directly) with the "
        f"corrected line_items."
    )

    return types.Content(role="model", parts=[types.Part(text=summary)])
