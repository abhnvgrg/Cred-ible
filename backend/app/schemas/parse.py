from __future__ import annotations

"""
Pydantic v2 schemas for the bank statement parser module.

ParsedSignals field names are fixed by the 4-agent scoring pipeline contract
(Income Agent, Repayment Agent, Lifestyle Agent, Compliance Agent).
They must not be renamed or removed.
"""

from typing import Literal

from pydantic import BaseModel, Field


ParseEmploymentType = Literal["salaried", "freelance", "self_employed"]


class ParsedSignals(BaseModel):
    """
    The 14 derived signals expected by the downstream agent pipeline.
    All field names are contract-fixed — do not rename.
    """

    upi_monthly_txn_count: int = Field(
        ge=0,
        description="Average count of UPI narrations per month",
    )
    upi_avg_txn_value: int = Field(
        ge=0,
        description="Mean UPI credit/debit value in INR",
    )
    merchant_diversity_score: float = Field(
        ge=0, le=1,
        description="Unique merchant count / total txns, normalized 0–1",
    )
    regularity_score: float = Field(
        ge=0, le=1,
        description="1 - (std_dev(monthly_credits) / mean(monthly_credits)), clipped 0–1",
    )
    monthly_income_inr: int = Field(
        ge=0,
        description="Average monthly net credits, excluding internal transfers",
    )
    income_stability_score: float = Field(
        ge=0, le=1,
        description="Regularity of credit amounts month-over-month",
    )
    savings_rate_pct: float = Field(
        description="avg((monthly_credits - monthly_debits) / monthly_credits) × 100",
    )
    bank_balance_avg_3m: int = Field(
        description="Average closing balance over last 3 months",
    )
    debt_to_income_ratio: float = Field(
        ge=0,
        description="Estimated fixed EMI debits / monthly_income_inr",
    )
    utility_bill_ontime_pct: float = Field(
        ge=0, le=100,
        description="% of utility payments made on or before the 15th of the month",
    )
    mobile_recharge_freq: float = Field(
        ge=0,
        description="Average mobile recharges per month",
    )
    recharge_consistency_score: float = Field(
        ge=0, le=1,
        description="Regularity of recharge intervals, 0–1",
    )
    months_of_history: int = Field(
        ge=0,
        description="Number of months covered by the statement",
    )
    monthly_volume_trend_pct: float = Field(
        description="% change in transaction volume, first vs. last 3 months",
    )


class ParseRequest(BaseModel):
    """Fields submitted alongside the uploaded statement file."""

    borrower_name: str = Field(min_length=1, max_length=100)
    employment_type: ParseEmploymentType
    gst_applicable: bool
    loan_amount_requested: int = Field(ge=0, le=50_000_000)


class IncomeAuditResponse(BaseModel):
    income_type: str
    raw_monthly_avg: float = Field(ge=0)
    corrected_monthly_avg: float = Field(ge=0)
    regularity: Literal["HIGH", "MEDIUM", "LOW"]
    trend: Literal["IMPROVING", "STABLE", "DECLINING"]
    raw_score: int = Field(ge=0, le=100)
    corrected_score: int = Field(ge=0, le=100)
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str


class RepaymentAuditResponse(BaseModel):
    bills_found: list[str] = Field(default_factory=list)
    emis_found: bool
    rent_found: bool
    score: int = Field(ge=0, le=100)
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    confirmed_payments_made: int = Field(ge=0)
    expected_payments: int = Field(ge=0)
    reasoning: str


class LifestyleAuditResponse(BaseModel):
    essential_ratio: float = Field(ge=0, le=1)
    multiple_sims: bool
    score: int = Field(ge=0, le=100)
    reasoning: str


class DataQualityAuditResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    flags: list[str] = Field(default_factory=list)
    missing_months: list[str] = Field(default_factory=list)
    parallel_balance_tracks: bool = False
    balance_track_ranges: list[str] = Field(default_factory=list)
    anomalous_income_months: list[str] = Field(default_factory=list)
    raw_monthly_income_avg: float = Field(ge=0)
    corrected_monthly_income_avg: float = Field(ge=0)
    rent_payments_found: bool = False
    utility_consistency: Literal["consistent", "inconsistent"]
    utility_providers: list[str] = Field(default_factory=list)
    months_without_utility_payments: list[str] = Field(default_factory=list)
    income: IncomeAuditResponse
    repayment: RepaymentAuditResponse
    lifestyle: LifestyleAuditResponse


class ParseResponse(BaseModel):
    """Response from POST /parse/statement."""

    parsed_signals: ParsedSignals
    detected_bank: str
    statement_months: int = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1)
    low_history_warning: bool = False
    income_undetectable: bool = False
    upi_inactive: bool = False
    parser_warnings: list[str] = Field(default_factory=list)
    data_quality_audit: DataQualityAuditResponse


class ParsePersonaSet(BaseModel):
    """One demo persona's metadata + pre-computed parse response."""

    borrower_name: str
    employment_type: ParseEmploymentType
    gst_applicable: bool
    loan_amount_requested: int
    response: ParseResponse


class ParsePersonasResponse(BaseModel):
    """Response from GET /parse/personas."""

    personas: list[ParsePersonaSet]
