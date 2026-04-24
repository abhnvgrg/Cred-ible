export type SimSignals = {
  upi_monthly_txn_count: number;
  utility_bill_ontime_pct: number;
  savings_rate_pct: number;
  months_of_history: number;
  debt_to_income_ratio: number;
  gst_compliance_score: number;
};

export type SimResponse = {
  baseline_score: number;
  projected_score: number;
  delta: number;
  top_improvement: keyof SimSignals | "utility_bill_ontime_pct";
  explanation: string;
  agent_deltas: {
    income_agent: number;
    repayment_agent: number;
    lifestyle_agent: number;
    compliance_agent: number;
  };
  confidence: number;
};

export type PersonaBaseline = {
  id: string;
  name: string;
  gst_applicable: boolean;
  current: SimSignals;
};

export const FEATURE_COEFFICIENTS: Record<keyof SimSignals, number> = {
  utility_bill_ontime_pct: 0.45,
  savings_rate_pct: 0.38,
  upi_monthly_txn_count: 1.2,
  months_of_history: 3.5,
  debt_to_income_ratio: -85,
  gst_compliance_score: 42
};

const AGENT_SPLITS: Record<keyof SimSignals, Partial<Record<keyof SimResponse["agent_deltas"], number>>> = {
  utility_bill_ontime_pct: { repayment_agent: 0.7, lifestyle_agent: 0.2, compliance_agent: 0.1 },
  savings_rate_pct: { lifestyle_agent: 0.5, income_agent: 0.3, repayment_agent: 0.2 },
  upi_monthly_txn_count: { lifestyle_agent: 0.6, income_agent: 0.4 },
  months_of_history: { income_agent: 0.5, compliance_agent: 0.5 },
  debt_to_income_ratio: { repayment_agent: 1.0 },
  gst_compliance_score: { compliance_agent: 1.0 }
};

function clipScore(value: number): number {
  return Math.max(300, Math.min(900, Math.round(value)));
}

export function simulateScore(
  current: SimSignals,
  projected: SimSignals,
  baselineScore?: number
): SimResponse {
  const baseline = baselineScore ?? 300;
  const deltas: Record<keyof SimSignals, number> = {
    utility_bill_ontime_pct:
      (projected.utility_bill_ontime_pct - current.utility_bill_ontime_pct) *
      FEATURE_COEFFICIENTS.utility_bill_ontime_pct,
    savings_rate_pct: (projected.savings_rate_pct - current.savings_rate_pct) * FEATURE_COEFFICIENTS.savings_rate_pct,
    upi_monthly_txn_count:
      (projected.upi_monthly_txn_count - current.upi_monthly_txn_count) * FEATURE_COEFFICIENTS.upi_monthly_txn_count,
    months_of_history:
      (projected.months_of_history - current.months_of_history) * FEATURE_COEFFICIENTS.months_of_history,
    debt_to_income_ratio:
      (projected.debt_to_income_ratio - current.debt_to_income_ratio) * FEATURE_COEFFICIENTS.debt_to_income_ratio,
    gst_compliance_score:
      (projected.gst_compliance_score - current.gst_compliance_score) * FEATURE_COEFFICIENTS.gst_compliance_score
  };

  const projectedScore = clipScore(baseline + Object.values(deltas).reduce((sum, value) => sum + value, 0));
  const delta = projectedScore - baseline;

  const positiveKeys = (Object.keys(deltas) as Array<keyof SimSignals>).filter((key) => deltas[key] > 0);
  const topImprovement: keyof SimSignals | "utility_bill_ontime_pct" =
    positiveKeys.sort((a, b) => deltas[b] - deltas[a])[0] ?? "utility_bill_ontime_pct";

  const agentBuckets: SimResponse["agent_deltas"] = {
    income_agent: 0,
    repayment_agent: 0,
    lifestyle_agent: 0,
    compliance_agent: 0
  };

  (Object.keys(deltas) as Array<keyof SimSignals>).forEach((feature) => {
    const split = AGENT_SPLITS[feature];
    Object.entries(split).forEach(([agent, weight]) => {
      agentBuckets[agent as keyof SimResponse["agent_deltas"]] += deltas[feature] * (weight ?? 0);
    });
  });

  const explanation =
    topImprovement === "utility_bill_ontime_pct"
      ? "Paying utility bills on time is the single biggest improvement you can make. It drives the strongest positive score movement."
      : `${topImprovement} contributed the most to your projected score improvement.`;

  return {
    baseline_score: baseline,
    projected_score: projectedScore,
    delta,
    top_improvement: topImprovement,
    explanation,
    agent_deltas: {
      income_agent: Math.round(agentBuckets.income_agent),
      repayment_agent: Math.round(agentBuckets.repayment_agent),
      lifestyle_agent: Math.round(agentBuckets.lifestyle_agent),
      compliance_agent: Math.round(agentBuckets.compliance_agent)
    },
    confidence: 0.84
  };
}

function clip(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toDisplayName(personaId: string): string {
  const cleaned = personaId.replace(/[-_]+/g, " ").trim();
  if (!cleaned) return "Applicant";
  return cleaned
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function estimateSignalsFromScore(score: number): SimSignals {
  const normalizedScore = clipScore(score);
  return {
    upi_monthly_txn_count: Math.round(clip((normalizedScore - 300) / 3.2, 20, 260)),
    utility_bill_ontime_pct: clip(42 + (normalizedScore - 300) / 6, 35, 98),
    savings_rate_pct: clip((normalizedScore - 470) / 9, 0, 40),
    months_of_history: normalizedScore >= 760 ? 24 : normalizedScore >= 650 ? 12 : normalizedScore >= 560 ? 6 : 3,
    debt_to_income_ratio: Number(clip(0.9 - (normalizedScore - 300) / 900, 0.05, 1.2).toFixed(2)),
    gst_compliance_score: Number(clip((normalizedScore - 420) / 420, 0.1, 1).toFixed(2))
  };
}

export function getPersonaBaseline(
  personaId: string | null | undefined,
  options?: { inferredBaselineScore?: number }
): PersonaBaseline {
  const normalizedId = (personaId ?? "applicant").trim().toLowerCase() || "applicant";
  const inferredScore = clipScore(options?.inferredBaselineScore ?? 300);
  return {
    id: normalizedId,
    name: toDisplayName(normalizedId),
    gst_applicable: false,
    current: estimateSignalsFromScore(inferredScore)
  };
}

export type ParsePersonaResponse = {
  personas: Array<{
    borrower_name: string;
    gst_applicable: boolean;
    response: {
      parsed_signals: {
        upi_monthly_txn_count: number;
        utility_bill_ontime_pct: number;
        savings_rate_pct: number;
        months_of_history: number;
        debt_to_income_ratio: number;
      };
    };
  }>;
};

export function mergePersonaFromParseApi(
  baseline: PersonaBaseline,
  apiPayload: ParsePersonaResponse | null
): PersonaBaseline {
  if (!apiPayload?.personas?.length) return baseline;
  const match = apiPayload.personas.find(
    (item) => item.borrower_name.trim().toLowerCase() === baseline.name.trim().toLowerCase()
  );
  if (!match) return baseline;

  const upiCount = Number(match.response.parsed_signals.upi_monthly_txn_count);
  const utilityPct = Number(match.response.parsed_signals.utility_bill_ontime_pct);
  const savingsPct = Number(match.response.parsed_signals.savings_rate_pct);
  const historyMonths = Number(match.response.parsed_signals.months_of_history);
  const dtiRatio = Number(match.response.parsed_signals.debt_to_income_ratio);

  return {
    ...baseline,
    gst_applicable: match.gst_applicable,
    current: {
      ...baseline.current,
      upi_monthly_txn_count: Number.isFinite(upiCount) ? upiCount : baseline.current.upi_monthly_txn_count,
      utility_bill_ontime_pct: Number.isFinite(utilityPct) ? utilityPct : baseline.current.utility_bill_ontime_pct,
      savings_rate_pct: Number.isFinite(savingsPct) ? savingsPct : baseline.current.savings_rate_pct,
      months_of_history: Number.isFinite(historyMonths) ? historyMonths : baseline.current.months_of_history,
      debt_to_income_ratio: Number.isFinite(dtiRatio) ? dtiRatio : baseline.current.debt_to_income_ratio
    }
  };
}
