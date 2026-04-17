"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { loadOfflinePersonaPayload, scoreBorrowerOffline } from "@/lib/offline-score";
import type { BorrowerSignalInput, ScoreResponse } from "@/lib/scoring";
import { clearIntakePayload, loadIntakePayload, saveScoreResult } from "@/lib/scoring";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

type AgentStatus = "pending" | "running" | "done" | "error";

const AGENTS = [
  { key: "income", label: "Income Agent", detail: "Evaluating cashflow and earnings stability" },
  { key: "repayment", label: "Repayment Agent", detail: "Reviewing rent + utility repayment habits" },
  { key: "lifestyle", label: "Lifestyle Agent", detail: "Assessing behavioral consistency from mobile signals" },
  { key: "compliance", label: "Compliance Agent", detail: "Running RBI checks and fraud-risk controls" }
];

const MIN_DURATION_MS = 3200;
const NAV_DELAY_MS = 600;
const MISSING_PAYLOAD_REDIRECT_MS = 1800;
const REQUEST_TIMEOUT_MS = 12000;

function statusBadgeClass(status: AgentStatus): string {
  if (status === "done") return "bg-emerald-500/20 text-emerald-200";
  if (status === "running") return "bg-primary/25 text-indigo-100";
  if (status === "error") return "bg-red-500/20 text-red-200";
  return "bg-slate-700/45 text-slate-300";
}

function statusLabel(status: AgentStatus): string {
  if (status === "done") return "Completed";
  if (status === "running") return "Running";
  if (status === "error") return "Failed";
  return "Queued";
}

function toDisplayName(rawPersona: string): string {
  if (!rawPersona) return "Demo Persona";
  return rawPersona.charAt(0).toUpperCase() + rawPersona.slice(1);
}

function isLikelyBackendAvailabilityIssue(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const message = error.message.toLowerCase();
  return (
    message.includes("unable to reach cred-ible api") ||
    message.includes("timed out") ||
    message.includes("api request failed (502)") ||
    message.includes("api request failed (503)") ||
    message.includes("api request failed (504)")
  );
}

function getBackLink(persona: string | null, source: string | null): { href: string; label: string } {
  if (persona) {
    if (source === "marketing") return { href: "/landing-page", label: "Back to home" };
    return { href: "/persona-selection", label: "Back to personas" };
  }
  return { href: "/intake", label: "Back to intake" };
}

function ProcessingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const persona = useMemo(() => {
    const rawPersona = searchParams.get("persona");
    if (!rawPersona) return null;
    const normalizedPersona = rawPersona.trim().toLowerCase();
    return normalizedPersona.length > 0 ? normalizedPersona : null;
  }, [searchParams]);
  const source = useMemo(() => searchParams.get("source"), [searchParams]);
  const backLink = useMemo(() => getBackLink(persona, source), [persona, source]);

  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>(AGENTS.map(() => "pending"));
  const [statusMessage, setStatusMessage] = useState("Preparing scoring workflow...");
  const [error, setError] = useState<string | null>(null);
  const [missingPayload, setMissingPayload] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const progressPercentage = useMemo(() => {
    if (error) return 100;
    const completedCount = agentStatuses.filter((status) => status === "done").length;
    const runningCount = agentStatuses.filter((status) => status === "running").length;
    return Math.min(100, Math.round(((completedCount + runningCount * 0.5) / AGENTS.length) * 100));
  }, [agentStatuses, error]);

  useEffect(() => {
    let cancelled = false;
    const timers: number[] = [];

    const persistResultAndNavigate = (
      response: ScoreResponse,
      borrowerName: string,
      options?: { fallbackUsed?: boolean; fallbackReason?: string }
    ) => {
      const saved = saveScoreResult({
        response,
        source: persona ? "persona" : "intake",
        persona,
        borrowerName,
        generatedAt: new Date().toISOString(),
        fallbackUsed: options?.fallbackUsed,
        fallbackReason: options?.fallbackReason ?? null
      });

      if (!saved) {
        setError("Scoring completed but this browser blocked local storage. Please retry.");
        setAgentStatuses((previous) => previous.map((status) => (status === "done" ? status : "error")));
        setStatusMessage("Unable to save scoring result.");
        return;
      }

      if (!persona) clearIntakePayload();

      const navTimer = window.setTimeout(() => {
        if (!cancelled) router.replace("/credit-dashboard");
      }, NAV_DELAY_MS);
      timers.push(navTimer);
    };

    const runScoring = async () => {
      setError(null);
      setMissingPayload(false);
      setAgentStatuses(AGENTS.map(() => "pending"));
      setStatusMessage(persona ? `Loading demo persona: ${toDisplayName(persona)}` : "Loading intake payload");

      const startedAt = Date.now();
      let fallbackPayload: BorrowerSignalInput | null = null;
      let borrowerName = "Applicant";

      AGENTS.forEach((agent, index) => {
        const timer = window.setTimeout(() => {
          if (cancelled) return;
          setAgentStatuses((previous) =>
            previous.map((status, currentIndex) => {
              if (currentIndex < index && status !== "error") return "done";
              if (currentIndex === index) return "running";
              return status;
            })
          );
          setStatusMessage(`${agent.label} is running...`);
        }, index * 700);
        timers.push(timer);
      });

      try {
        let response: ScoreResponse;

        if (persona) {
          fallbackPayload = loadOfflinePersonaPayload(persona);
          borrowerName = fallbackPayload?.borrower_name ?? toDisplayName(persona);
          response = await apiFetch<ScoreResponse>(`/score/demo/${encodeURIComponent(persona)}`, {
            method: "POST",
            timeoutMs: REQUEST_TIMEOUT_MS
          });
        } else {
          const payload = loadIntakePayload();
          if (!payload) {
            setMissingPayload(true);
            setStatusMessage("No intake payload found. Redirecting to intake...");
            setAgentStatuses(AGENTS.map(() => "pending"));
            const redirectTimer = window.setTimeout(() => {
              if (!cancelled) router.replace("/intake");
            }, MISSING_PAYLOAD_REDIRECT_MS);
            timers.push(redirectTimer);
            return;
          }

          fallbackPayload = payload;
          borrowerName = payload.borrower_name;
          response = await apiFetch<ScoreResponse>("/score", {
            method: "POST",
            body: JSON.stringify(payload),
            timeoutMs: REQUEST_TIMEOUT_MS
          });
        }

        const elapsed = Date.now() - startedAt;
        if (elapsed < MIN_DURATION_MS) {
          await new Promise<void>((resolve) => {
            const timer = window.setTimeout(() => resolve(), MIN_DURATION_MS - elapsed);
            timers.push(timer);
          });
        }
        if (cancelled) return;

        setAgentStatuses(AGENTS.map(() => "done"));
        setStatusMessage("Scoring complete. Preparing results...");
        persistResultAndNavigate(response, borrowerName);
      } catch (scoringError) {
        if (cancelled) return;

        const canFallbackOffline = fallbackPayload !== null && isLikelyBackendAvailabilityIssue(scoringError);
        if (canFallbackOffline && fallbackPayload) {
          const fallbackResponse = scoreBorrowerOffline(fallbackPayload, { processingTimeMs: 950 });
          setAgentStatuses(AGENTS.map(() => "done"));
          setStatusMessage("Live API unavailable. Using offline demo scoring...");
          persistResultAndNavigate(fallbackResponse, borrowerName, {
            fallbackUsed: true,
            fallbackReason: "Live scoring API was unavailable. Offline estimation was used for continuity."
          });
          return;
        }

        setAgentStatuses((previous) => previous.map((status) => (status === "done" ? status : "error")));
        setStatusMessage("Scoring failed.");
        setError(
          scoringError instanceof Error ? scoringError.message : "Unexpected error while processing this borrower."
        );
      }
    };

    void runScoring();

    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [attempt, persona, router]);

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">AI processing</span>
        <h1 className="headline mt-4 text-3xl font-extrabold sm:text-4xl">Synthesizing credit decision</h1>
        <p className="mt-2 text-sm muted">{statusMessage}</p>
        <div className="mt-4 progress-track">
          <div
            className={`progress-fill ${error ? "!bg-red-500 !shadow-none" : ""}`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        <p className="mt-3 text-xs uppercase tracking-[0.16em] muted">
          {persona ? `Demo persona: ${toDisplayName(persona)}` : "Borrower intake flow"}
        </p>
      </SurfaceCard>

      <section className="neon-grid">
        {AGENTS.map((agent, index) => {
          const status = agentStatuses[index];
          return (
            <SurfaceTile key={agent.key} className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="headline text-lg font-bold">{agent.label}</p>
                <p className="mt-1 text-sm muted">{agent.detail}</p>
              </div>
              <span className={`status-pill ${statusBadgeClass(status)}`}>{statusLabel(status)}</span>
            </SurfaceTile>
          );
        })}
      </section>

      {error ? (
        <SurfaceTile className="border border-red-500/35 bg-red-500/10">
          <p className="headline text-lg font-bold text-red-100">Processing interrupted</p>
          <p className="mt-2 text-sm text-red-200/90">{error}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={() => setAttempt((current) => current + 1)} className="btn-primary text-sm">
              Retry processing
            </button>
            <ActionLink href={backLink.href} variant="secondary" className="text-sm">
              {backLink.label}
            </ActionLink>
            {!persona ? (
              <ActionLink href="/persona-selection" variant="ghost" className="text-sm">
                Use persona demo
              </ActionLink>
            ) : null}
          </div>
        </SurfaceTile>
      ) : null}

      {missingPayload ? (
        <SurfaceTile className="border border-outline-variant/35 bg-surface-low/80">
          <p className="headline text-lg font-bold text-slate-100">Let&apos;s start your first assessment</p>
          <p className="mt-2 text-sm muted">We&apos;ll guide you to the right starting point to begin scoring.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <ActionLink href="/intake" className="text-sm">
              Start intake
            </ActionLink>
            <ActionLink href="/persona-selection" variant="secondary" className="text-sm">
              Try demo persona
            </ActionLink>
          </div>
        </SurfaceTile>
      ) : null}

      <RbiNotice
        disclaimer="Automated scoring remains a decision-support step and should be paired with lender underwriting controls and RBI compliance checks."
        retention="Data retention: processing activity and fallback events may be logged for up to 30 days for auditability and incident analysis."
      />
    </div>
  );
}

function ProcessingFallback() {
  return (
    <SurfaceCard>
      <h1 className="headline text-2xl font-bold">Preparing processing workflow...</h1>
      <p className="mt-2 text-sm muted">Initializing agent orchestration.</p>
    </SurfaceCard>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense fallback={<ProcessingFallback />}>
      <ProcessingPageContent />
    </Suspense>
  );
}
