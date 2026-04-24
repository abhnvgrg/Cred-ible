export type ConfidenceLevel = "high" | "medium" | "low";
export type FraudRiskLevel = "low" | "medium" | "high";
export type EmploymentType = "salaried" | "freelance" | "self_employed";
export type IncomeProofType = "salary_slip" | "invoice" | "bank_statement" | "self_declared";
export type GSTFilingFrequency = "monthly" | "quarterly" | "not_applicable";
export type ComplianceStatus = "pass" | "fail" | "review";

export interface UPISignal {
  transaction_frequency_per_month: number;
  average_transaction_value_inr: number;
  merchant_diversity_score: number;
  regularity_score: number;
  months_of_history: number;
  monthly_volume_trend_pct: number;
}

export interface GSTSignal {
  filing_frequency: GSTFilingFrequency;
  filing_consistency_score: number;
  missed_filings_last_12m: number;
  revenue_trend_pct: number;
  is_applicable: boolean;
}

export interface RentalSignal {
  rent_amount_inr: number;
  on_time_payment_ratio: number;
  late_payments_last_24m: number;
  tenancy_months: number;
  longest_gap_months: number;
}

export interface UtilitySignal {
  electricity_on_time_ratio: number;
  water_on_time_ratio: number;
  average_monthly_total_inr: number;
  payment_months_observed: number;
}

export interface MobileAppSignal {
  recharge_frequency_per_month: number;
  average_recharge_value_inr: number;
  consistency_score: number;
  finance_app_usage_score: number;
  risky_app_usage_score: number;
  monthly_data_usage_gb: number;
}

export interface EmploymentSignal {
  employment_type: EmploymentType;
  monthly_income_inr: number;
  income_stability_score: number;
  months_in_current_work: number;
  income_proof_type: IncomeProofType;
}

export interface BorrowerSignalInput {
  borrower_name: string;
  upi: UPISignal;
  gst: GSTSignal | null;
  rent: RentalSignal;
  mobile: MobileAppSignal;
  utilities: UtilitySignal;
  employment: EmploymentSignal;
  existing_emi_on_time_ratio: number;
  declared_attributes: Record<string, string>;
}

export interface AgentScoreOutput {
  score: number;
  confidence: ConfidenceLevel;
  reasoning: string;
  flags: string[];
}

export interface ComplianceAgentOutput {
  rbi_compliant: boolean;
  fraud_risk: FraudRiskLevel;
  flags: string[];
  notes: string;
}

export interface AgentBreakdown {
  income: number;
  repayment: number;
  lifestyle: number;
  compliance: ComplianceStatus;
}

export interface ScoreResponse {
  final_score: number;
  risk_level?: FraudRiskLevel;
  confidence: ConfidenceLevel;
  explanation: string;
  agent_breakdown: AgentBreakdown;
  component_weights?: Record<string, number>;
  component_contributions?: Record<string, number>;
  rbi_flags: string[];
  positive_factors?: string[];
  risk_factors?: string[];
  recommended_loan_limit: string;
  processing_time_ms: number;
  disclaimer: string;
  agent_outputs: Record<string, AgentScoreOutput | ComplianceAgentOutput>;
}

export interface StoredScoreResult {
  response: ScoreResponse;
  source: "intake" | "persona";
  persona: string | null;
  borrowerName: string;
  generatedAt: string;
  fallbackUsed?: boolean;
  fallbackReason?: string | null;
}

export interface IncomeAuditResult {
  income_type: string;
  raw_monthly_avg: number;
  corrected_monthly_avg: number;
  regularity: "HIGH" | "MEDIUM" | "LOW";
  trend: "IMPROVING" | "STABLE" | "DECLINING";
  raw_score: number;
  corrected_score: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  reasoning: string;
}

export interface RepaymentAuditResult {
  bills_found: string[];
  emis_found: boolean;
  rent_found: boolean;
  score: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  confirmed_payments_made: number;
  expected_payments: number;
  reasoning: string;
}

export interface LifestyleAuditResult {
  essential_ratio: number;
  multiple_sims: boolean;
  score: number;
  reasoning: string;
}

export interface DataQualityAuditResult {
  score: number;
  flags: string[];
  missing_months: string[];
  parallel_balance_tracks: boolean;
  balance_track_ranges: string[];
  anomalous_income_months: string[];
  raw_monthly_income_avg: number;
  corrected_monthly_income_avg: number;
  rent_payments_found: boolean;
  utility_consistency: "consistent" | "inconsistent";
  utility_providers: string[];
  months_without_utility_payments: string[];
  income: IncomeAuditResult;
  repayment: RepaymentAuditResult;
  lifestyle: LifestyleAuditResult;
}

export interface ParseStatementResult {
  parsed_signals: {
    upi_monthly_txn_count: number;
    upi_avg_txn_value: number;
    merchant_diversity_score: number;
    regularity_score: number;
    monthly_income_inr: number;
    income_stability_score: number;
    savings_rate_pct: number;
    bank_balance_avg_3m: number;
    debt_to_income_ratio: number;
    utility_bill_ontime_pct: number;
    mobile_recharge_freq: number;
    recharge_consistency_score: number;
    months_of_history: number;
    monthly_volume_trend_pct: number;
  };
  detected_bank: string;
  statement_months: number;
  confidence_score: number;
  low_history_warning: boolean;
  income_undetectable: boolean;
  upi_inactive: boolean;
  parser_warnings: string[];
  data_quality_audit: DataQualityAuditResult;
}

const INTAKE_PAYLOAD_KEY = "cred-ible:intake-payload:v1";
const SCORE_RESULT_KEY = "cred-ible:score-result:v1";
const PARSED_STATEMENT_KEY = "cred-ible:parsed-statement:v1";

function setSessionStorageValue(key: string, value: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    window.sessionStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function getSessionStorageValue(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function removeSessionStorageValue(key: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    return;
  }
}

function parseJson(value: string | null): unknown {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isConfidenceLevel(value: unknown): value is ConfidenceLevel {
  return value === "high" || value === "medium" || value === "low";
}

function isFraudRiskLevel(value: unknown): value is FraudRiskLevel {
  return value === "low" || value === "medium" || value === "high";
}

function isComplianceStatus(value: unknown): value is ComplianceStatus {
  return value === "pass" || value === "fail" || value === "review";
}

function isAgentScoreOutputValue(value: unknown): value is AgentScoreOutput {
  if (!isRecord(value)) return false;
  return (
    typeof value.score === "number" &&
    isConfidenceLevel(value.confidence) &&
    typeof value.reasoning === "string" &&
    Array.isArray(value.flags) &&
    value.flags.every((flag) => typeof flag === "string")
  );
}

function isComplianceAgentOutputValue(value: unknown): value is ComplianceAgentOutput {
  if (!isRecord(value)) return false;
  return (
    typeof value.rbi_compliant === "boolean" &&
    isFraudRiskLevel(value.fraud_risk) &&
    Array.isArray(value.flags) &&
    value.flags.every((flag) => typeof flag === "string") &&
    typeof value.notes === "string"
  );
}

function isAgentOutputValue(value: unknown): value is AgentScoreOutput | ComplianceAgentOutput {
  return isAgentScoreOutputValue(value) || isComplianceAgentOutputValue(value);
}

function isAgentBreakdownValue(value: unknown): value is AgentBreakdown {
  if (!isRecord(value)) return false;
  return (
    typeof value.income === "number" &&
    typeof value.repayment === "number" &&
    typeof value.lifestyle === "number" &&
    isComplianceStatus(value.compliance)
  );
}

function isScoreResponseValue(value: unknown): value is ScoreResponse {
  if (!isRecord(value)) return false;
  const hasValidRiskLevel = value.risk_level === undefined || isFraudRiskLevel(value.risk_level);
  const hasValidComponentWeights =
    value.component_weights === undefined ||
    (isRecord(value.component_weights) &&
      Object.values(value.component_weights).every((weight) => typeof weight === "number"));
  const hasValidComponentContributions =
    value.component_contributions === undefined ||
    (isRecord(value.component_contributions) &&
      Object.values(value.component_contributions).every((contribution) => typeof contribution === "number"));
  const hasValidPositiveFactors =
    value.positive_factors === undefined ||
    (Array.isArray(value.positive_factors) &&
      value.positive_factors.every((factor) => typeof factor === "string"));
  const hasValidRiskFactors =
    value.risk_factors === undefined ||
    (Array.isArray(value.risk_factors) &&
      value.risk_factors.every((factor) => typeof factor === "string"));

  if (
    typeof value.final_score !== "number" ||
    !hasValidRiskLevel ||
    !isConfidenceLevel(value.confidence) ||
    typeof value.explanation !== "string" ||
    !isAgentBreakdownValue(value.agent_breakdown) ||
    !hasValidComponentWeights ||
    !hasValidComponentContributions ||
    !Array.isArray(value.rbi_flags) ||
    !value.rbi_flags.every((flag) => typeof flag === "string") ||
    !hasValidPositiveFactors ||
    !hasValidRiskFactors ||
    typeof value.recommended_loan_limit !== "string" ||
    typeof value.processing_time_ms !== "number" ||
    typeof value.disclaimer !== "string" ||
    !isRecord(value.agent_outputs)
  ) {
    return false;
  }

  return Object.values(value.agent_outputs).every(isAgentOutputValue);
}

function isBorrowerSignalInputValue(value: unknown): value is BorrowerSignalInput {
  if (!isRecord(value)) return false;
  const hasRequiredNestedObjects =
    isRecord(value.upi) &&
    (value.gst === null || value.gst === undefined || isRecord(value.gst)) &&
    isRecord(value.rent) &&
    isRecord(value.mobile) &&
    isRecord(value.utilities) &&
    isRecord(value.employment);

  return (
    typeof value.borrower_name === "string" &&
    typeof value.existing_emi_on_time_ratio === "number" &&
    hasRequiredNestedObjects &&
    isRecord(value.declared_attributes)
  );
}

function isStoredScoreResultValue(value: unknown): value is StoredScoreResult {
  if (!isRecord(value)) return false;

  return (
    isScoreResponseValue(value.response) &&
    (value.source === "intake" || value.source === "persona") &&
    (typeof value.persona === "string" || value.persona === null) &&
    typeof value.borrowerName === "string" &&
    typeof value.generatedAt === "string" &&
    (value.fallbackUsed === undefined || typeof value.fallbackUsed === "boolean") &&
    (value.fallbackReason === undefined ||
      value.fallbackReason === null ||
      typeof value.fallbackReason === "string")
  );
}

export function saveIntakePayload(payload: BorrowerSignalInput): boolean {
  return setSessionStorageValue(INTAKE_PAYLOAD_KEY, JSON.stringify(payload));
}

export function loadIntakePayload(): BorrowerSignalInput | null {
  const parsed = parseJson(getSessionStorageValue(INTAKE_PAYLOAD_KEY));
  return isBorrowerSignalInputValue(parsed) ? parsed : null;
}

export function clearIntakePayload(): void {
  removeSessionStorageValue(INTAKE_PAYLOAD_KEY);
}

export function saveScoreResult(result: StoredScoreResult): boolean {
  return setSessionStorageValue(SCORE_RESULT_KEY, JSON.stringify(result));
}

export function loadScoreResult(): StoredScoreResult | null {
  const parsed = parseJson(getSessionStorageValue(SCORE_RESULT_KEY));
  return isStoredScoreResultValue(parsed) ? parsed : null;
}

export function clearScoreResult(): void {
  removeSessionStorageValue(SCORE_RESULT_KEY);
}

function isUpperConfidence(value: unknown): value is "HIGH" | "MEDIUM" | "LOW" {
  return value === "HIGH" || value === "MEDIUM" || value === "LOW";
}

function isIncomeAuditResult(value: unknown): value is IncomeAuditResult {
  if (!isRecord(value)) return false;
  return (
    typeof value.income_type === "string" &&
    typeof value.raw_monthly_avg === "number" &&
    typeof value.corrected_monthly_avg === "number" &&
    isUpperConfidence(value.regularity) &&
    (value.trend === "IMPROVING" || value.trend === "STABLE" || value.trend === "DECLINING") &&
    typeof value.raw_score === "number" &&
    typeof value.corrected_score === "number" &&
    isUpperConfidence(value.confidence) &&
    typeof value.reasoning === "string"
  );
}

function isRepaymentAuditResult(value: unknown): value is RepaymentAuditResult {
  if (!isRecord(value)) return false;
  return (
    Array.isArray(value.bills_found) &&
    value.bills_found.every((item) => typeof item === "string") &&
    typeof value.emis_found === "boolean" &&
    typeof value.rent_found === "boolean" &&
    typeof value.score === "number" &&
    isUpperConfidence(value.confidence) &&
    typeof value.confirmed_payments_made === "number" &&
    typeof value.expected_payments === "number" &&
    typeof value.reasoning === "string"
  );
}

function isLifestyleAuditResult(value: unknown): value is LifestyleAuditResult {
  if (!isRecord(value)) return false;
  return (
    typeof value.essential_ratio === "number" &&
    typeof value.multiple_sims === "boolean" &&
    typeof value.score === "number" &&
    typeof value.reasoning === "string"
  );
}

function isDataQualityAuditResult(value: unknown): value is DataQualityAuditResult {
  if (!isRecord(value)) return false;
  return (
    typeof value.score === "number" &&
    Array.isArray(value.flags) &&
    value.flags.every((item) => typeof item === "string") &&
    Array.isArray(value.missing_months) &&
    value.missing_months.every((item) => typeof item === "string") &&
    typeof value.parallel_balance_tracks === "boolean" &&
    Array.isArray(value.balance_track_ranges) &&
    value.balance_track_ranges.every((item) => typeof item === "string") &&
    Array.isArray(value.anomalous_income_months) &&
    value.anomalous_income_months.every((item) => typeof item === "string") &&
    typeof value.raw_monthly_income_avg === "number" &&
    typeof value.corrected_monthly_income_avg === "number" &&
    typeof value.rent_payments_found === "boolean" &&
    (value.utility_consistency === "consistent" || value.utility_consistency === "inconsistent") &&
    Array.isArray(value.utility_providers) &&
    value.utility_providers.every((item) => typeof item === "string") &&
    Array.isArray(value.months_without_utility_payments) &&
    value.months_without_utility_payments.every((item) => typeof item === "string") &&
    isIncomeAuditResult(value.income) &&
    isRepaymentAuditResult(value.repayment) &&
    isLifestyleAuditResult(value.lifestyle)
  );
}

function isParseStatementResult(value: unknown): value is ParseStatementResult {
  if (!isRecord(value)) return false;
  return (
    isRecord(value.parsed_signals) &&
    typeof value.detected_bank === "string" &&
    typeof value.statement_months === "number" &&
    typeof value.confidence_score === "number" &&
    typeof value.low_history_warning === "boolean" &&
    typeof value.income_undetectable === "boolean" &&
    typeof value.upi_inactive === "boolean" &&
    Array.isArray(value.parser_warnings) &&
    value.parser_warnings.every((item) => typeof item === "string") &&
    isDataQualityAuditResult(value.data_quality_audit)
  );
}

export function saveParsedStatementResult(result: ParseStatementResult): boolean {
  return setSessionStorageValue(PARSED_STATEMENT_KEY, JSON.stringify(result));
}

export function loadParsedStatementResult(): ParseStatementResult | null {
  const parsed = parseJson(getSessionStorageValue(PARSED_STATEMENT_KEY));
  return isParseStatementResult(parsed) ? parsed : null;
}

export function clearParsedStatementResult(): void {
  removeSessionStorageValue(PARSED_STATEMENT_KEY);
}

export function isComplianceAgentOutput(
  output: AgentScoreOutput | ComplianceAgentOutput
): output is ComplianceAgentOutput {
  return "rbi_compliant" in output;
}
