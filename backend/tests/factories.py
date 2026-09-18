from __future__ import annotations

from typing import Any

from app.schemas import (
    AgentScoreOutput,
    BorrowerSignalInput,
    ComplianceAgentOutput,
)

STRONG = {
    "borrower_name": "Strong Borrower",
    "upi": {
        "transaction_frequency_per_month": 180,
        "average_transaction_value_inr": 2400.0,
        "merchant_diversity_score": 0.85,
        "regularity_score": 0.92,
        "months_of_history": 30,
        "monthly_volume_trend_pct": 12.0,
    },
    "gst": {
        "filing_frequency": "monthly",
        "filing_consistency_score": 0.95,
        "missed_filings_last_12m": 0,
        "revenue_trend_pct": 18.0,
        "is_applicable": True,
    },
    "rent": {
        "rent_amount_inr": 18000.0,
        "on_time_payment_ratio": 0.98,
        "late_payments_last_24m": 0,
        "tenancy_months": 36,
        "longest_gap_months": 0,
    },
    "mobile": {
        "recharge_frequency_per_month": 1.0,
        "average_recharge_value_inr": 599.0,
        "consistency_score": 0.93,
        "finance_app_usage_score": 0.8,
        "risky_app_usage_score": 0.02,
        "monthly_data_usage_gb": 40.0,
    },
    "utilities": {
        "electricity_on_time_ratio": 0.98,
        "water_on_time_ratio": 0.97,
        "average_monthly_total_inr": 2400.0,
        "payment_months_observed": 30,
    },
    "employment": {
        "employment_type": "salaried",
        "monthly_income_inr": 95000.0,
        "income_stability_score": 0.94,
        "months_in_current_work": 48,
        "income_proof_type": "salary_slip",
    },
    "existing_emi_on_time_ratio": 1.0,
    "declared_attributes": {},
}

WEAK = {
    "borrower_name": "Weak Borrower",
    "upi": {
        "transaction_frequency_per_month": 12,
        "average_transaction_value_inr": 180.0,
        "merchant_diversity_score": 0.1,
        "regularity_score": 0.15,
        "months_of_history": 3,
        "monthly_volume_trend_pct": -45.0,
    },
    "gst": {
        "filing_frequency": "quarterly",
        "filing_consistency_score": 0.2,
        "missed_filings_last_12m": 7,
        "revenue_trend_pct": -40.0,
        "is_applicable": True,
    },
    "rent": {
        "rent_amount_inr": 9000.0,
        "on_time_payment_ratio": 0.35,
        "late_payments_last_24m": 14,
        "tenancy_months": 6,
        "longest_gap_months": 5,
    },
    "mobile": {
        "recharge_frequency_per_month": 6.0,
        "average_recharge_value_inr": 49.0,
        "consistency_score": 0.2,
        "finance_app_usage_score": 0.05,
        "risky_app_usage_score": 0.85,
        "monthly_data_usage_gb": 2.0,
    },
    "utilities": {
        "electricity_on_time_ratio": 0.4,
        "water_on_time_ratio": 0.35,
        "average_monthly_total_inr": 900.0,
        "payment_months_observed": 5,
    },
    "employment": {
        "employment_type": "freelance",
        "monthly_income_inr": 12000.0,
        "income_stability_score": 0.2,
        "months_in_current_work": 3,
        "income_proof_type": "self_declared",
    },
    "existing_emi_on_time_ratio": 0.4,
    "declared_attributes": {},
}


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = {key: (dict(value) if isinstance(value, dict) else value) for key, value in base.items()}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def strong_borrower(**overrides: Any) -> BorrowerSignalInput:
    return BorrowerSignalInput(**_merge(STRONG, overrides))


def weak_borrower(**overrides: Any) -> BorrowerSignalInput:
    return BorrowerSignalInput(**_merge(WEAK, overrides))


def agent_score(
    score: int = 70,
    confidence: str = "high",
    flags: list[str] | None = None,
) -> AgentScoreOutput:
    return AgentScoreOutput(
        score=score,
        confidence=confidence,
        reasoning="Synthetic agent output used by the test suite.",
        flags=flags or [],
    )


def compliance(
    rbi_compliant: bool = True,
    fraud_risk: str = "low",
    flags: list[str] | None = None,
) -> ComplianceAgentOutput:
    return ComplianceAgentOutput(
        rbi_compliant=rbi_compliant,
        fraud_risk=fraud_risk,
        flags=flags or [],
        notes="Synthetic compliance output used by the test suite.",
    )
