// Mirror of the Pydantic models in the Python agent.
// Keep in sync with bom_procurement_agent/models.py.

export type EmailType = "NEW_BOM" | "REVISION" | "DUPLICATE";
export type Form = "sheet" | "plate" | "coil" | "tube" | "rebar" | "wire" | "flat_bar";
export type UoM = "TON" | "KG" | "M";
export type LineStatus = "auto_approved" | "hitl_pending";
export type HitlReason =
  | "low_confidence_match"
  | "no_acceptable_match"
  | "special_handling_note";

export type LineItem = {
  line_ref: string;
  raw_description: string;
  grade: string;
  form: Form | null;
  thickness_mm: number | null;
  quantity: number;
  uom: UoM | null;
  notes: string;
};

export type Extraction = {
  email_type: EmailType;
  project: string;
  bom_revision: string;
  line_items: LineItem[];
  global_notes: string;
};

export type ReconciledLine = {
  line_ref: string;
  raw_description: string;
  sap_code: string | null;
  matched_description: string | null;
  quantity: number;
  uom: UoM;
  confidence: number;
  status: LineStatus;
  hitl_reason: HitlReason | null;
};

export type Reconciliation = {
  project: string;
  bom_revision: string;
  reconciled_lines: ReconciledLine[];
};

export type POLineItem = {
  line_ref: string;
  sap_code: string | null;
  description: string;
  quantity: number;
  uom: UoM;
  confidence: number;
  status: LineStatus;
};

export type PurchaseOrder = {
  po_number: string;
  project: string;
  bom_revision: string;
  line_items: POLineItem[];
  status: string;
  generated_at: string;
};

export type ReviewArtifact = {
  status: "pending_human_review";
  project: string;
  bom_revision: string;
  generated_at: string;
  reason: string;
  hitl_queue: { line_ref: string; reason: HitlReason }[];
  reconciliation: Reconciliation;
  next_action: string;
};

// ── Pipeline-trace view model ──────────────────────────────────────────

export type AgentName =
  | "extractor"
  | "validator"
  | "reconciler"
  | "po_creator"
  | "hitl_gate";

export type ToolCall = {
  name: string;
  args?: Record<string, unknown>;
  result?: unknown;
};

export type StepStatus = "completed" | "halted" | "errored";

export type Step = {
  index: number;
  agent: AgentName;
  loop_iteration?: number;
  status: StepStatus;
  duration_ms: number;
  summary: string;
  state_in?: Record<string, unknown>;
  state_out?: Record<string, unknown>;
  tool_calls?: ToolCall[];
};

// ── Email + Run wrapper ────────────────────────────────────────────────

export type IncomingEmail = {
  email_id: string;
  received_at: string;
  from: string;
  to?: string;
  cc?: string;
  subject: string;
  body: string;
  attachments?: { filename: string; type: string; content: string }[];
};

export type RunResult =
  | { kind: "po"; po: PurchaseOrder; summary: string }
  | { kind: "review"; review: ReviewArtifact; summary: string }
  | { kind: "duplicate"; summary: string };

export type Run = {
  email: IncomingEmail;
  steps: Step[];
  total_duration_ms: number;
  result: RunResult;
};
