"use client";

import { SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import type { SimulationAnalysisJson } from "@/lib/simulation-analysis";

export function SimulationAuditDisplay({ analysis }: { analysis: SimulationAnalysisJson }) {
  const keyAuditIssues = buildAuditIssueCards(analysis);

  return (
    <>
      <SurfaceCard className="space-y-5">
        <div>
          <span className="eyebrow">Statement Quality & Agent Analysis</span>
          <h2 className="headline mt-3 text-3xl font-extrabold">Simulation Audit Results</h2>
        </div>

        <SurfaceTile className="space-y-4">
          <p className="headline text-xl font-bold">Statement Audit Findings</p>
          <div className="rounded-2xl border border-red-300/30 bg-red-950/40 p-4">
            <p className="text-sm font-semibold text-red-200">
              Critical signal: {analysis.data_quality.parallel_balance_tracks ? "parallel balance tracks detected" : "no parallel balance tracks detected"}
            </p>
            <p className="mt-1 text-sm text-red-100/90">
              Data quality score is {analysis.data_quality.score}/100.{" "}
              {analysis.data_quality.score < 70
                ? "Scoring should be interpreted cautiously and surfaced for lender override."
                : "Data quality is usable, with issue-level review still required."}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-outline-variant/25 bg-surface-low/70 p-4">
              <p className="text-xs uppercase tracking-[0.12em] muted">Income comparison</p>
              <div className="mt-3 space-y-3">
                <BarRow
                  label="Raw avg"
                  value={analysis.data_quality.raw_monthly_income_avg}
                  max={Math.max(
                    analysis.data_quality.raw_monthly_income_avg,
                    analysis.data_quality.corrected_monthly_income_avg,
                    1
                  )}
                  tone="red"
                />
                <BarRow
                  label="Corrected avg"
                  value={analysis.data_quality.corrected_monthly_income_avg}
                  max={Math.max(
                    analysis.data_quality.raw_monthly_income_avg,
                    analysis.data_quality.corrected_monthly_income_avg,
                    1
                  )}
                  tone="green"
                />
              </div>
            </div>
            <div className="rounded-2xl border border-outline-variant/25 bg-surface-low/70 p-4">
              <p className="text-xs uppercase tracking-[0.12em] muted">Verdict</p>
              <p className="mt-2 text-sm text-slate-100">
                Score {analysis.final.credit_score} is {analysis.final.confidence.toLowerCase()} confidence with{" "}
                {analysis.final.risk_level.toLowerCase()} risk.{" "}
                {analysis.data_quality.score < 70
                  ? "Primary decision risk comes from statement quality anomalies."
                  : "Primary decision risk comes from borrower behaviour, not statement completeness."}
              </p>
              <p className="mt-2 text-sm muted">{analysis.final.lender_notes}</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {keyAuditIssues.map((issue) => (
              <IssueCard key={issue.title} title={issue.title} body={issue.body} severity={issue.severity} />
            ))}
          </div>
        </SurfaceTile>

        <SurfaceTile>
          <p className="headline text-xl font-bold">Data Integrity Audit</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Metric label="Data quality score" value={`${analysis.data_quality.score}/100`} />
            <Metric label="Utility consistency" value={analysis.data_quality.utility_consistency} />
            <Metric label="Parallel balance tracks" value={analysis.data_quality.parallel_balance_tracks ? "Yes" : "No"} />
            <Metric label="Rent payments found" value={analysis.data_quality.rent_payments_found ? "Yes" : "No"} />
            <Metric
              label="Raw monthly credits avg"
              value={`INR ${analysis.data_quality.raw_monthly_income_avg.toLocaleString("en-IN")}`}
            />
            <Metric
              label="Corrected monthly credits avg"
              value={`INR ${analysis.data_quality.corrected_monthly_income_avg.toLocaleString("en-IN")}`}
            />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <ListBlock title="Audit flags" items={analysis.data_quality.flags} emptyLabel="No audit flags raised." />
            <ListBlock title="Missing months" items={analysis.data_quality.missing_months} emptyLabel="No missing months." />
            <ListBlock
              title="Anomalous income months"
              items={analysis.data_quality.anomalous_income_months}
              emptyLabel="No anomalous income spikes."
            />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <ListBlock
              title="Balance track ranges"
              items={analysis.data_quality.balance_track_ranges}
              emptyLabel="No separate balance tracks detected."
            />
            <ListBlock
              title="Utility providers"
              items={analysis.data_quality.utility_providers}
              emptyLabel="No mapped utility providers found."
            />
            <ListBlock
              title="Months without utilities"
              items={analysis.data_quality.months_without_utility_payments}
              emptyLabel="Utility payment appears in each month."
            />
          </div>
        </SurfaceTile>

        <section className="grid gap-4 lg:grid-cols-3">
          <AgentAnalysisCard
            title="Income Agent"
            score={analysis.agents.income.score}
            confidence={analysis.agents.income.confidence}
            lines={[
              `Income type: ${analysis.agents.income.income_type}`,
              `Raw avg: INR ${analysis.agents.income.raw_monthly_avg.toLocaleString("en-IN")}`,
              `Corrected avg: INR ${analysis.agents.income.corrected_monthly_avg.toLocaleString("en-IN")}`,
              `Trend: ${analysis.agents.income.trend}`,
              `Raw score (pre-correction): ${analysis.agents.income.raw_score_before_anomaly_correction}/100`,
              `Corrected score (post-correction): ${analysis.agents.income.corrected_score_after_anomaly_correction}/100`,
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
              `Confirmed payments: ${analysis.agents.repayment.confirmed_payments_made}/${analysis.agents.repayment.expected_payments}`,
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
        </SurfaceTile>
      </SurfaceCard>
    </>
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

function BarRow({
  label,
  value,
  max,
  tone,
}: {
  label: string;
  value: number;
  max: number;
  tone: "red" | "green";
}) {
  const width = Math.max(8, Math.round((value / max) * 100));
  const barClass = tone === "red" ? "bg-red-500/60" : "bg-emerald-500/60";
  return (
    <div>
      <div className="flex items-center justify-between text-xs muted">
        <span>{label}</span>
        <span>INR {value.toLocaleString("en-IN")}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-slate-700/50">
        <div className={`h-2 rounded-full ${barClass}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function ListBlock({
  title,
  items,
  emptyLabel,
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
  reasoning,
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

function IssueCard({
  title,
  body,
  severity,
}: {
  title: string;
  body: string;
  severity: "critical" | "warning" | "notice";
}) {
  const className =
    severity === "critical"
      ? "border-red-300/30 bg-red-950/30 text-red-100"
      : severity === "warning"
        ? "border-amber-300/30 bg-amber-950/30 text-amber-100"
        : "border-slate-400/30 bg-slate-800/50 text-slate-100";
  return (
    <div className={`rounded-2xl border p-4 ${className}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm opacity-90">{body}</p>
    </div>
  );
}

function buildAuditIssueCards(
  analysis: SimulationAnalysisJson
): Array<{
  title: string;
  body: string;
  severity: "critical" | "warning" | "notice";
}> {
  const cards: Array<{ title: string; body: string; severity: "critical" | "warning" | "notice" }> = [];

  if (analysis.data_quality.parallel_balance_tracks) {
    cards.push({
      title: "Critical — Parallel balance tracks detected",
      body: analysis.data_quality.balance_track_ranges.length
        ? analysis.data_quality.balance_track_ranges.join(" | ")
        : "Multiple incompatible balance continuities detected.",
      severity: "critical",
    });
  }
  if (analysis.data_quality.missing_months.length) {
    cards.push({
      title: "Warning — Missing month gap",
      body: `No transactions found for: ${analysis.data_quality.missing_months.join(", ")}.`,
      severity: "warning",
    });
  }
  if (!analysis.data_quality.rent_payments_found) {
    cards.push({
      title: "Notice — No rent payments detected",
      body: "Could indicate cash rent, second account usage, or rent-free living; review manually.",
      severity: "notice",
    });
  }
  if (analysis.data_quality.utility_consistency === "inconsistent") {
    cards.push({
      title: "Notice — Utility provider inconsistency",
      body: analysis.data_quality.utility_providers.length
        ? `Detected providers: ${analysis.data_quality.utility_providers.join(", ")}.`
        : "Utility pattern indicates possible multi-location or mixed-household billing.",
      severity: "notice",
    });
  }
  if (analysis.agents.income.score < 40 && analysis.agents.income.regularity === "HIGH") {
    cards.push({
      title: "Warning — Income agent appears conservative",
      body: "Daily/near-daily payout regularity exists, but income score is still low; review model assumptions.",
      severity: "warning",
    });
  }

  return cards.slice(0, 6);
}
