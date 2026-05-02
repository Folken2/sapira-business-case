"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  CircleSlash,
  Loader2,
  Wrench,
} from "lucide-react";
import { cn, formatMs } from "@/lib/utils";
import type { Step, AgentName } from "@/lib/types";

const AGENT_LABEL: Record<AgentName, string> = {
  extractor: "Extractor",
  validator: "Validator",
  reconciler: "SAP Reconciler",
  po_creator: "PO Creator",
  hitl_gate: "HITL Gate",
};

const AGENT_COLOR: Record<AgentName, string> = {
  extractor: "bg-blue-50 text-blue-800 border-blue-200",
  validator: "bg-violet-50 text-violet-800 border-violet-200",
  reconciler: "bg-cyan-50 text-cyan-800 border-cyan-200",
  po_creator: "bg-emerald-50 text-emerald-800 border-emerald-200",
  hitl_gate: "bg-amber-50 text-amber-800 border-amber-200",
};

type Props = {
  steps: Step[];
  /** ms between auto-advancing steps; null = render all at once */
  autoplayDelayMs?: number | null;
  /** key that resets playback when it changes (e.g. selected email id) */
  playbackKey?: string;
};

export function PipelineSteps({
  steps,
  autoplayDelayMs = 600,
  playbackKey,
}: Props) {
  const [revealed, setRevealed] = useState(
    autoplayDelayMs === null ? steps.length : 0
  );

  useEffect(() => {
    if (autoplayDelayMs === null) {
      setRevealed(steps.length);
      return;
    }
    setRevealed(0);
    let cancelled = false;
    let i = 0;
    const tick = () => {
      if (cancelled) return;
      i += 1;
      setRevealed(i);
      if (i < steps.length) {
        setTimeout(tick, autoplayDelayMs);
      }
    };
    const t0 = setTimeout(tick, autoplayDelayMs);
    return () => {
      cancelled = true;
      clearTimeout(t0);
    };
  }, [steps, autoplayDelayMs, playbackKey]);

  return (
    <ol className="relative space-y-3">
      {steps.map((step, i) => {
        const visible = i < revealed;
        const inProgress = i === revealed - 1 && autoplayDelayMs !== null;
        return (
          <li
            key={step.index}
            className={cn(
              "transition-all duration-300",
              visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
            )}
          >
            <StepCard step={step} pulse={inProgress} />
          </li>
        );
      })}
      {revealed < steps.length && autoplayDelayMs !== null && (
        <li className="flex items-center gap-2 text-xs text-celo-text-secondary pt-2">
          <Loader2 className="h-3 w-3 animate-spin" />
          Pipeline running…
        </li>
      )}
    </ol>
  );
}

function StepCard({ step, pulse }: { step: Step; pulse: boolean }) {
  const Icon =
    step.status === "halted"
      ? CircleSlash
      : step.status === "errored"
        ? CircleSlash
        : CheckCircle2;
  const iconColor =
    step.status === "halted"
      ? "text-amber-600"
      : step.status === "errored"
        ? "text-red-600"
        : "text-emerald-600";

  return (
    <div
      className={cn(
        "rounded-lg border bg-white shadow-sm p-3",
        pulse && "ring-2 ring-celo-yellow/40"
      )}
    >
      <header className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4 shrink-0", iconColor)} />
        <span
          className={cn(
            "text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border",
            AGENT_COLOR[step.agent]
          )}
        >
          {AGENT_LABEL[step.agent]}
        </span>
        {step.loop_iteration && (
          <span className="text-[10px] font-mono text-celo-text-secondary">
            iter {step.loop_iteration}
          </span>
        )}
        <span className="ml-auto text-[10px] font-mono text-celo-text-light">
          {formatMs(step.duration_ms)}
        </span>
      </header>
      <p className="mt-2 text-sm text-celo-text-primary leading-snug">
        {step.summary}
      </p>
      {step.tool_calls && step.tool_calls.length > 0 && (
        <details className="mt-2 text-xs">
          <summary className="cursor-pointer flex items-center gap-1 text-celo-text-secondary hover:text-celo-text-primary">
            <Wrench className="h-3 w-3" />
            {step.tool_calls.length} tool call
            {step.tool_calls.length > 1 ? "s" : ""}
          </summary>
          <ul className="mt-1 ml-4 space-y-1 font-mono text-[11px] text-celo-text-secondary">
            {step.tool_calls.map((tc, i) => (
              <li key={i}>
                <span className="text-celo-text-primary">{tc.name}</span>
                {tc.args && Object.keys(tc.args).length > 0 && (
                  <span className="text-celo-text-light">
                    ({Object.keys(tc.args).join(", ")})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
      {step.state_out && (
        <details className="mt-1.5 text-xs">
          <summary className="cursor-pointer flex items-center gap-1 text-celo-text-secondary hover:text-celo-text-primary">
            <CircleDashed className="h-3 w-3" />
            state delta
          </summary>
          <pre className="mt-1 p-2 bg-zinc-50 rounded font-mono text-[10px] leading-relaxed overflow-x-auto border border-zinc-100">
            {JSON.stringify(step.state_out, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
