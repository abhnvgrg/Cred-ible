import type {
  DataQualityAuditResult,
  ParseStatementResult,
  StoredScoreResult,
} from "@/lib/scoring";

export type WhatIfSimulationResponse = {
  base_score: number;
  projected_score: number;
  score_delta: number;
  projected_risk_level: "low" | "medium" | "high";
  confidence: "high" | "medium" | "low";
  explanation: string;
  projected_breakdown: {
    income: number;
    repayment: number;
    lifestyle: number;
    compliance: "pass" | "fail" | "review";
  };
  component_impacts: Record<string, number>;
  recommendations: Array<{
    title: string;
    impact: "high" | "medium" | "low";
    note: string;
  }>;
  processing_time_ms: number;
  disclaimer: string;
};

export type SimulationAnalysisJson = {
  data_quality: {
    score: number;
    flags: string[];
    missing_months: string[];
    parallel_balance_tracks: boolean;
    anomalous_income_months: string[];
    rent_payments_found: boolean;
    utility_consistency: "consistent" | "inconsistent";
  };
  agents: {
    income: {
      raw_monthly_avg: number;
      corrected_monthly_avg: number;
      regularity: "HIGH" | "MEDIUM" | "LOW";
      trend: "IMPROVING" | "STABLE" | "DECLINING";
      score: number;
      confidence: "HIGH" | "MEDIUM" | "LOW";
      reasoning: string;
    };
    repayment: {
      bills_found: string[];
      emis_found: boolean;
      rent_found: boolean;
      score: number;
      confidence: "HIGH" | "MEDIUM" | "LOW";
      reasoning: string;
    };
    lifestyle: {
      essential_ratio: number;
      multiple_sims: boolean;
      score: number;
      reasoning: string;
    };
  };
  conflicts: string[];
  final: {
    internal_score: number;
    credit_score: number;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    confidence: "HIGH" | "MEDIUM" | "LOW";
    compliance_penalty: number;
    recommended_loan_range_inr: { min: number; max: number };
    positive_factors: string[];
    risk_factors: string[];
    lender_notes: string;
  };
};

function toUpperConfidence(value: "high" | "medium" | "low"): "HIGH" | "MEDIUM" | "LOW" {
  if (value === "high") return "HIGH";
  if (value === "medium") return "MEDIUM";
  return "LOW";
}

function toUpperRisk(value: "low" | "medium" | "high"): "LOW" | "MEDIUM" | "HIGH" {
  if (value === "low") return "LOW";
  if (value === "medium") return "MEDIUM";
  return "HIGH";
}

function clip(value: number, lower: number, upper: number): number {
  return Math.max(lower, Math.min(upper, value));
}

function internalScoreFromCredit(score: number): number {
  return Math.round(((score - 300) / 6) * 10) / 10;
}

function recommendedLoanRange(score: number): { min: number; max: number } {
  if (score < 500) return { min: 20_000, max: 50_000 };
  if (score < 650) return { min: 50_000, max: 150_000 };
  if (score < 750) return { min: 150_000, max: 300_000 };
  return { min: 300_000, max: 600_000 };
}

function compliancePenalty(audit: DataQualityAuditResult): number {
  let penalty = 0;
  if (audit.score < 80) penalty += 2;
  penalty += Math.min(3, audit.flags.length > 0 ? Math.ceil(audit.flags.length / 3) : 0);
  return clip(penalty, 0, 5);
}

function buildConflictList(
  audit: DataQualityAuditResult,
  incomeScore: number,
  repaymentScore: number,
  lifestyleScore: number
): string[] {
  const conflicts: string[] = [];
  if (Math.abs(incomeScore - repaymentScore) >= 20) {
    const base = `Income agent scores ${incomeScore}/100 while repayment agent scores ${repaymentScore}/100. These signals conflict.`;
    if (audit.score < 70) {
      conflicts.push(
        `${base} Data quality score is ${audit.score}/100, so the conflict is surfaced to the lender rather than force-resolved.`
      );
    } else if (repaymentScore >= incomeScore) {
      conflicts.push(
        `${base} Data quality is clean enough to trust repayment behaviour more, so repayment is prioritised in lender interpretation.`
      );
    } else {
      conflicts.push(
        `${base} Data quality is acceptable, but repayment behaviour does not confirm the stronger income signal, so confidence is widened.`
      );
    }
  }
  if (Math.abs(lifestyleScore - repaymentScore) >= 25) {
    conflicts.push(
      `Lifestyle agent differs materially from repayment agent (${lifestyleScore}/100 vs ${repaymentScore}/100); spending behaviour should be reviewed alongside bill-payment consistency.`
    );
  }
  return conflicts;
}

function lenderNotes(
  audit: DataQualityAuditResult,
  analysis: SimulationAnalysisJson
): string {
  const notes: string[] = [];
  notes.push(
    `Data quality scored ${audit.score}/100 with ${audit.flags.length} audit flag(s).`
  );
  notes.push(
    `Corrected monthly income is estimated at INR ${Math.round(analysis.agents.income.corrected_monthly_avg).toLocaleString("en-IN")}, with ${analysis.agents.income.regularity.toLowerCase()} regularity and ${analysis.agents.income.trend.toLowerCase()} trend.`
  );
  notes.push(
    `Repayment evidence confirms ${audit.repayment.confirmed_payments_made} out of ${audit.repayment.expected_payments} expected monthly payments.`
  );
  if (analysis.conflicts.length) {
    notes.push(analysis.conflicts[0]);
  }
  if (audit.parallel_balance_tracks) {
    notes.push("Parallel balance tracks were detected and should be resolved before approval unless a lender overrides this exception.");
  }
  if (!audit.rent_payments_found) {
    notes.push("No rent payments were visible; this should be reviewed rather than treated as an automatic negative.");
  }
  return notes.join(" ");
}

export function buildSimulationAnalysis(
  parsedStatement: ParseStatementResult,
  scoreResult: StoredScoreResult,
  simulation: WhatIfSimulationResponse
): { json: SimulationAnalysisJson; summary: string } {
  const audit = parsedStatement.data_quality_audit;
  const incomeScore = simulation.projected_breakdown.income;
  const repaymentScore = simulation.projected_breakdown.repayment;
  const lifestyleScore = simulation.projected_breakdown.lifestyle;
  const finalConfidence = audit.score < 65 ? "LOW" : toUpperConfidence(simulation.confidence);
  const penalty = compliancePenalty(audit);
  const conflicts = buildConflictList(audit, incomeScore, repaymentScore, lifestyleScore);

  const positiveFactors = [
    ...(scoreResult.response.positive_factors ?? []),
    ...simulation.recommendations.filter((item) => item.impact !== "low").map((item) => item.title),
  ].filter((value, index, source) => source.indexOf(value) === index).slice(0, 5);

  const riskFactors = [
    ...(scoreResult.response.risk_factors ?? []),
    ...audit.flags,
  ].filter((value, index, source) => source.indexOf(value) === index).slice(0, 6);

  const json: SimulationAnalysisJson = {
    data_quality: {
      score: audit.score,
      flags: audit.flags,
      missing_months: audit.missing_months,
      parallel_balance_tracks: audit.parallel_balance_tracks,
      anomalous_income_months: audit.anomalous_income_months,
      rent_payments_found: audit.rent_payments_found,
      utility_consistency: audit.utility_consistency,
    },
    agents: {
      income: {
        raw_monthly_avg: Math.round(audit.income.raw_monthly_avg),
        corrected_monthly_avg: Math.round(audit.income.corrected_monthly_avg),
        regularity: audit.income.regularity,
        trend: audit.income.trend,
        score: incomeScore,
        confidence: audit.score < 65 ? "LOW" : audit.income.confidence,
        reasoning: `${audit.income.reasoning} Simulated income component is now ${incomeScore}/100.`,
      },
      repayment: {
        bills_found: audit.repayment.bills_found,
        emis_found: audit.repayment.emis_found,
        rent_found: audit.repayment.rent_found,
        score: repaymentScore,
        confidence: audit.score < 65 ? "LOW" : audit.repayment.confidence,
        reasoning: `${audit.repayment.reasoning} Simulated repayment component is now ${repaymentScore}/100.`,
      },
      lifestyle: {
        essential_ratio: Math.round(audit.lifestyle.essential_ratio * 1000) / 1000,
        multiple_sims: audit.lifestyle.multiple_sims,
        score: lifestyleScore,
        reasoning: `${audit.lifestyle.reasoning} Simulated lifestyle component is now ${lifestyleScore}/100.`,
      },
    },
    conflicts,
    final: {
      internal_score: internalScoreFromCredit(simulation.projected_score),
      credit_score: simulation.projected_score,
      risk_level: toUpperRisk(simulation.projected_risk_level),
      confidence: finalConfidence,
      compliance_penalty: penalty,
      recommended_loan_range_inr: recommendedLoanRange(simulation.projected_score),
      positive_factors: positiveFactors,
      risk_factors: riskFactors,
      lender_notes: "",
    },
  };

  json.final.lender_notes = lenderNotes(audit, json);

  const summary = [
    `Data quality scored ${audit.score}/100.`,
    `Corrected monthly income is about INR ${Math.round(audit.income.corrected_monthly_avg).toLocaleString("en-IN")} with ${audit.income.regularity.toLowerCase()} regularity.`,
    `The simulated credit score is ${simulation.projected_score} (${simulation.score_delta >= 0 ? "+" : ""}${simulation.score_delta}) with ${finalConfidence.toLowerCase()} confidence.`,
    conflicts[0] ?? "No major agent conflict required override logic in this simulation."
  ].join(" ");

  return { json, summary };
}
