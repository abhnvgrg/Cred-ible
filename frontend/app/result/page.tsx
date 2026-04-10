"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import type { AgentScoreOutput, ConfidenceLevel, StoredScoreResult } from "@/lib/scoring";
import { isComplianceAgentOutput, loadScoreResult } from "@/lib/scoring";
import { useEffect, useMemo, useState } from "react";

function confidenceClass(confidence: ConfidenceLevel): string {
  if (confidence === "high") return "bg-emerald-500/20 text-emerald-200";
  if (confidence === "medium") return "bg-amber-400/20 text-amber-100";
  return "bg-red-500/20 text-red-200";
}

function confidenceLabel(confidence: ConfidenceLevel): string {
  return confidence.charAt(0).toUpperCase() + confidence.slice(1);
}

function formatKeyLabel(raw: string): string {
  return raw
    .replaceAll("_", " ")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDateTime(dateTime: string): string {
  const parsed = new Date(dateTime);
  if (Number.isNaN(parsed.getTime())) return dateTime;
  return parsed.toLocaleString();
}

function buildReportText(storedResult: StoredScoreResult): string {
  const { response } = storedResult;

  const lines = [
    "BharatCredit Score Report",
    "=========================",
    `Generated at: ${formatDateTime(storedResult.generatedAt)}`,
    `Flow source: ${storedResult.source}`,
    `Borrower: ${storedResult.borrowerName}`,
    `Persona: ${storedResult.persona ?? "N/A"}`,
    `Offline fallback used: ${storedResult.fallbackUsed ? "Yes" : "No"}`,
    ...(storedResult.fallbackReason ? [`Fallback reason: ${storedResult.fallbackReason}`] : []),
    "",
    "Summary",
    "-------",
    `Final score: ${response.final_score} / 900`,
    `Confidence: ${response.confidence}`,
    `Recommended loan range: ${response.recommended_loan_limit}`,
    `Processing time (ms): ${response.processing_time_ms}`,
    "",
    "Agent Breakdown",
    "---------------",
    `Income: ${response.agent_breakdown.income}`,
    `Repayment: ${response.agent_breakdown.repayment}`,
    `Lifestyle: ${response.agent_breakdown.lifestyle}`,
    `Compliance: ${response.agent_breakdown.compliance}`,
    "",
    "RBI Flags",
    "---------",
    ...(response.rbi_flags.length ? response.rbi_flags.map((flag) => `- ${flag}`) : ["- None"]),
    "",
    "Explanation",
    "-----------",
    response.explanation,
    "",
    "Disclaimer",
    "----------",
    response.disclaimer
  ];

  return lines.join("\n");
}

export default function ResultPage() {
  const [storedResult, setStoredResult] = useState<StoredScoreResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const nextResult = loadScoreResult();
    if (!nextResult) {
      setLoadError("No score result found. Please run intake or demo processing first.");
      return;
    }
    setStoredResult(nextResult);
  }, []);

  const scoreProgress = useMemo(() => {
    if (!storedResult) return 0;
    return Math.min(100, Math.max(0, ((storedResult.response.final_score - 300) / 600) * 100));
  }, [storedResult]);

  const nextAction = useMemo(() => {
    if (!storedResult || storedResult.source === "intake") {
      return {
        href: "/intake",
        label: "Run new intake assessment"
      };
    }

    return {
      href: "/persona-selection",
      label: "Run another persona demo"
    };
  }, [storedResult]);

  const handleDownloadReport = () => {
    if (!storedResult) return;

    const reportText = buildReportText(storedResult);
    const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const anchor = document.createElement("a");
    const safeBorrowerName = storedResult.borrowerName.replace(/\s+/g, "-").toLowerCase() || "borrower";
    anchor.href = url;
    anchor.download = `bharatcredit-report-${safeBorrowerName}.txt`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  if (loadError) {
    return (
      <SurfaceTile className="border border-red-500/35 bg-red-500/10">
        <h1 className="headline text-2xl font-bold text-red-100">Result unavailable</h1>
        <p className="mt-2 text-sm text-red-200">{loadError}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ActionLink href="/intake" className="text-sm">
            Go to intake
          </ActionLink>
          <ActionLink href="/persona-selection" variant="secondary" className="text-sm">
            Go to personas
          </ActionLink>
        </div>
      </SurfaceTile>
    );
  }

  if (!storedResult) {
    return (
      <SurfaceCard>
        <p className="text-sm muted">Loading score output...</p>
      </SurfaceCard>
    );
  }

  const { response } = storedResult;

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <p className="text-xs uppercase tracking-[0.14em] muted">
          {storedResult.borrowerName} • Generated {formatDateTime(storedResult.generatedAt)}
        </p>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm muted">Final credit score</p>
            <p className="headline mt-1 text-5xl font-extrabold display-gradient sm:text-6xl">{response.final_score}</p>
            <p className="mt-1 text-xs muted">Scale: 300 to 900</p>
          </div>
          <span className={`status-pill ${confidenceClass(response.confidence)}`}>
            Confidence {confidenceLabel(response.confidence)}
          </span>
        </div>
        <div className="mt-5">
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${scoreProgress}%` }} aria-label="Final score progress" />
          </div>
          <div className="mt-1 flex justify-between text-xs muted">
            <span>300</span>
            <span>900</span>
          </div>
        </div>
      </SurfaceCard>

      {storedResult.fallbackUsed ? (
        <SurfaceTile className="border border-amber-400/35 bg-amber-400/12">
          <p className="headline text-lg font-bold text-amber-100">Offline fallback result</p>
          <p className="mt-1 text-sm text-amber-200/90">
            {storedResult.fallbackReason ??
              "Live scoring API was unavailable. This result was generated locally for continuity."}
          </p>
        </SurfaceTile>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2">
        <SurfaceTile>
          <h2 className="headline text-xl font-bold">Recommendation</h2>
          <p className="mt-3 text-sm muted">Recommended loan range</p>
          <p className="headline mt-1 text-3xl font-bold text-primary">{response.recommended_loan_limit}</p>
          <p className="mt-3 text-sm muted">Processing time: {response.processing_time_ms} ms</p>
        </SurfaceTile>

        <SurfaceTile>
          <h2 className="headline text-xl font-bold">RBI flags</h2>
          {response.rbi_flags.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm muted">
              {response.rbi_flags.map((flag) => (
                <li key={flag}>{flag}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm muted">No RBI flags were raised.</p>
          )}
        </SurfaceTile>
      </section>

      <SurfaceCard>
        <h2 className="headline text-xl font-bold">Explanation</h2>
        <p className="mt-3 whitespace-pre-line text-sm leading-6 muted">{response.explanation}</p>
      </SurfaceCard>

      <SurfaceCard>
        <h2 className="headline text-xl font-bold">Agent breakdown</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SurfaceTile className="p-3">
            <p className="text-xs uppercase tracking-wider muted">Income</p>
            <p className="headline mt-1 text-2xl font-bold">{response.agent_breakdown.income}</p>
          </SurfaceTile>
          <SurfaceTile className="p-3">
            <p className="text-xs uppercase tracking-wider muted">Repayment</p>
            <p className="headline mt-1 text-2xl font-bold">{response.agent_breakdown.repayment}</p>
          </SurfaceTile>
          <SurfaceTile className="p-3">
            <p className="text-xs uppercase tracking-wider muted">Lifestyle</p>
            <p className="headline mt-1 text-2xl font-bold">{response.agent_breakdown.lifestyle}</p>
          </SurfaceTile>
          <SurfaceTile className="p-3">
            <p className="text-xs uppercase tracking-wider muted">Compliance</p>
            <p className="headline mt-1 text-2xl font-bold capitalize">{response.agent_breakdown.compliance}</p>
          </SurfaceTile>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {Object.entries(response.agent_outputs).length ? (
            Object.entries(response.agent_outputs).map(([agentName, output]) => (
              <SurfaceTile key={agentName}>
                <h3 className="headline text-lg font-bold">{formatKeyLabel(agentName)} agent</h3>
                {isComplianceAgentOutput(output) ? (
                  <div className="mt-2 space-y-1 text-sm muted">
                    <p>RBI compliant: {output.rbi_compliant ? "Yes" : "No"}</p>
                    <p>Fraud risk: {formatKeyLabel(output.fraud_risk)}</p>
                    <p>Notes: {output.notes}</p>
                    {output.flags.length ? (
                      <ul className="mt-2 list-disc space-y-1 pl-5">
                        {output.flags.map((flag) => (
                          <li key={flag}>{flag}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : (
                  <AgentScoreDetails output={output} />
                )}
              </SurfaceTile>
            ))
          ) : (
            <p className="text-sm muted">Agent-level outputs were not available for this run.</p>
          )}
        </div>
      </SurfaceCard>

      <RbiNotice
        title="Disclaimer"
        disclaimer={response.disclaimer}
        retention="Data retention: generated reports and score snapshots may be retained for up to 30 days for audits, grievance handling, and model quality monitoring."
      />

      <section className="flex flex-wrap gap-3">
        <button type="button" onClick={handleDownloadReport} className="btn-primary text-sm">
          Download report
        </button>
        <ActionLink href={nextAction.href} variant="secondary" className="text-sm">
          {nextAction.label}
        </ActionLink>
        <ActionLink href="/what-if-analysis" variant="ghost" className="text-sm">
          What-if analysis
        </ActionLink>
        <ActionLink href="/loan-marketplace" variant="ghost" className="text-sm">
          Loan marketplace
        </ActionLink>
      </section>
    </div>
  );
}

function AgentScoreDetails({ output }: { output: AgentScoreOutput }) {
  return (
    <div className="mt-2 space-y-1 text-sm muted">
      <p>Score: {output.score}</p>
      <p>Confidence: {confidenceLabel(output.confidence)}</p>
      <p>Reasoning: {output.reasoning}</p>
      {output.flags.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {output.flags.map((flag) => (
            <li key={flag}>{flag}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
