import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api";

type PersonasResponse = {
  personas: Array<{
    id: string;
    name: string;
    profile: string;
  }>;
};

export async function GET() {
  try {
    const response = await apiFetch<PersonasResponse>("/personas");
    return NextResponse.json(response);
  } catch {
    return NextResponse.json({ error: "Unable to fetch personas" }, { status: 502 });
  }
}
