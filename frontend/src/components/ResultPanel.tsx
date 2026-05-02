"use client";

import { AlertTriangle, CheckCircle2, FileText, Copy, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  RunResult,
  POLineItem,
  ReconciledLine,
  HitlReason,
} from "@/lib/types";

const HITL_REASON_LABEL: Record<HitlReason, string> = {
  low_confidence_match: "Low-confidence SAP match",
  no_acceptable_match: "No acceptable SAP match",
  special_handling_note: "Margin note requires review",
};

export function ResultPanel({ result }: { result: RunResult }) {
  if (result.kind === "po") {
    return <PoView result={result} />;
  }
  if (result.kind === "review") {
    return <ReviewView result={result} />;
  }
  return <DuplicateView summary={result.summary} />;
}

// ── PO view ─────────────────────────────────────────────────────────────

function PoView({
  result,
}: {
  result: Extract<RunResult, { kind: "po" }>;
}) {
  const { po, summary } = result;
  return (
    <section className="rounded-lg border border-emerald-200 bg-white shadow-sm overflow-hidden">
      <header className="px-4 py-3 bg-emerald-50 border-b border-emerald-200 flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-emerald-700" />
        <h3 className="text-sm font-semibold text-emerald-900">
          Draft Purchase Order
        </h3>
        <span className="ml-auto text-[10px] font-mono text-emerald-700">
          {po.po_number}
        </span>
      </header>
      <p className="px-4 py-3 text-sm text-celo-text-primary border-b border-zinc-100 bg-emerald-50/40">
        {summary}
      </p>
      <table className="w-full text-sm">
        <thead className="text-xs text-celo-text-secondary bg-zinc-50">
          <tr>
            <th className="text-left font-medium px-4 py-2">Line</th>
            <th className="text-left font-medium px-4 py-2">SAP code</th>
            <th className="text-left font-medium px-4 py-2">Description</th>
            <th className="text-right font-medium px-4 py-2">Qty</th>
            <th className="text-right font-medium px-4 py-2">UoM</th>
            <th className="text-right font-medium px-4 py-2">Conf.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {po.line_items.map((li) => (
            <PoRow key={li.line_ref} li={li} />
          ))}
        </tbody>
      </table>
      <footer className="px-4 py-3 bg-zinc-50 border-t border-zinc-100 text-xs text-celo-text-secondary flex items-center gap-2">
        <FileText className="h-3 w-3" />
        Status: <span className="font-mono">{po.status}</span>
        <span className="ml-auto text-celo-text-light">
          generated {new Date(po.generated_at).toLocaleString()}
        </span>
      </footer>
    </section>
  );
}

function PoRow({ li }: { li: POLineItem }) {
  return (
    <tr>
      <td className="px-4 py-2 font-mono text-xs">{li.line_ref}</td>
      <td className="px-4 py-2 font-mono text-xs">
        <span className="px-1.5 py-0.5 bg-zinc-100 rounded">{li.sap_code}</span>
      </td>
      <td className="px-4 py-2 text-celo-text-primary">{li.description}</td>
      <td className="px-4 py-2 text-right font-mono">{li.quantity}</td>
      <td className="px-4 py-2 text-right font-mono text-xs text-celo-text-secondary">
        {li.uom}
      </td>
      <td className="px-4 py-2 text-right font-mono text-xs">
        <ConfidencePill score={li.confidence} />
      </td>
    </tr>
  );
}

function ConfidencePill({ score }: { score: number }) {
  const color =
    score >= 0.85
      ? "bg-emerald-100 text-emerald-800"
      : score >= 0.6
        ? "bg-amber-100 text-amber-800"
        : "bg-red-100 text-red-800";
  return (
    <span className={cn("px-1.5 py-0.5 rounded", color)}>
      {(score * 100).toFixed(0)}%
    </span>
  );
}

// ── Review view ─────────────────────────────────────────────────────────

function ReviewView({
  result,
}: {
  result: Extract<RunResult, { kind: "review" }>;
}) {
  const { review, summary } = result;
  const hitlIds = new Set(review.hitl_queue.map((h) => h.line_ref));
  return (
    <section className="rounded-lg border border-amber-300 bg-white shadow-sm overflow-hidden">
      <header className="px-4 py-3 bg-amber-50 border-b border-amber-200 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-700" />
        <h3 className="text-sm font-semibold text-amber-900">
          Human Review Required — {review.project} ({review.bom_revision})
        </h3>
      </header>
      <p className="px-4 py-3 text-sm text-celo-text-primary border-b border-zinc-100 bg-amber-50/40">
        {summary}
      </p>

      {/* HITL queue first — it's the call to action */}
      <div className="px-4 py-3 border-b border-zinc-100">
        <h4 className="text-xs font-semibold tracking-wide text-celo-text-secondary uppercase mb-2 flex items-center gap-1.5">
          <Filter className="h-3 w-3" />
          HITL queue · {review.hitl_queue.length} item
          {review.hitl_queue.length === 1 ? "" : "s"}
        </h4>
        <ul className="space-y-1.5">
          {review.hitl_queue.map((item) => (
            <li
              key={item.line_ref}
              className="flex items-center gap-2 text-sm bg-amber-50 border border-amber-200 rounded px-3 py-2"
            >
              <span className="font-mono text-xs text-amber-900">
                {item.line_ref}
              </span>
              <span className="text-celo-text-primary">
                {HITL_REASON_LABEL[item.reason] ?? item.reason}
              </span>
              <button
                disabled
                className="ml-auto text-[10px] font-mono px-2 py-1 rounded bg-amber-200 text-amber-900 disabled:opacity-50"
                title="Wired to your procurement console in production"
              >
                APPROVE
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Full reconciliation table for context */}
      <h4 className="text-xs font-semibold tracking-wide text-celo-text-secondary uppercase px-4 pt-3 pb-2">
        Reconciliation
      </h4>
      <table className="w-full text-sm">
        <thead className="text-xs text-celo-text-secondary bg-zinc-50">
          <tr>
            <th className="text-left font-medium px-4 py-2">Line</th>
            <th className="text-left font-medium px-4 py-2">SAP code</th>
            <th className="text-left font-medium px-4 py-2">Description</th>
            <th className="text-right font-medium px-4 py-2">Qty</th>
            <th className="text-right font-medium px-4 py-2">Conf.</th>
            <th className="text-left font-medium px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {review.reconciliation.reconciled_lines.map((rl) => (
            <ReconRow key={rl.line_ref} rl={rl} flagged={hitlIds.has(rl.line_ref)} />
          ))}
        </tbody>
      </table>
      <footer className="px-4 py-3 bg-zinc-50 border-t border-zinc-100 text-xs text-celo-text-secondary leading-relaxed">
        <strong className="text-celo-text-primary">Next:</strong> {review.next_action}
      </footer>
    </section>
  );
}

function ReconRow({
  rl,
  flagged,
}: {
  rl: ReconciledLine;
  flagged: boolean;
}) {
  return (
    <tr className={cn(flagged && "bg-amber-50/40")}>
      <td className="px-4 py-2 font-mono text-xs">{rl.line_ref}</td>
      <td className="px-4 py-2 font-mono text-xs">
        {rl.sap_code ? (
          <span className="px-1.5 py-0.5 bg-zinc-100 rounded">{rl.sap_code}</span>
        ) : (
          <span className="text-red-600">none</span>
        )}
      </td>
      <td className="px-4 py-2 text-celo-text-primary">
        {rl.matched_description ?? <em className="text-celo-text-light">(no match)</em>}
      </td>
      <td className="px-4 py-2 text-right font-mono">
        {rl.quantity} <span className="text-celo-text-light">{rl.uom}</span>
      </td>
      <td className="px-4 py-2 text-right font-mono text-xs">
        <ConfidencePill score={rl.confidence} />
      </td>
      <td className="px-4 py-2 text-xs">
        {rl.status === "auto_approved" ? (
          <span className="text-emerald-700">auto</span>
        ) : (
          <span className="text-amber-700 font-medium">HITL</span>
        )}
      </td>
    </tr>
  );
}

// ── Duplicate view ──────────────────────────────────────────────────────

function DuplicateView({ summary }: { summary: string }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white shadow-sm p-6 text-center">
      <Copy className="h-8 w-8 text-celo-text-light mx-auto mb-3" />
      <h3 className="text-sm font-semibold text-celo-text-primary">
        Duplicate detected — no PO drafted
      </h3>
      <p className="mt-2 text-sm text-celo-text-secondary leading-relaxed max-w-md mx-auto">
        {summary}
      </p>
    </section>
  );
}
