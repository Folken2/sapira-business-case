"""Pydantic models — single source of truth for the BOM pipeline data shapes.

Used in three places:
  1. Prompts            — schemas rendered into instruction text via .json_schema()
  2. Tool bodies        — Model.model_validate(payload) to validate dict args
  3. Runtime parsing    — after_agent_callback parses LLM output into typed objects
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat


class EmailType(str, Enum):
    NEW_BOM = "NEW_BOM"
    REVISION = "REVISION"
    DUPLICATE = "DUPLICATE"


class Form(str, Enum):
    SHEET = "sheet"
    PLATE = "plate"
    COIL = "coil"
    TUBE = "tube"
    REBAR = "rebar"
    WIRE = "wire"
    FLAT_BAR = "flat_bar"


class UoM(str, Enum):
    TON = "TON"
    KG = "KG"
    M = "M"


class LineStatus(str, Enum):
    AUTO_APPROVED = "auto_approved"
    HITL_PENDING = "hitl_pending"


class HitlReason(str, Enum):
    LOW_CONFIDENCE_MATCH = "low_confidence_match"
    NO_ACCEPTABLE_MATCH = "no_acceptable_match"
    SPECIAL_HANDLING_NOTE = "special_handling_note"


# ─── Extraction (extractor output) ───────────────────────────────────────────


class LineItem(BaseModel):
    line_ref: str = Field(..., description="Line identifier within the BOM (e.g. 'LINE 1').")
    raw_description: str = Field(..., min_length=1, description="Verbatim text from the email.")
    grade: str = Field("", description="Steel grade; empty if not determinable.")
    form: Optional[Form] = Field(None, description="Form factor; null if not determinable.")
    thickness_mm: Optional[PositiveFloat] = Field(None, description="Thickness in mm; null for non-flat forms.")
    quantity: PositiveFloat = Field(..., description="Order quantity in the line's UoM.")
    uom: Optional[UoM] = Field(None, description="Unit of measure; required for a clean extraction.")
    notes: str = Field("", description="Margin/handwritten note attached to this line, verbatim.")


class Extraction(BaseModel):
    email_type: EmailType
    project: str = Field(..., description="Project name; empty allowed only for DUPLICATE.")
    bom_revision: str = Field(..., description="Revision tag, e.g. 'v1', 'v2'.")
    line_items: list[LineItem] = Field(default_factory=list)
    global_notes: str = Field("", description="Email-level notes not tied to a single line.")


# ─── Reconciliation (reconciler output) ─────────────────────────────────────


class ReconciledLine(BaseModel):
    line_ref: str
    raw_description: str
    sap_code: Optional[str] = Field(None, description="Best matching SAP code, or null.")
    matched_description: Optional[str] = Field(None, description="SAP master description, or null.")
    quantity: PositiveFloat
    uom: UoM
    confidence: NonNegativeFloat = Field(..., le=1.0, description="Match confidence in [0, 1].")
    status: LineStatus
    hitl_reason: Optional[HitlReason] = None


class Reconciliation(BaseModel):
    project: str
    bom_revision: str
    reconciled_lines: list[ReconciledLine] = Field(default_factory=list)


# ─── Purchase Order (po_creator tool input) ─────────────────────────────────


class POLineItem(BaseModel):
    line_ref: str
    sap_code: Optional[str]
    description: str
    quantity: PositiveFloat
    uom: UoM
    confidence: NonNegativeFloat = Field(..., le=1.0)
    status: LineStatus


class PurchaseOrder(BaseModel):
    po_number: str
    project: str
    bom_revision: str
    line_items: list[POLineItem]
    status: str = "draft_pending_review"


class CreatePurchaseOrderArgs(BaseModel):
    """Validates the args dict the LLM passes to `create_purchase_order`."""

    project: str = Field(..., min_length=1)
    bom_revision: str = Field(..., min_length=1)
    line_items: list[POLineItem] = Field(..., min_length=1)


# ─── Helpers ────────────────────────────────────────────────────────────────


def render_schema(model: type[BaseModel]) -> str:
    """Render a model's JSON Schema as a compact, prompt-friendly string."""
    import json

    return json.dumps(model.model_json_schema(), indent=2)
