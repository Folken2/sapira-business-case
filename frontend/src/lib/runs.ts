import type { Run } from "./types";

import email001 from "@/data/runs/email_001_clean_pdf.json";
import email002 from "@/data/runs/email_002_messy_body.json";
import email003 from "@/data/runs/email_003_duplicate.json";

const RUNS: Record<string, Run> = {
  email_001_clean_pdf: email001 as Run,
  email_002_messy_body: email002 as Run,
  email_003_duplicate: email003 as Run,
};

export function listRuns(): Run[] {
  return Object.values(RUNS);
}

export function getRun(emailId: string): Run | null {
  return RUNS[emailId] ?? null;
}
