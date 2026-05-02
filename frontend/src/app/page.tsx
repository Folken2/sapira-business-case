"use client";

import { useEffect, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { EmailInbox } from "@/components/EmailInbox";
import { EmailPreview } from "@/components/EmailPreview";
import { PipelineSteps } from "@/components/PipelineSteps";
import { ResultPanel } from "@/components/ResultPanel";
import { listRuns } from "@/lib/runs";
import { formatMs } from "@/lib/utils";
import type { Run } from "@/lib/types";

const ALL_RUNS = listRuns();

export default function Home() {
  const [selectedId, setSelectedId] = useState<string | null>(
    ALL_RUNS[0]?.email.email_id ?? null
  );
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(false);
  const [revealResult, setRevealResult] = useState(false);

  // Fetch the run when selection changes
  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true);
    setRun(null);
    setRevealResult(false);
    fetch(`/api/run?email_id=${encodeURIComponent(selectedId)}`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        setRun(data as Run);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  // Reveal the result panel after the simulated step playback completes.
  useEffect(() => {
    if (!run) return;
    const totalDelay = run.steps.length * 600 + 400;
    const t = setTimeout(() => setRevealResult(true), totalDelay);
    return () => clearTimeout(t);
  }, [run]);

  return (
    <div className="h-screen grid grid-cols-[320px_minmax(0,1fr)_minmax(0,1.1fr)]">
      <EmailInbox runs={ALL_RUNS} selectedId={selectedId} onSelect={setSelectedId} />

      {/* Centre column — selected email + pipeline */}
      <main className="overflow-y-auto bg-bg-secondary px-6 py-5">
        <header className="flex items-baseline gap-3 mb-4">
          <h1 className="text-lg font-semibold tracking-tight">
            Sapira BOM Pipeline
          </h1>
          <span className="text-xs text-celo-text-secondary">
            Aceros Ibéricos · 8-week pilot
          </span>
        </header>

        {!run && loading && <SkeletonBlock label="Loading run…" />}

        {run && (
          <>
            <SectionTitle index={1} label="Incoming email" />
            <EmailPreview email={run.email} />

            <SectionTitle
              index={2}
              label="Pipeline trace"
              right={
                <button
                  onClick={() => {
                    // Force a remount of PipelineSteps via state reset
                    setRun(null);
                    setRevealResult(false);
                    setTimeout(() => {
                      fetch(`/api/run?email_id=${encodeURIComponent(selectedId!)}`)
                        .then((r) => r.json())
                        .then(setRun);
                    }, 50);
                  }}
                  className="flex items-center gap-1 text-xs text-celo-text-secondary hover:text-celo-text-primary"
                >
                  <RotateCcw className="h-3 w-3" />
                  Replay
                </button>
              }
            />
            <PipelineSteps
              steps={run.steps}
              autoplayDelayMs={600}
              playbackKey={selectedId ?? undefined}
            />
            <p className="mt-3 text-xs text-celo-text-secondary flex items-center gap-2">
              <Play className="h-3 w-3" />
              total wall time:{" "}
              <span className="font-mono">{formatMs(run.total_duration_ms)}</span>
            </p>
          </>
        )}
      </main>

      {/* Right column — result */}
      <aside className="overflow-y-auto border-l border-zinc-200 bg-white px-6 py-5">
        <SectionTitle index={3} label="Outcome" />
        {!run && <SkeletonBlock label="Awaiting run…" />}
        {run && !revealResult && (
          <SkeletonBlock label="Pipeline running — outcome pending…" />
        )}
        {run && revealResult && <ResultPanel result={run.result} />}
      </aside>
    </div>
  );
}

function SectionTitle({
  index,
  label,
  right,
}: {
  index: number;
  label: string;
  right?: React.ReactNode;
}) {
  return (
    <h2 className="flex items-center gap-2 text-xs font-semibold tracking-wide text-celo-text-secondary uppercase mt-5 mb-2">
      <span className="bg-celo-yellow text-celo-text-primary text-[10px] font-mono w-5 h-5 inline-flex items-center justify-center rounded-full">
        {index}
      </span>
      <span>{label}</span>
      {right && <span className="ml-auto">{right}</span>}
    </h2>
  );
}

function SkeletonBlock({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-200 bg-white py-12 text-center text-sm text-celo-text-light">
      {label}
    </div>
  );
}
