import { NextResponse } from "next/server";
import { getRun } from "@/lib/runs";

export const runtime = "nodejs";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const emailId = searchParams.get("email_id");
  if (!emailId) {
    return NextResponse.json({ error: "missing email_id" }, { status: 400 });
  }
  const run = getRun(emailId);
  if (!run) {
    return NextResponse.json({ error: `unknown email_id: ${emailId}` }, { status: 404 });
  }
  return NextResponse.json(run);
}
