import type {
  AgentScoreOutput,
  BorrowerSignalInput,
  ComplianceAgentOutput,
  ConfidenceLevel,
  ScoreResponse
} from "@/lib/scoring";

const CONFIDENCE_WEIGHT: Record<ConfidenceLevel, number> = {
  high: 1,
  medium: 0.7,
  low: 0.4
};

const PROHIBITED_SIGNALS = new Set(["religion", "caste", "gender", "political_affiliation"]);
const OFFLINE_DISCLAIMER =
  "Offline fallback estimate generated in the frontend because live scoring was unavailable.";

const OFFLINE_PERSONA_PAYLOADS: Record<string, BorrowerSignalInput> = {
  raju: {
    borrower_name: "Raju",
    upi: {
      transaction_frequency_per_month: 180,
      average_transaction_value_inr: 450,
      merchant_diversity_score: 0.74,
      regularity_score: 0.88,
      months_of_history: 14,
      monthly_volume_trend_pct: 8
    },
    gst: {
      filing_frequency: "not_applicable",
      filing_consistency_score: 0,
      missed_filings_last_12m: 0,
      revenue_trend_pct: 0,
      is_applicable: false
    },
    rent: {
      rent_amount_inr: 6500,
      on_time_payment_ratio: 0.98,
      late_payments_last_24m: 0,
      tenancy_months: 36,
      longest_gap_months: 0
    },
    mobile: {
      recharge_frequency_per_month: 1,
      average_recharge_value_inr: 299,
      consistency_score: 0.91,
      finance_app_usage_score: 0.86,
      risky_app_usage_score: 0.08,
      monthly_data_usage_gb: 18
    },
    utilities: {
      electricity_on_time_ratio: 0.94,
      water_on_time_ratio: 0.92,
      average_monthly_total_inr: 2100,
      payment_months_observed: 24
    },
    employment: {
      employment_type: "self_employed",
      monthly_income_inr: 32000,
      income_stability_score: 0.78,
      months_in_current_work: 120,
      income_proof_type: "bank_statement"
    },
    existing_emi_on_time_ratio: 1,
    declared_attributes: {}
  },
  priya: {
    borrower_name: "Priya",
    upi: {
      transaction_frequency_per_month: 40,
      average_transaction_value_inr: 3200,
      merchant_diversity_score: 0.63,
      regularity_score: 0.52,
      months_of_history: 12,
      monthly_volume_trend_pct: 3
    },
    gst: {
      filing_frequency: "quarterly",
      filing_consistency_score: 0.72,
      missed_filings_last_12m: 1,
      revenue_trend_pct: 5,
      is_applicable: true
    },
    rent: {
      rent_amount_inr: 18000,
      on_time_payment_ratio: 0.91,
      late_payments_last_24m: 2,
      tenancy_months: 24,
      longest_gap_months: 0
    },
    mobile: {
      recharge_frequency_per_month: 0.9,
      average_recharge_value_inr: 449,
      consistency_score: 0.77,
      finance_app_usage_score: 0.88,
      risky_app_usage_score: 0.12,
      monthly_data_usage_gb: 26
    },
    utilities: {
      electricity_on_time_ratio: 0.96,
      water_on_time_ratio: 0.94,
      average_monthly_total_inr: 3500,
      payment_months_observed: 24
    },
    employment: {
      employment_type: "freelance",
      monthly_income_inr: 68000,
      income_stability_score: 0.58,
      months_in_current_work: 48,
      income_proof_type: "invoice"
    },
    existing_emi_on_time_ratio: 0.98,
    declared_attributes: {}
  },
  mohammed: {
    borrower_name: "Mohammed",
    upi: {
      transaction_frequency_per_month: 95,
      average_transaction_value_inr: 1100,
      merchant_diversity_score: 0.69,
      regularity_score: 0.75,
      months_of_history: 18,
      monthly_volume_trend_pct: 6
    },
    gst: {
      filing_frequency: "monthly",
      filing_consistency_score: 0.95,
      missed_filings_last_12m: 0,
      revenue_trend_pct: 7,
      is_applicable: true
    },
    rent: {
      rent_amount_inr: 12000,
      on_time_payment_ratio: 0.83,
      late_payments_last_24m: 1,
      tenancy_months: 60,
      longest_gap_months: 3
    },
    mobile: {
      recharge_frequency_per_month: 1.6,
      average_recharge_value_inr: 499,
      consistency_score: 0.82,
      finance_app_usage_score: 0.84,
      risky_app_usage_score: 0.18,
      monthly_data_usage_gb: 32
    },
    utilities: {
      electricity_on_time_ratio: 0.88,
      water_on_time_ratio: 0.9,
      average_monthly_total_inr: 4300,
      payment_months_observed: 24
    },
    employment: {
      employment_type: "self_employed",
      monthly_income_inr: 95000,
      income_stability_score: 0.72,
      months_in_current_work: 132,
      income_proof_type: "bank_statement"
    },
    existing_emi_on_time_ratio: 0.9,
    declared_attributes: {}
  }
};

function clampScore(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score)));
}

function confidenceFromQuality(dataQuality: number): ConfidenceLevel {
  if (dataQuality >= 0.75) return "high";
  if (dataQuality >= 0.45) return "medium";
  return "low";
}

function runIncomeAgent(payload: BorrowerSignalInput): AgentScoreOutput {
  const { upi, gst, employment } = payload;
  let score = 40;
  score += Math.min(20, upi.transaction_frequency_per_month / 12);
  score += upi.regularity_score * 15;
  score += upi.merchant_diversity_score * 5;
  score += employment.income_stability_score * 15;
  score += Math.min(10, employment.months_in_current_work / 12);

  const flags: string[] = [];
  if (upi.monthly_volume_trend_pct < -10) {
    score -= 6;
    flags.push("UPI transaction volume trend is declining");
  }
  if (employment.income_proof_type === "self_declared") {
    score -= 8;
    flags.push("Income proof is self-declared");
  }
  if (gst && gst.is_applicable) {
    score += gst.filing_consistency_score * 8;
    score -= gst.missed_filings_last_12m * 2;
    if (gst.revenue_trend_pct < -10) {
      score -= 4;
      flags.push("GST-reported revenue trend is negative");
    }
  }

  const quality =
    Math.min(1, upi.months_of_history / 12) * 0.45 +
    employment.income_stability_score * 0.35 +
    (employment.income_proof_type !== "self_declared" ? 0.2 : 0.05);

  return {
    score: clampScore(score),
    confidence: confidenceFromQuality(quality),
    reasoning:
      "Income stability was assessed using UPI regularity, work continuity, and available income proof. A stronger and more stable transaction pattern over time improved this score.",
    flags
  };
}

function runRepaymentAgent(payload: BorrowerSignalInput): AgentScoreOutput {
  const { rent, utilities, existing_emi_on_time_ratio } = payload;
  let score = 35;
  score += rent.on_time_payment_ratio * 35;
  score += ((utilities.electricity_on_time_ratio + utilities.water_on_time_ratio) / 2) * 20;
  score += existing_emi_on_time_ratio * 10;
  score += Math.min(10, rent.tenancy_months / 24);
  score -= rent.longest_gap_months * 4;
  score -= rent.late_payments_last_24m * 1.5;

  const flags: string[] = [];
  if (rent.longest_gap_months >= 2) {
    flags.push(`Rental payment gap of ${rent.longest_gap_months} month(s) observed`);
  }
  if (rent.late_payments_last_24m > 0) {
    flags.push(`${rent.late_payments_last_24m} late rent payment(s) in 24 months`);
  }
  if (existing_emi_on_time_ratio < 0.85) {
    flags.push("Existing EMI repayment ratio is below preferred threshold");
  }

  const quality =
    rent.on_time_payment_ratio * 0.45 +
    ((utilities.electricity_on_time_ratio + utilities.water_on_time_ratio) / 2) * 0.35 +
    Math.min(1, utilities.payment_months_observed / 24) * 0.2;

  return {
    score: clampScore(score),
    confidence: confidenceFromQuality(quality),
    reasoning:
      "Repayment behavior was inferred from rent and utility bill discipline. High on-time payment consistency improved the score, while payment gaps or late events reduced it.",
    flags
  };
}

function runLifestyleAgent(payload: BorrowerSignalInput): AgentScoreOutput {
  const { mobile, upi } = payload;
  let score = 45;
  score += mobile.consistency_score * 20;
  score += mobile.finance_app_usage_score * 20;
  score -= mobile.risky_app_usage_score * 25;
  score += Math.min(10, upi.merchant_diversity_score * 10);
  score += Math.min(8, mobile.recharge_frequency_per_month * 1.2);

  const flags: string[] = [];
  if (mobile.risky_app_usage_score > 0.5) {
    flags.push("Elevated risky app usage pattern detected");
  }
  if (mobile.consistency_score < 0.4) {
    flags.push("Mobile recharge behavior appears inconsistent");
  }

  const quality =
    mobile.consistency_score * 0.45 +
    mobile.finance_app_usage_score * 0.35 +
    (1 - mobile.risky_app_usage_score) * 0.2;

  return {
    score: clampScore(score),
    confidence: confidenceFromQuality(quality),
    reasoning:
      "Lifestyle risk considered recharge consistency, app usage quality, and spending diversity. Financial app engagement generally improved this score, while risky usage patterns reduced it.",
    flags
  };
}

function runComplianceAgent(payload: BorrowerSignalInput): ComplianceAgentOutput {
  const flags: string[] = [];
  const sensitiveKeys = new Set(
    Object.keys(payload.declared_attributes).map((key) => key.trim().toLowerCase())
  );
  const prohibitedFound = [...sensitiveKeys].filter((key) => PROHIBITED_SIGNALS.has(key)).sort();
  if (prohibitedFound.length) {
    flags.push(`Prohibited sensitive attributes present in input: ${prohibitedFound.join(", ")}`);
  }
  if (payload.employment.monthly_income_inr > 300000 && payload.upi.average_transaction_value_inr < 200) {
    flags.push("Declared income appears inconsistent with transaction behavior");
  }
  if (payload.gst && payload.gst.is_applicable && payload.gst.missed_filings_last_12m >= 4) {
    flags.push("High GST filing irregularity detected");
  }
  if (payload.rent.longest_gap_months >= 4 && payload.utilities.electricity_on_time_ratio < 0.6) {
    flags.push("Multiple repayment stress indicators detected");
  }

  const fraudRisk = prohibitedFound.length || flags.length >= 3 ? "high" : flags.length ? "medium" : "low";
  return {
    rbi_compliant: prohibitedFound.length === 0,
    fraud_risk: fraudRisk,
    flags,
    notes:
      "Compliance checks evaluate signal consistency and RBI-sensitive attribute violations. Any sensitive-attribute usage triggers non-compliance."
  };
}

function scaleToCreditBand(score0To100: number): number {
  const scaled = Math.round(300 + Math.max(0, Math.min(100, score0To100)) * 6);
  return Math.max(300, Math.min(900, scaled));
}

function loanLimitFromScore(finalScore: number): string {
  if (finalScore < 500) return "₹20,000 - ₹50,000";
  if (finalScore < 650) return "₹50,000 - ₹1,50,000";
  if (finalScore < 750) return "₹1,50,000 - ₹3,00,000";
  return "₹3,00,000 - ₹6,00,000";
}

function baseConfidence(scores: AgentScoreOutput[]): ConfidenceLevel {
  const avgWeight = scores.reduce((sum, score) => sum + CONFIDENCE_WEIGHT[score.confidence], 0) / scores.length;
  if (avgWeight >= 0.85) return "high";
  if (avgWeight >= 0.6) return "medium";
  return "low";
}

function incomeReliability(payload: BorrowerSignalInput, income: AgentScoreOutput): number {
  const proofBonus = payload.employment.income_proof_type !== "self_declared" ? 0.2 : 0.05;
  const historyBonus = Math.min(0.25, payload.upi.months_of_history / 48);
  return CONFIDENCE_WEIGHT[income.confidence] + proofBonus + historyBonus;
}

function repaymentReliability(payload: BorrowerSignalInput, repayment: AgentScoreOutput): number {
  const paymentQuality =
    payload.rent.on_time_payment_ratio * 0.6 +
    ((payload.utilities.electricity_on_time_ratio + payload.utilities.water_on_time_ratio) / 2) * 0.4;
  return CONFIDENCE_WEIGHT[repayment.confidence] + paymentQuality * 0.4;
}

function lifestyleReliability(payload: BorrowerSignalInput, lifestyle: AgentScoreOutput): number {
  const behaviorQuality =
    payload.mobile.consistency_score * 0.5 +
    payload.mobile.finance_app_usage_score * 0.35 +
    (1 - payload.mobile.risky_app_usage_score) * 0.15;
  return CONFIDENCE_WEIGHT[lifestyle.confidence] + behaviorQuality * 0.25;
}

export function scoreBorrowerOffline(
  payload: BorrowerSignalInput,
  options?: { processingTimeMs?: number }
): ScoreResponse {
  const processingTimeMs = options?.processingTimeMs ?? 900;
  const income = runIncomeAgent(payload);
  const repayment = runRepaymentAgent(payload);
  const lifestyle = runLifestyleAgent(payload);
  const compliance = runComplianceAgent(payload);
  const scoringAgents = [income, repayment, lifestyle];

  const weightedNumerator = scoringAgents.reduce(
    (sum, score) => sum + score.score * CONFIDENCE_WEIGHT[score.confidence],
    0
  );
  const weightedDenominator = scoringAgents.reduce((sum, score) => sum + CONFIDENCE_WEIGHT[score.confidence], 0);
  const weightedAverage = weightedNumerator / Math.max(weightedDenominator, 1e-6);

  const scoreValues = scoringAgents.map((score) => score.score);
  const spread = Math.max(...scoreValues) - Math.min(...scoreValues);
  const conflictDetected = spread >= 25;
  let finalInternal = weightedAverage;
  let conflictExplanation = `Agent outputs were reasonably aligned (spread ${spread} points), so confidence-weighted averaging was used.`;

  if (conflictDetected) {
    const reliabilityScores = {
      income: incomeReliability(payload, income),
      repayment: repaymentReliability(payload, repayment),
      lifestyle: lifestyleReliability(payload, lifestyle)
    };
    const mostReliableSignal = Object.entries(reliabilityScores).sort((a, b) => b[1] - a[1])[0]?.[0] as
      | "income"
      | "repayment"
      | "lifestyle";
    const mostReliableScore =
      mostReliableSignal === "income" ? income.score : mostReliableSignal === "repayment" ? repayment.score : lifestyle.score;
    finalInternal = weightedAverage * 0.6 + mostReliableScore * 0.4;
    conflictExplanation = `Agent outputs showed divergence (spread ${spread} points), so the resolver prioritized the ${mostReliableSignal} signal due to stronger reliability indicators.`;
  }

  let confidence = baseConfidence(scoringAgents);
  const rbiFlags = [...compliance.flags];

  if (compliance.fraud_risk === "high") {
    finalInternal -= 15;
    confidence = "low";
    rbiFlags.push("High fraud-risk pattern detected");
  } else if (compliance.fraud_risk === "medium") {
    finalInternal -= 7;
  }

  if (!compliance.rbi_compliant) {
    confidence = "low";
    rbiFlags.push("Potential RBI non-compliance in submitted attributes");
  }

  const finalScore = scaleToCreditBand(finalInternal);

  return {
    final_score: finalScore,
    confidence,
    explanation: `Income score is ${income.score}, repayment score is ${repayment.score}, and lifestyle score is ${lifestyle.score}. ${conflictExplanation} ${income.reasoning} ${repayment.reasoning} Overall borrower risk is ${
      finalScore >= 650 ? "moderate-low" : finalScore >= 550 ? "moderate" : "elevated"
    }.`,
    agent_breakdown: {
      income: income.score,
      repayment: repayment.score,
      lifestyle: lifestyle.score,
      compliance: compliance.rbi_compliant && compliance.fraud_risk !== "high" ? "pass" : "review"
    },
    rbi_flags: rbiFlags,
    recommended_loan_limit: loanLimitFromScore(finalScore),
    processing_time_ms: processingTimeMs,
    disclaimer: OFFLINE_DISCLAIMER,
    agent_outputs: {
      income,
      repayment,
      lifestyle,
      compliance
    }
  };
}

export function loadOfflinePersonaPayload(personaId: string): BorrowerSignalInput | null {
  const payload = OFFLINE_PERSONA_PAYLOADS[personaId.trim().toLowerCase()];
  if (!payload) return null;
  return JSON.parse(JSON.stringify(payload)) as BorrowerSignalInput;
}
