"use client";

import { Mail, Inbox } from "lucide-react";
import { cn, formatRelative } from "@/lib/utils";
import type { Run } from "@/lib/types";

type Props = {
  runs: Run[];
  selectedId: string | null;
  onSelect: (emailId: string) => void;
};

const KIND_BADGE: Record<string, { label: string; className: string }> = {
  po: { label: "→ DRAFT PO", className: "bg-emerald-100 text-emerald-800" },
  review: { label: "→ HITL REVIEW", className: "bg-amber-100 text-amber-800" },
  duplicate: { label: "→ DUPLICATE", className: "bg-zinc-200 text-zinc-700" },
};

export function EmailInbox({ runs, selectedId, onSelect }: Props) {
  return (
    <aside className="flex flex-col h-full bg-white border-r border-zinc-200">
      <header className="px-4 py-3 border-b border-zinc-200 flex items-center gap-2">
        <Inbox className="h-4 w-4 text-celo-gray" />
        <h2 className="text-sm font-semibold tracking-tight">Shared Inbox</h2>
        <span className="ml-auto text-xs text-celo-text-secondary">
          {runs.length} unread
        </span>
      </header>
      <ul className="flex-1 overflow-y-auto divide-y divide-zinc-100">
        {runs.map((run) => {
          const badge = KIND_BADGE[run.result.kind] ?? KIND_BADGE.duplicate;
          const isSelected = selectedId === run.email.email_id;
          return (
            <li key={run.email.email_id}>
              <button
                onClick={() => onSelect(run.email.email_id)}
                className={cn(
                  "w-full text-left px-4 py-3 hover:bg-zinc-50 transition-colors",
                  isSelected &&
                    "bg-celo-yellow-light hover:bg-celo-yellow-light border-l-4 border-l-celo-yellow"
                )}
              >
                <div className="flex items-center gap-2 text-xs text-celo-text-secondary">
                  <Mail className="h-3 w-3" />
                  <span className="truncate">{run.email.from}</span>
                  <span className="ml-auto whitespace-nowrap">
                    {formatRelative(run.email.received_at)}
                  </span>
                </div>
                <div className="mt-1 text-sm font-medium text-celo-text-primary line-clamp-2">
                  {run.email.subject}
                </div>
                <div className="mt-1.5 text-xs text-celo-text-secondary line-clamp-1">
                  {run.email.body.split("\n")[0]}
                </div>
                <span
                  className={cn(
                    "mt-2 inline-block text-[10px] font-mono px-1.5 py-0.5 rounded",
                    badge.className
                  )}
                >
                  {badge.label}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <footer className="px-4 py-3 border-t border-zinc-200 text-xs text-celo-text-secondary">
        Click an email to run the BOM pipeline.
      </footer>
    </aside>
  );
}
