"use client";

import { useEffect, useMemo, useState } from "react";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import type { StoredScoreResult } from "@/lib/scoring";
import { loadScoreResult } from "@/lib/scoring";

type Offer = {
  lender: string;
  amount: string;
  apr: string;
  tenure: string;
};

function riskBand(score: number): string {
  if (score >= 750) return "Excellent";
  if (score >= 650) return "Good";
  if (score >= 550) return "Fair";
  if (score >= 450) return "Review";
  return "High Risk";
}

function scoreArcPercent(score: number): number {
  return Math.max(0, Math.min(100, ((score - 300) / 600) * 100));
}

function fallbackOffers(score: number): Offer[] {
  if (score >= 700) {
    return [
      { lender: "SBI Mudra Loan", amount: "Up to ₹10,00,000", apr: "10.5% p.a.", tenure: "36 months" },
      { lender: "Bajaj Finserv", amount: "Up to ₹7,00,000", apr: "13% p.a.", tenure: "24 months" },
      { lender: "Ujjivan MFI Partner", amount: "Up to ₹2,00,000", apr: "18% p.a.", tenure: "12 months" }
    ];
  }
  if (score >= 600) {
    return [
      { lender: "SBI Mudra Loan", amount: "Up to ₹4,00,000", apr: "11.8% p.a.", tenure: "24 months" },
      { lender: "Bajaj Finserv", amount: "Up to ₹3,00,000", apr: "14.2% p.a.", tenure: "18 months" },
      { lender: "Ujjivan MFI Partner", amount: "Up to ₹1,50,000", apr: "19% p.a.", tenure: "12 months" }
    ];
  }
  return [
    { lender: "SBI Mudra Loan", amount: "Up to ₹1,50,000", apr: "12.9% p.a.", tenure: "18 months" },
    { lender: "Bajaj Finserv", amount: "Up to ₹1,00,000", apr: "15.7% p.a.", tenure: "12 months" },
    { lender: "Ujjivan MFI Partner", amount: "Up to ₹80,000", apr: "20% p.a.", tenure: "9 months" }
  ];
}

export default function ResultPage() {
  const [storedResult, setStoredResult] = useState<StoredScoreResult | null>(null);

  useEffect(() => {
    setStoredResult(loadScoreResult());
  }, []);

  const score = storedResult?.response.final_score ?? 0;
  const band = riskBand(score);
  const offers = useMemo(() => fallbackOffers(score), [score]);

  if (!storedResult) {
    return (
      <SurfaceCard>
        <p className="text-sm muted">No score result found. Run intake or demo processing first.</p>
        <div className="mt-4">
          <ActionLink href="/intake" className="text-sm">
            Start intake
          </ActionLink>
        </div>
      </SurfaceCard>
    );
  }

  const breakdown = storedResult.response.agent_breakdown;
  const conflictDetected =
    Math.max(breakdown.income, breakdown.repayment, breakdown.lifestyle) -
      Math.min(breakdown.income, breakdown.repayment, breakdown.lifestyle) >
    25;
  const spread =
    Math.max(breakdown.income, breakdown.repayment, breakdown.lifestyle) -
    Math.min(breakdown.income, breakdown.repayment, breakdown.lifestyle);

  const topPositive = storedResult.response.positive_factors?.[0] ?? "Utility repayment consistency improved score resilience.";
  const driverBars = [
    { label: "UPI transaction regularity", value: Math.round(breakdown.income * 0.42), agent: "Income Agent", positive: true },
    { label: "Utility on-time ratio", value: Math.round(breakdown.repayment * 0.38), agent: "Repayment Agent", positive: true },
    { label: "Savings rate", value: Math.round(breakdown.lifestyle * 0.29), agent: "Lifestyle Agent", positive: true },
    { label: "Income irregularity", value: -Math.max(6, Math.round((100 - breakdown.income) * 0.18)), agent: "Income Agent", positive: false },
    { label: "Compliance risk drag", value: -Math.max(4, storedResult.response.rbi_flags.length * 6), agent: "Compliance Agent", positive: false }
  ];

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="eyebrow">Logic score result</span>
            <h1 className="headline mt-3 text-4xl font-extrabold">{score}</h1>
            <p className="mt-1 text-sm muted">
              {band} · Completed in {(storedResult.response.processing_time_ms / 1000).toFixed(1)}s
            </p>
          </div>
          <div className="relative h-32 w-32">
            <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="transparent" stroke="rgba(255,255,255,0.12)" strokeWidth="8" />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="transparent"
                stroke="#a3a6ff"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(scoreArcPercent(score) / 100) * 264} 264`}
              />
            </svg>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" className="btn-secondary text-sm" onClick={() => window.print()}>
            Download Credit Report
          </button>
          <ActionLink href="/loan-marketplace" className="text-sm">
            View matched offers
          </ActionLink>
        </div>
      </SurfaceCard>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AgentCard name="Income Agent" score={breakdown.income} findings={storedResult.response.positive_factors ?? []} />
        <AgentCard name="Repayment Agent" score={breakdown.repayment} findings={storedResult.response.risk_factors ?? []} />
        <AgentCard name="Lifestyle Agent" score={breakdown.lifestyle} findings={storedResult.response.positive_factors ?? []} />
        <AgentCard
          name="Compliance Agent"
          score={storedResult.response.rbi_flags.length ? Math.max(35, 92 - storedResult.response.rbi_flags.length * 9) : 90}
          findings={storedResult.response.rbi_flags.length ? storedResult.response.rbi_flags : ["No major compliance conflicts detected"]}
        />
      </section>

      <SurfaceTile>
        <p className="headline text-xl font-bold">Conflict resolution</p>
        {conflictDetected ? (
          <p className="mt-2 text-sm muted">
            Contradiction detected across agents (spread: {spread}). Repayment was weighted higher for final synthesis due to
            stronger payment behavior. Final blend: Repayment 40%, Income 30%, Lifestyle 20%, Compliance 10%.
          </p>
        ) : (
          <p className="mt-2 text-sm muted">
            Agents were directionally aligned (spread: {spread}), so default weighted fusion was applied.
          </p>
        )}
        <p className="mt-2 text-sm text-slate-300">Resolution confidence: {storedResult.response.confidence}</p>
      </SurfaceTile>

      <SurfaceTile>
        <p className="headline text-xl font-bold">Feature drivers</p>
        <div className="mt-4 space-y-3">
          {driverBars.map((item) => (
            <div key={item.label}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span>{item.label}</span>
                <span className={item.positive ? "text-emerald-300" : "text-red-300"}>
                  {item.value >= 0 ? "+" : ""}
                  {item.value} pts · {item.agent}
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800">
                <div
                  className={`h-2 rounded-full ${item.positive ? "bg-emerald-400" : "bg-red-400"}`}
                  style={{ width: `${Math.min(100, Math.abs(item.value))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </SurfaceTile>

      <section className="grid gap-4 lg:grid-cols-2">
        <SurfaceTile>
          <p className="headline text-xl font-bold">Data provenance</p>
          <ul className="mt-3 space-y-2 text-sm muted">
            <li>Merchant diversity and UPI cadence were derived from bank statement transactions.</li>
            <li>Utility on-time behavior was inferred from recurring bill-payment narrations and payment dates.</li>
            <li>Regularity and stability scores were computed from month-over-month credit/debit patterns.</li>
          </ul>
        </SurfaceTile>

        <SurfaceTile>
          <p className="headline text-xl font-bold">Top improvement path</p>
          <p className="mt-2 text-sm muted">{topPositive}</p>
        </SurfaceTile>
      </section>

      <SurfaceTile>
        <p className="headline text-xl font-bold">Matched loan offers</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {offers.map((offer) => (
            <div key={offer.lender} className="rounded-2xl border border-outline-variant/30 bg-surface-low/80 p-4">
              <p className="font-semibold text-slate-100">{offer.lender}</p>
              <p className="mt-1 text-xs muted">{offer.amount}</p>
              <p className="text-xs muted">{offer.apr}</p>
              <p className="text-xs muted">{offer.tenure}</p>
            </div>
          ))}
        </div>
      </SurfaceTile>

      <RbiNotice
        disclaimer={storedResult.response.disclaimer}
        retention="Data retention: scoring inputs and generated reports may be retained for up to 30 days for auditability."
      />
    </div>
  );
}

function AgentCard({ name, score, findings }: { name: string; score: number; findings: string[] }) {
  const normalizedScore = Math.max(0, Math.min(100, score));
  return (
    <SurfaceTile>
      <p className="headline text-lg font-bold">{name}</p>
      <p className="mt-1 text-sm text-slate-100">{normalizedScore}/100</p>
      <div className="mt-2 h-2 rounded-full bg-slate-800">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${normalizedScore}%` }} />
      </div>
      <ul className="mt-3 space-y-1 text-xs muted">
        {(findings.length ? findings : ["Signal source: Derived from statement transactions"]).slice(0, 3).map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </SurfaceTile>
  );
}
