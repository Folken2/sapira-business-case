"""Schema-validation callbacks for the BOM pipeline.

Two flavours, one philosophy: keep tools dumb, validate at the boundaries.

1. `validate_agent_output(model, state_key, feedback_key)` — factory that
   returns an `after_agent_callback`. Parses the agent's text output as JSON,
   validates against `model`, writes the typed dict back to state on success
   or a structured error message to `feedback_key` on failure (so a wrapping
   LoopAgent can retry with concrete feedback — no validator LLM call burned
   on structural mistakes).

2. `validate_tool_args(model, tool_name)` — factory that returns a
   `before_tool_callback`. Validates the `args` dict of a specific tool call
   against `model` before the tool runs. Returns an error dict on failure so
   the agent sees the validation error and can retry the call.

Wire either factory into the LlmAgent constructor:
    LlmAgent(
        ...,
        after_agent_callback=validate_agent_output(Extraction, "extraction"),
        before_tool_callback=validate_tool_args(PurchaseOrder, "create_purchase_order"),
    )
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _extract_json_blob(text: str) -> Optional[str]:
    """Find a JSON object in arbitrary LLM text — fenced, raw, or buried."""
    if not text:
        return None
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return None


def _format_pydantic_errors(err: ValidationError) -> str:
    lines = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"])
        lines.append(f"  - {loc}: {e['msg']} (got: {e.get('input')!r})")
    return "\n".join(lines)


# ─── after_agent_callback factory ────────────────────────────────────────────


def validate_agent_output(
    model: type[BaseModel],
    state_key: str,
    feedback_key: str = "validation_feedback",
) -> Callable[[CallbackContext], Optional[genai_types.Content]]:
    """Return an after_agent_callback that parses + validates the agent's
    text output (`state[state_key]`) against `model`.

    On success: overwrites `state[state_key]` with the validated dict and
    clears `state[feedback_key]`.
    On failure: writes a concrete error message to `state[feedback_key]` so
    the next loop iteration's agent can fix the specific issue.
    """

    schema_name = model.__name__

    def _callback(callback_context: CallbackContext) -> Optional[genai_types.Content]:
        state = callback_context.state
        raw = state.get(state_key)
        if not raw or not isinstance(raw, str):
            return None

        blob = _extract_json_blob(raw)
        if blob is None:
            state[feedback_key] = (
                f"{schema_name} output did not contain a JSON object. Return "
                f"ONLY the JSON object matching the {schema_name} schema, "
                f"optionally fenced in ```json ... ```."
            )
            return None

        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError as e:
            state[feedback_key] = (
                f"{schema_name} output is not valid JSON: {e.msg} "
                f"(line {e.lineno}, col {e.colno}). Re-emit the JSON object."
            )
            return None

        try:
            validated = model.model_validate(parsed)
        except ValidationError as e:
            state[feedback_key] = (
                f"{schema_name} failed schema validation. Fix these errors:\n"
                + _format_pydantic_errors(e)
            )
            return None

        # Store as a JSON string (not a dict) so that ADK's `str(value)` call
        # in inject_session_state produces clean JSON downstream — not Python
        # repr with single quotes.
        state[state_key] = validated.model_dump_json(indent=2)
        if feedback_key in state:
            state[feedback_key] = ""  # clear without removing the key
        logger.warning(
            "[%s] callback OK — stored validated %s in state[%r] (%d chars).",
            callback_context.agent_name if hasattr(callback_context, "agent_name") else "?",
            schema_name,
            state_key,
            len(state[state_key]),
        )
        return None

    return _callback


# ─── before_tool_callback factory ────────────────────────────────────────────


def validate_tool_args(
    model: type[BaseModel],
    tool_name: str,
) -> Callable[[BaseTool, dict[str, Any], ToolContext], Awaitable[Optional[dict]]]:
    """Return a before_tool_callback that validates `args` against `model`
    when the named tool is about to be called. Returning a dict short-circuits
    the actual tool call; returning None lets it proceed."""

    schema_name = model.__name__

    async def _callback(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> Optional[dict]:
        if tool.name != tool_name:
            return None
        try:
            model.model_validate(args)
        except ValidationError as e:
            logger.warning("%s args failed validation: %s", tool_name, e)
            return {
                "status": "error",
                "error": (
                    f"Arguments to {tool_name} failed {schema_name} validation. "
                    f"Fix these errors and retry:\n{_format_pydantic_errors(e)}"
                ),
            }
        return None

    return _callback
