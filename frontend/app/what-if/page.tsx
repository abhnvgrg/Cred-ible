"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { loadScoreResult } from "@/lib/scoring";
import { useEffect, useMemo, useState } from "react";

interface WhatIfRequest {
  base_score: number;
  income_shift: number;
  compliance_boost: number;
  debt_reduction: number;
}

interface WhatIfRecommendation {
  title: string;
  impact: "high" | "medium" | "low";
  note: string;
}

interface WhatIfResponse {
  base_score: number;
  projected_score: number;
  score_delta: number;
  confidence: "high" | "medium" | "low";
  explanation: string;
  recommendations: WhatIfRecommendation[];
  processing_time_ms: number;
  disclaimer: string;
}

export default function WhatIfPage() {
  const [baseScore, setBaseScore] = useState(714);
  const [incomeShift, setIncomeShift] = useState(12);
  const [complianceBoost, setComplianceBoost] = useState(8);
  const [debtReduction, setDebtReduction] = useState(9);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<WhatIfResponse | null>(null);

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
        const response = await apiFetch<WhatIfResponse>("/simulate/what-if", {
          method: "POST",
          body: JSON.stringify(payload),
          timeoutMs: 10000
        });
        if (!cancelled) {
          setResult(response);
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
