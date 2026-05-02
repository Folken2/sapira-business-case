"""StatePlugin — captures full session-state evolution across the BOM pipeline.

Plugin-level callbacks fire for EVERY agent in the run (including each
LoopAgent iteration of `extractor` and `validator`), so we get a true
chronological trace without per-agent wiring. The final trace is written
to `output/trace-<timestamp>.json` when the root agent completes.

Each step record contains:
  - step_index            (monotonic, across the whole invocation)
  - agent_name
  - phase                 ("before" | "after")
  - timestamp_iso
  - state_snapshot        (only the BOM-relevant keys, deep-copied + JSON-safe)

Designed for demo/inspection — not optimised for high-frequency production use.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)

# Only snapshot keys produced/consumed by the BOM pipeline — keeps the trace
# focused and avoids dumping unrelated session state.
_TRACKED_KEYS = (
    "current_email",
    "extraction",
    "validation_feedback",
    "reconciliation",
    "hitl_queue",
    "draft_purchase_order",
    "po_summary",
)

_OUTPUT_DIR = Path(
    os.getenv("PO_OUTPUT_DIR")
    or Path(__file__).resolve().parent.parent.parent / "output"
)


def _json_safe(value: Any) -> Any:
    """Best-effort copy that round-trips through JSON."""
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return str(value)


class StatePlugin(BasePlugin):
    """Captures per-agent state snapshots and writes a trace file at end of run."""

    def __init__(self, root_agent_name: str = "bom_pipeline") -> None:
        super().__init__(name="state")
        self._root_agent_name = root_agent_name
        # Keyed by invocation_id so concurrent invocations don't collide.
        self._steps: dict[str, list[dict[str, Any]]] = {}

    def _record(
        self,
        callback_context: CallbackContext,
        agent: BaseAgent,
        phase: str,
    ) -> None:
        invocation_id = (
            callback_context._invocation_context.invocation_id  # type: ignore[attr-defined]
        )
        steps = self._steps.setdefault(invocation_id, [])
        snapshot: dict[str, Any] = {}
        for key in _TRACKED_KEYS:
            if key in callback_context.state:
                snapshot[key] = _json_safe(
                    copy.deepcopy(callback_context.state[key])
                )
        steps.append(
            {
                "step_index": len(steps),
                "agent_name": agent.name,
                "phase": phase,
                "timestamp_iso": datetime.now(timezone.utc).isoformat(),
                "state_snapshot": snapshot,
            }
        )

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._record(callback_context, agent, "before")
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._record(callback_context, agent, "after")

        # When the root agent finishes, flush the trace to disk.
        if agent.name == self._root_agent_name:
            invocation_id = (
                callback_context._invocation_context.invocation_id  # type: ignore[attr-defined]
            )
            steps = self._steps.pop(invocation_id, [])
            if not steps:
                return None

            _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            path = _OUTPUT_DIR / f"trace-{timestamp}.json"
            payload = {
                "invocation_id": invocation_id,
                "root_agent": self._root_agent_name,
                "step_count": len(steps),
                "steps": steps,
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.warning("[state] wrote %d steps to %s", len(steps), path)
        return None
