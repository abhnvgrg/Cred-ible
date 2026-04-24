"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { loadParsedStatementResult, loadScoreResult } from "@/lib/scoring";
import {
  buildSimulationAnalysis,
  type SimulationAnalysisJson,
  type WhatIfSimulationResponse,
} from "@/lib/simulation-analysis";
import { useEffect, useMemo, useState } from "react";

interface WhatIfRequest {
  base_score: number;
  income_shift: number;
  compliance_boost: number;
  debt_reduction: number;
}

export default function WhatIfPage() {
  const [baseScore, setBaseScore] = useState(670);
  const [incomeShift, setIncomeShift] = useState(12);
  const [complianceBoost, setComplianceBoost] = useState(8);
  const [debtReduction, setDebtReduction] = useState(9);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<WhatIfSimulationResponse | null>(null);
  const [analysis, setAnalysis] = useState<SimulationAnalysisJson | null>(null);
  const [analysisSummary, setAnalysisSummary] = useState<string | null>(null);

  useEffect(() => {
    const existingResult = loadScoreResult();
    if (existingResult) {
      setBaseScore(existingResult.response.final_score);
    }
  }, []);

  const payload: WhatIfRequest = useMemo(
    () => ({
      base_score: baseScore,
      income_shift: incomeShift,
      compliance_boost: complianceBoost,
      debt_reduction: debtReduction
    }),
    [baseScore, complianceBoost, debtReduction, incomeShift]
  );

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await apiFetch<WhatIfSimulationResponse>("/simulate/what-if", {
          method: "POST",
          body: JSON.stringify(payload),
          timeoutMs: 10000
        });
        if (!cancelled) {
          setResult(response);
          const parsedStatement = loadParsedStatementResult();
          const storedScore = loadScoreResult();
          if (parsedStatement && storedScore) {
            const nextAnalysis = buildSimulationAnalysis(parsedStatement, storedScore, response);
            setAnalysis(nextAnalysis.json);
            setAnalysisSummary(nextAnalysis.summary);
          } else {
            setAnalysis(null);
            setAnalysisSummary(null);
          }
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : "Simulation failed.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }, 280);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [payload]);

  const projectedScore = result?.projected_score ?? baseScore;
  const scoreDelta = result?.score_delta ?? 0;

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">Scenario simulation</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">What-if analysis</h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed muted">
          Simulate behavior and compliance adjustments to estimate how a borrower&apos;s score may evolve before final
          underwriting.
        </p>
      </SurfaceCard>

      <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
        <SurfaceCard className="space-y-6">
          <Slider
            label="Increase monthly income stability"
            value={incomeShift}
            onChange={setIncomeShift}
            min={0}
            max={20}
          />
          <Slider
            label="Improve GST/compliance consistency"
            value={complianceBoost}
            onChange={setComplianceBoost}
            min={0}
            max={20}
          />
          <Slider
            label="Reduce debt-utilization stress"
            value={debtReduction}
            onChange={setDebtReduction}
            min={0}
            max={20}
          />
          {errorMessage ? <p className="text-sm text-red-200">{errorMessage}</p> : null}
          {result?.recommendations?.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {result.recommendations.map((item) => (
                <SurfaceTile key={item.title}>
                  <p className="text-xs uppercase tracking-[0.12em] muted">{item.impact} impact</p>
                  <p className="headline mt-1 text-lg font-bold">{item.title}</p>
                  <p className="mt-1 text-sm muted">{item.note}</p>
                </SurfaceTile>
              ))}
            </div>
          ) : null}
        </SurfaceCard>

        <SurfaceCard className="text-center">
          <p className="text-xs uppercase tracking-[0.15em] muted">Projected score</p>
          <p className="headline mt-3 text-7xl font-extrabold display-gradient">{projectedScore}</p>
          <p className={`mt-2 text-sm font-semibold ${scoreDelta >= 0 ? "text-emerald-300" : "text-red-200"}`}>
            {scoreDelta >= 0 ? "+" : ""}
            {scoreDelta} vs baseline ({baseScore})
          </p>
          <div className="mt-6 grid gap-3 text-left sm:grid-cols-2">
            <SurfaceTile>
              <p className="text-xs uppercase tracking-[0.12em] muted">Confidence</p>
              <p className="headline mt-2 text-xl font-bold">{result?.confidence ?? "pending"}</p>
            </SurfaceTile>
            <SurfaceTile>
              <p className="text-xs uppercase tracking-[0.12em] muted">Status</p>
              <p className="headline mt-2 text-xl font-bold">{isLoading ? "Simulating..." : "Ready"}</p>
            </SurfaceTile>
          </div>
          {result?.explanation ? <p className="mt-4 text-sm muted">{result.explanation}</p> : null}
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <ActionLink href="/ai-processing" className="text-sm">
              Reprocess borrower
            </ActionLink>
            <ActionLink href="/loan-marketplace" variant="secondary" className="text-sm">
              View loan offers
            </ActionLink>
          </div>
        </SurfaceCard>
      </div>

      {analysis ? (
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <SurfaceCard className="space-y-5">
            <div>
              <span className="eyebrow">Simulation Audit</span>
              <h2 className="headline mt-3 text-3xl font-extrabold">Full statement-quality and agent analysis</h2>
              {analysisSummary ? <p className="mt-2 text-sm muted">{analysisSummary}</p> : null}
            </div>

            <SurfaceTile>
              <p className="headline text-xl font-bold">Data Integrity Audit</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <Metric label="Data quality score" value={`${analysis.data_quality.score}/100`} />
                <Metric label="Utility consistency" value={analysis.data_quality.utility_consistency} />
                <Metric label="Parallel balance tracks" value={analysis.data_quality.parallel_balance_tracks ? "Yes" : "No"} />
                <Metric label="Rent payments found" value={analysis.data_quality.rent_payments_found ? "Yes" : "No"} />
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <ListBlock title="Audit flags" items={analysis.data_quality.flags} emptyLabel="No audit flags raised." />
                <ListBlock title="Missing months" items={analysis.data_quality.missing_months} emptyLabel="No missing months." />
              </div>
            </SurfaceTile>

            <section className="grid gap-4 lg:grid-cols-3">
              <AgentAnalysisCard
                title="Income Agent"
                score={analysis.agents.income.score}
                confidence={analysis.agents.income.confidence}
                lines={[
                  `Income type: ${analysis.agents.income.regularity === "HIGH" ? "gig/active" : "mixed or variable"}`,
                  `Raw avg: INR ${analysis.agents.income.raw_monthly_avg.toLocaleString("en-IN")}`,
                  `Corrected avg: INR ${analysis.agents.income.corrected_monthly_avg.toLocaleString("en-IN")}`,
                  `Trend: ${analysis.agents.income.trend}`,
                ]}
                reasoning={analysis.agents.income.reasoning}
              />
              <AgentAnalysisCard
                title="Repayment Agent"
                score={analysis.agents.repayment.score}
                confidence={analysis.agents.repayment.confidence}
                lines={[
                  `Bills found: ${analysis.agents.repayment.bills_found.length ? analysis.agents.repayment.bills_found.join(", ") : "None visible"}`,
                  `EMIs found: ${analysis.agents.repayment.emis_found ? "Yes" : "No"}`,
                  `Rent found: ${analysis.agents.repayment.rent_found ? "Yes" : "No"}`,
                ]}
                reasoning={analysis.agents.repayment.reasoning}
              />
              <AgentAnalysisCard
                title="Lifestyle Agent"
                score={analysis.agents.lifestyle.score}
                confidence={analysis.final.confidence}
                lines={[
                  `Essential ratio: ${(analysis.agents.lifestyle.essential_ratio * 100).toFixed(0)}%`,
                  `Multiple SIMs: ${analysis.agents.lifestyle.multiple_sims ? "Yes" : "No"}`,
                ]}
                reasoning={analysis.agents.lifestyle.reasoning}
              />
            </section>

            <SurfaceTile>
              <p className="headline text-xl font-bold">Conflict Resolution</p>
              <ListBlock
                title="Conflicts"
                items={analysis.conflicts}
                emptyLabel="No major conflicts required manual override."
              />
            </SurfaceTile>

            <SurfaceTile>
              <p className="headline text-xl font-bold">Final Lending View</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                <Metric label="Internal score" value={`${analysis.final.internal_score}/100`} />
                <Metric label="Credit score" value={String(analysis.final.credit_score)} />
                <Metric label="Risk level" value={analysis.final.risk_level} />
                <Metric label="Confidence" value={analysis.final.confidence} />
                <Metric label="Compliance penalty" value={String(analysis.final.compliance_penalty)} />
                <Metric
                  label="Recommended loan range"
                  value={`INR ${analysis.final.recommended_loan_range_inr.min.toLocaleString("en-IN")} - INR ${analysis.final.recommended_loan_range_inr.max.toLocaleString("en-IN")}`}
                />
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <ListBlock title="Positive factors" items={analysis.final.positive_factors} emptyLabel="No positive factors captured." />
                <ListBlock title="Risk factors" items={analysis.final.risk_factors} emptyLabel="No risk factors captured." />
              </div>
              <p className="mt-4 text-sm muted">{analysis.final.lender_notes}</p>
            </SurfaceTile>
          </SurfaceCard>

          <SurfaceCard>
            <p className="eyebrow">Structured JSON</p>
            <h2 className="headline mt-3 text-2xl font-extrabold">Simulation output payload</h2>
            <pre className="mt-4 overflow-x-auto rounded-2xl bg-slate-950/80 p-4 text-xs leading-6 text-slate-200">
              {JSON.stringify(analysis, null, 2)}
            </pre>
          </SurfaceCard>
        </div>
      ) : result ? (
        <SurfaceCard>
          <p className="headline text-xl font-bold">Detailed audit unavailable</p>
          <p className="mt-2 text-sm muted">
            The simulation ran, but no stored parser audit was found for this borrower in the current browser session.
            Upload a statement through intake first to populate the full integrity audit on this page.
          </p>
        </SurfaceCard>
      ) : null}

      <RbiNotice
        disclaimer={
          result?.disclaimer ??
          "Scenario outcomes are indicative decision-support estimates and must not replace complete RBI-compliant underwriting."
        }
        retention="Data retention: simulation parameters may be retained for up to 30 days to support explainability and audit trails."
      />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-outline-variant/25 bg-surface-low/70 p-4">
      <p className="text-xs uppercase tracking-[0.12em] muted">{label}</p>
      <p className="headline mt-1 text-lg font-bold">{value}</p>
    </div>
  );
}

function ListBlock({
  title,
  items,
  emptyLabel
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.12em] muted">{title}</p>
      {items.length ? (
        <ul className="mt-2 space-y-2 text-sm muted">
          {items.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm muted">{emptyLabel}</p>
      )}
    </div>
  );
}

function AgentAnalysisCard({
  title,
  score,
  confidence,
  lines,
  reasoning
}: {
  title: string;
  score: number;
  confidence: string;
  lines: string[];
  reasoning: string;
}) {
  return (
    <SurfaceTile>
      <p className="headline text-lg font-bold">{title}</p>
      <p className="mt-1 text-sm text-slate-100">
        {score}/100 · {confidence}
      </p>
      <ul className="mt-3 space-y-2 text-sm muted">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="mt-3 text-sm muted">{reasoning}</p>
    </SurfaceTile>
  );
}

function Slider({
  label,
  value,
  onChange,
  min,
  max
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
  min: number;
  max: number;
}) {
  return (
    <label className="space-y-2">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-semibold text-slate-100">{label}</span>
        <span className="status-pill bg-primary/25 text-indigo-100">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-primary"
      />
    </label>
  );
}
