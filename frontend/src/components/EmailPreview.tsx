"use client";

import { Paperclip } from "lucide-react";
import type { IncomingEmail } from "@/lib/types";

export function EmailPreview({ email }: { email: IncomingEmail }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 text-sm">
      <div className="grid grid-cols-[80px_1fr] gap-y-1 text-xs text-celo-text-secondary mb-3">
        <span>From:</span>
        <span className="text-celo-text-primary">{email.from}</span>
        {email.to && (
          <>
            <span>To:</span>
            <span className="text-celo-text-primary">{email.to}</span>
          </>
        )}
        {email.cc && (
          <>
            <span>Cc:</span>
            <span className="text-celo-text-primary">{email.cc}</span>
          </>
        )}
        <span>Subject:</span>
        <span className="font-medium text-celo-text-primary">{email.subject}</span>
      </div>
      <pre className="whitespace-pre-wrap font-sans text-celo-text-primary leading-relaxed">
        {email.body}
      </pre>
      {email.attachments && email.attachments.length > 0 && (
        <div className="mt-4 pt-3 border-t border-zinc-100">
          {email.attachments.map((att) => (
            <details key={att.filename} className="text-xs">
              <summary className="cursor-pointer flex items-center gap-1.5 text-celo-text-secondary hover:text-celo-text-primary">
                <Paperclip className="h-3 w-3" />
                <span className="font-mono">{att.filename}</span>
                <span className="text-celo-text-light">({att.type})</span>
              </summary>
              <pre className="mt-2 p-3 bg-zinc-50 rounded font-mono text-[11px] whitespace-pre-wrap leading-relaxed border border-zinc-100">
                {att.content}
              </pre>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
