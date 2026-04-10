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
  confidence: ConfidenceLevel;
  explanation: string;
  agent_breakdown: AgentBreakdown;
  rbi_flags: string[];
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

const INTAKE_PAYLOAD_KEY = "bharatcredit:intake-payload:v1";
const SCORE_RESULT_KEY = "bharatcredit:score-result:v1";

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
  if (
    typeof value.final_score !== "number" ||
    !isConfidenceLevel(value.confidence) ||
    typeof value.explanation !== "string" ||
    !isAgentBreakdownValue(value.agent_breakdown) ||
    !Array.isArray(value.rbi_flags) ||
    !value.rbi_flags.every((flag) => typeof flag === "string") ||
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

export function isComplianceAgentOutput(
  output: AgentScoreOutput | ComplianceAgentOutput
): output is ComplianceAgentOutput {
  return "rbi_compliant" in output;
}
