from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]
FraudRiskLevel = Literal["low", "medium", "high"]
EmploymentType = Literal["salaried", "freelance", "self_employed"]
IncomeProofType = Literal["salary_slip", "invoice", "bank_statement", "self_declared"]
GSTFilingFrequency = Literal["monthly", "quarterly", "not_applicable"]
ComplianceStatus = Literal["pass", "fail", "review"]


class UPISignal(BaseModel):
    transaction_frequency_per_month: int = Field(ge=0, le=2000)
    average_transaction_value_inr: float = Field(ge=0, le=1_000_000)
    merchant_diversity_score: float = Field(ge=0, le=1)
    regularity_score: float = Field(ge=0, le=1)
    months_of_history: int = Field(ge=1, le=60)
    monthly_volume_trend_pct: float = Field(ge=-100, le=300)


class GSTSignal(BaseModel):
    filing_frequency: GSTFilingFrequency
    filing_consistency_score: float = Field(ge=0, le=1)
    missed_filings_last_12m: int = Field(ge=0, le=12)
    revenue_trend_pct: float = Field(ge=-100, le=300)
    is_applicable: bool = True


class RentalSignal(BaseModel):
    rent_amount_inr: float = Field(ge=0, le=500_000)
    on_time_payment_ratio: float = Field(ge=0, le=1)
    late_payments_last_24m: int = Field(ge=0, le=24)
    tenancy_months: int = Field(ge=1, le=600)
    longest_gap_months: int = Field(ge=0, le=36)


class UtilitySignal(BaseModel):
    electricity_on_time_ratio: float = Field(ge=0, le=1)
    water_on_time_ratio: float = Field(ge=0, le=1)
    average_monthly_total_inr: float = Field(ge=0, le=200_000)
    payment_months_observed: int = Field(ge=1, le=120)


class MobileAppSignal(BaseModel):
    recharge_frequency_per_month: float = Field(ge=0, le=30)
    average_recharge_value_inr: float = Field(ge=0, le=10_000)
    consistency_score: float = Field(ge=0, le=1)
    finance_app_usage_score: float = Field(ge=0, le=1)
    risky_app_usage_score: float = Field(ge=0, le=1)
    monthly_data_usage_gb: float = Field(ge=0, le=500)


class EmploymentSignal(BaseModel):
    employment_type: EmploymentType
    monthly_income_inr: float = Field(ge=0, le=5_000_000)
    income_stability_score: float = Field(ge=0, le=1)
    months_in_current_work: int = Field(ge=0, le=480)
    income_proof_type: IncomeProofType


class BorrowerSignalInput(BaseModel):
    borrower_name: str = Field(min_length=1, max_length=100)
    upi: UPISignal
    gst: GSTSignal | None = None
    rent: RentalSignal
    mobile: MobileAppSignal
    utilities: UtilitySignal
    employment: EmploymentSignal
    existing_emi_on_time_ratio: float = Field(default=1, ge=0, le=1)
    declared_attributes: dict[str, str] = Field(default_factory=dict)

class AgentScoreOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    confidence: ConfidenceLevel
    reasoning: str = Field(min_length=10)
    flags: list[str] = Field(default_factory=list)


class ComplianceAgentOutput(BaseModel):
    rbi_compliant: bool
    fraud_risk: FraudRiskLevel
    flags: list[str] = Field(default_factory=list)
    notes: str = Field(min_length=5)


class AgentBreakdown(BaseModel):
    income: int = Field(ge=0, le=100)
    repayment: int = Field(ge=0, le=100)
    lifestyle: int = Field(ge=0, le=100)
    compliance: ComplianceStatus


class ScoreResponse(BaseModel):
    final_score: int = Field(ge=300, le=900)
    confidence: ConfidenceLevel
    explanation: str
    agent_breakdown: AgentBreakdown
    rbi_flags: list[str] = Field(default_factory=list)
    positive_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    recommended_loan_limit: str
    processing_time_ms: int = Field(ge=0)
    disclaimer: str
    agent_outputs: dict[str, AgentScoreOutput | ComplianceAgentOutput]


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    work_email: str = Field(min_length=5, max_length=254)
    organization: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    user_id: str
    full_name: str
    work_email: str
    organization: str
    role: Literal["analyst", "admin"]
    session_token: str
    expires_in_seconds: int = Field(ge=1)
    message: str


class WhatIfRequest(BaseModel):
    base_score: int = Field(ge=300, le=900)
    income_shift: int = Field(ge=0, le=20)
    compliance_boost: int = Field(ge=0, le=20)
    debt_reduction: int = Field(ge=0, le=20)


class WhatIfRecommendation(BaseModel):
    title: str
    impact: Literal["high", "medium", "low"]
    note: str


class WhatIfResponse(BaseModel):
    base_score: int = Field(ge=300, le=900)
    projected_score: int = Field(ge=300, le=900)
    score_delta: int
    confidence: ConfidenceLevel
    explanation: str
    recommendations: list[WhatIfRecommendation]
    processing_time_ms: int = Field(ge=0)
    disclaimer: str


class MarketplaceOffer(BaseModel):
    lender: str
    product_type: str
    eligible_amount_inr: int = Field(ge=20_000)
    indicative_rate_apr: float = Field(ge=7.0, le=36.0)
    tenure_months: int = Field(ge=6, le=84)
    ai_match_pct: int = Field(ge=50, le=99)
    rationale: str
    requires_additional_docs: bool = False


class MarketplaceResponse(BaseModel):
    score_used: int = Field(ge=300, le=900)
    confidence: ConfidenceLevel
    offers: list[MarketplaceOffer]
    disclaimer: str


class BorrowerProfileInput(BaseModel):
    occupation: str = Field(min_length=2, max_length=120)
    sector: str | None = Field(default=None, min_length=2, max_length=120)
    age: int = Field(ge=18, le=100)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    monthly_income_inr: float = Field(ge=0, le=5_000_000)
    years_in_business: int = Field(ge=0, le=60)
    has_gst: bool
    has_formal_rent: bool
    has_bank_account: bool


class TrainModelResponse(BaseModel):
    records_used: int = Field(ge=1)
    classes: list[str]
    metrics: dict[str, float]
    dataset_path: str
    sheets_fused: list[str]
    model_path: str
    metrics_path: str
    trained_at_utc: str


class RiskPredictionResponse(BaseModel):
    predicted_risk: Literal["low", "medium", "high"]
    class_probabilities: dict[str, float]
    model_trained_at_utc: str
