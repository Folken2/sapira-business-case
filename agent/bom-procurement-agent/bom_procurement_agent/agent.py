"""bom-procurement-agent — Aceros Ibéricos pilot pipeline.

Architecture (top-down):

    SequentialAgent("bom_pipeline")
      ├── LoopAgent("extract_validate_loop", max_iterations=3)
      │     ├── LlmAgent("extractor")     output_key="extraction"
      │     └── LlmAgent("validator")     (calls exit_validation_loop OR
      │                                    request_extraction_revision)
      ├── LlmAgent("reconciler")          output_key="reconciliation"
      └── LlmAgent("po_creator")          output_key="po_summary"

State flow:
  load_email → current_email → extraction → (loop: extractor refines using
  validation_feedback until validator escalates) → reconciliation
  → draft_purchase_order + hitl_queue + po_summary
"""

from __future__ import annotations

from dotenv import load_dotenv
from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent

from .callbacks.validation import validate_agent_output, validate_tool_args
from .config.llm import FAST_MODEL, REASONING_MODEL
from .config.seed import seed_volume_if_empty
from .models import CreatePurchaseOrderArgs, Extraction, Reconciliation
from .prompt.sub_agents import (
    EXTRACTOR_INSTRUCTION,
    PO_CREATOR_INSTRUCTION,
    RECONCILER_INSTRUCTION,
    VALIDATOR_INSTRUCTION,
)
from .tools.bom_tools import (
    create_purchase_order_tool,
    exit_validation_loop_tool,
    flag_for_hitl_tool,
    load_email_tool,
    request_extraction_revision_tool,
    search_sap_tool,
)

load_dotenv()
seed_volume_if_empty()


# ─── Loop sub-agents (extract → validate, up to 3 attempts) ─────────────────

extractor = LlmAgent(
    model=REASONING_MODEL,
    name="extractor",
    description=(
        "Classifies the email (NEW_BOM/REVISION/DUPLICATE) and extracts structured "
        "BOM data. On loop iterations >1, refines based on validator feedback."
    ),
    instruction=EXTRACTOR_INSTRUCTION,
    tools=[load_email_tool],
    output_key="extraction",
    after_agent_callback=validate_agent_output(Extraction, "extraction"),
)

validator = LlmAgent(
    model=FAST_MODEL,
    name="validator",
    description=(
        "Verifies the extraction. Calls exit_validation_loop when clean, or "
        "request_extraction_revision with concrete feedback otherwise."
    ),
    instruction=VALIDATOR_INSTRUCTION,
    tools=[exit_validation_loop_tool, request_extraction_revision_tool],
)

extract_validate_loop = LoopAgent(
    name="extract_validate_loop",
    description="Extracts and validates the BOM, retrying up to 3 times with feedback.",
    sub_agents=[extractor, validator],
    max_iterations=3,
)


# ─── Post-loop pipeline steps ───────────────────────────────────────────────

reconciler = LlmAgent(
    model=REASONING_MODEL,
    name="reconciler",
    description="Matches each BOM line to a SAP material code; routes low-confidence lines to HITL.",
    instruction=RECONCILER_INSTRUCTION,
    tools=[search_sap_tool, flag_for_hitl_tool],
    output_key="reconciliation",
    after_agent_callback=validate_agent_output(Reconciliation, "reconciliation"),
)

po_creator = LlmAgent(
    model=FAST_MODEL,
    name="po_creator",
    description="Creates the draft Purchase Order from the reconciled lines.",
    instruction=PO_CREATOR_INSTRUCTION,
    tools=[create_purchase_order_tool],
    output_key="po_summary",
    before_tool_callback=validate_tool_args(
        CreatePurchaseOrderArgs, "create_purchase_order"
    ),
)


# ─── Pipeline (root) ─────────────────────────────────────────────────────────

root_agent = SequentialAgent(
    name="bom_pipeline",
    description=(
        "Multi-agent BOM ingestion pipeline for Aceros Ibéricos: "
        "extracts purchase specs from emails (validated in a 3-attempt loop), "
        "reconciles to SAP material codes, and drafts purchase orders."
    ),
    sub_agents=[extract_validate_loop, reconciler, po_creator],
)
