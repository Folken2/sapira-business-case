"""Domain tools for the BOM procurement pipeline.

Mock implementations for the Aceros Ibéricos pilot demo. SAP master data is a
JSON file; emails are pre-seeded JSON; the "purchase order" is written to
session state so a downstream UI can render the draft for HITL review.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SAP_PATH = _DATA_DIR / "sap_material_master.json"
_EMAILS_DIR = _DATA_DIR / "sample_emails"
_OUTPUT_DIR = Path(
    os.getenv("PO_OUTPUT_DIR")
    or Path(__file__).resolve().parent.parent.parent / "output"
)


def _load_sap_master() -> list[dict[str, Any]]:
    return json.loads(_SAP_PATH.read_text(encoding="utf-8"))["materials"]


def load_email(email_id: str, tool_context: ToolContext) -> dict:
    """Load a raw incoming BOM email by id from the shared inbox.

    Args:
        email_id: Identifier of the email to load (e.g. "email_001").

    Returns:
        Dict with status and the full email payload (headers, body, attachments).
    """
    path = _EMAILS_DIR / f"{email_id}.json"
    if not path.is_file():
        # Fallback: search by prefix so the LLM can pass partial ids.
        matches = list(_EMAILS_DIR.glob(f"{email_id}*.json"))
        if not matches:
            return {"status": "error", "error": f"Email not found: {email_id}"}
        path = matches[0]
    payload = json.loads(path.read_text(encoding="utf-8"))
    tool_context.state["current_email"] = payload
    return {"status": "success", "data": payload}


def search_sap_material_master(
    query: str,
    grade: str = "",
    form: str = "",
    thickness_mm: float = 0.0,
    top_k: int = 5,
    tool_context: ToolContext | None = None,
) -> dict:
    """Search the SAP material master for candidate matches.

    Combines lexical similarity on the description with optional structured
    filters (grade, form, thickness). Returns the top_k candidates with a
    confidence score in [0, 1] so the caller can decide auto-approve vs HITL.

    Args:
        query: Free-text description from the BOM line (e.g. "galvanized B 3mm sheet").
        grade: Optional steel grade to filter on (e.g. "S355J2"). Empty = no filter.
        form: Optional form factor (sheet, plate, coil, tube, rebar, wire, flat_bar).
        thickness_mm: Optional thickness in mm (0.0 = no filter). Tolerates ±0.2mm.
        top_k: Maximum number of candidates to return.

    Returns:
        Dict with status and a list of candidates ranked by confidence score.
    """
    materials = _load_sap_master()
    q_norm = query.lower().strip()

    candidates: list[dict[str, Any]] = []
    for m in materials:
        if grade and grade.lower() not in m["grade"].lower():
            continue
        if form and form.lower() != m["form"].lower():
            continue
        if thickness_mm > 0 and abs(m["thickness_mm"] - thickness_mm) > 0.2:
            continue

        lex = SequenceMatcher(None, q_norm, m["description"].lower()).ratio()
        token_overlap = len(set(q_norm.split()) & set(m["description"].lower().split()))
        score = round(min(1.0, lex + 0.05 * token_overlap), 3)
        candidates.append({**m, "confidence": score})

    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    return {"status": "success", "data": {"candidates": candidates[:top_k]}}


def flag_for_hitl(reason: str, line_ref: str, tool_context: ToolContext) -> dict:
    """Route a BOM line to the human-in-the-loop review queue.

    Use when confidence is below the auto-approve threshold (0.85), when a
    margin note adds non-standard requirements, or when no candidate match
    exists in the SAP master. Routing to HITL is ALWAYS preferred over a
    confident-but-wrong auto-approval.

    Args:
        reason: One of: "low_confidence_match", "no_acceptable_match",
            "special_handling_note".
        line_ref: BOM line identifier (e.g. "LINE 2", "LINE 4").

    Returns:
        Dict confirming the HITL routing.
    """
    queue = tool_context.state.setdefault("hitl_queue", [])
    queue.append({"line_ref": line_ref, "reason": reason})
    return {"status": "success", "message": f"{line_ref} routed to HITL: {reason}"}


def exit_validation_loop(tool_context: ToolContext) -> dict:
    """Signal the validation LoopAgent to stop — extraction is correct.

    Call this only when every BOM line is well-formed, complete, and free of
    contradictions. If anything is uncertain, do NOT call this; call
    request_extraction_revision instead and let the extractor try again.

    Returns:
        Dict confirming loop exit.
    """
    tool_context.actions.escalate = True
    return {"status": "success", "message": "Validation passed — exiting loop."}


def request_extraction_revision(feedback: str, tool_context: ToolContext) -> dict:
    """Send specific feedback back to the extractor for the next loop iteration.

    Use when the extraction has issues that the extractor should fix on its
    next attempt. Be concrete — name the line_ref and the exact problem so
    the extractor knows what to change.

    Args:
        feedback: Specific, actionable feedback (e.g. "LINE 2 missing uom; the
            email body says 'qty 45 TON' — set uom='TON'.").

    Returns:
        Dict confirming the feedback was queued for the next iteration.
    """
    tool_context.state["validation_feedback"] = feedback
    return {"status": "revision_requested", "feedback": feedback}


def create_purchase_order(
    project: str,
    bom_revision: str,
    line_items: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict:
    """Create the draft Purchase Order in SAP (mocked: writes to session state).

    The PO is a DRAFT — never auto-submitted. Lines below the auto-approve
    confidence threshold remain pending HITL approval and must not be sent to
    the supplier until reviewed.

    Args:
        project: Project name (e.g. "HARBOUR-7").
        bom_revision: BOM revision tag (e.g. "v1", "v2").
        line_items: List of dicts, each with keys: line_ref, sap_code,
            description, quantity, uom, confidence, status (auto_approved|hitl_pending).

    Returns:
        Dict with the draft PO payload that would be POSTed to SAP.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    po_number = f"DRAFT-{project}-{bom_revision}-{timestamp}"
    po = {
        "po_number": po_number,
        "project": project,
        "bom_revision": bom_revision,
        "line_items": line_items,
        "status": "draft_pending_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    tool_context.state["draft_purchase_order"] = json.dumps(po, indent=2)

    auto_count = sum(1 for li in line_items if li.get("status") == "auto_approved")
    hitl_count = len(line_items) - auto_count

    # Persist the full pipeline result to disk so the user can inspect it.
    artifact = {
        "purchase_order": po,
        "hitl_queue": tool_context.state.get("hitl_queue", []),
        "summary": {
            "total_lines": len(line_items),
            "auto_approved": auto_count,
            "hitl_pending": hitl_count,
        },
    }
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = _OUTPUT_DIR / f"{po_number}.json"
    artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "data": po,
        "artifact_path": str(artifact_path),
        "message": (
            f"Draft PO {po_number} created: {auto_count}/{len(line_items)} lines "
            f"auto-approved, {hitl_count} pending HITL. Artifact written to {artifact_path}."
        ),
    }


# Tool instances exposed to the agents
load_email_tool = FunctionTool(func=load_email)
search_sap_tool = FunctionTool(func=search_sap_material_master)
flag_for_hitl_tool = FunctionTool(func=flag_for_hitl)
exit_validation_loop_tool = FunctionTool(func=exit_validation_loop)
request_extraction_revision_tool = FunctionTool(func=request_extraction_revision)
create_purchase_order_tool = FunctionTool(func=create_purchase_order)
