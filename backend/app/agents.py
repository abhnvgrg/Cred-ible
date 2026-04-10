from __future__ import annotations

import asyncio

from .schemas import AgentScoreOutput, BorrowerSignalInput, ComplianceAgentOutput

CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
PROHIBITED_SIGNALS = {"religion", "caste", "gender", "political_affiliation"}


def _clamp_score(score: float) -> int:
    return int(max(0, min(100, round(score))))


def _confidence_from_quality(data_quality: float) -> str:
    if data_quality >= 0.75:
        return "high"
    if data_quality >= 0.45:
        return "medium"
    return "low"


async def income_stability_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.2)
    upi = payload.upi
    gst = payload.gst
    employment = payload.employment

    score = 40.0
    score += min(20, upi.transaction_frequency_per_month / 12)
    score += upi.regularity_score * 15
    score += upi.merchant_diversity_score * 5
    score += employment.income_stability_score * 15
    score += min(10, employment.months_in_current_work / 12)

    flags: list[str] = []
    if upi.monthly_volume_trend_pct < -10:
        score -= 6
        flags.append("UPI transaction volume trend is declining")
    if employment.income_proof_type == "self_declared":
        score -= 8
        flags.append("Income proof is self-declared")
    if gst and gst.is_applicable:
        score += gst.filing_consistency_score * 8
        score -= gst.missed_filings_last_12m * 2
        if gst.revenue_trend_pct < -10:
            score -= 4
            flags.append("GST-reported revenue trend is negative")

    quality = (
        min(1.0, upi.months_of_history / 12) * 0.45
        + employment.income_stability_score * 0.35
        + (0.2 if employment.income_proof_type != "self_declared" else 0.05)
    )
    confidence = _confidence_from_quality(quality)
    return AgentScoreOutput(
        score=_clamp_score(score),
        confidence=confidence,
        reasoning=(
            "Income stability was assessed using UPI regularity, work continuity, "
            "and available income proof. A stronger and more stable transaction "
            "pattern over time improved this score."
        ),
        flags=flags,
    )


async def repayment_behaviour_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.25)
    rent = payload.rent
    utilities = payload.utilities
    emi_ratio = payload.existing_emi_on_time_ratio

    score = 35.0
    score += rent.on_time_payment_ratio * 35
    score += ((utilities.electricity_on_time_ratio + utilities.water_on_time_ratio) / 2) * 20
    score += emi_ratio * 10
    score += min(10, rent.tenancy_months / 24)
    score -= rent.longest_gap_months * 4
    score -= rent.late_payments_last_24m * 1.5

    flags: list[str] = []
    if rent.longest_gap_months >= 2:
        flags.append(f"Rental payment gap of {rent.longest_gap_months} month(s) observed")
    if rent.late_payments_last_24m > 0:
        flags.append(f"{rent.late_payments_last_24m} late rent payment(s) in 24 months")
    if emi_ratio < 0.85:
        flags.append("Existing EMI repayment ratio is below preferred threshold")

    quality = (
        rent.on_time_payment_ratio * 0.45
        + ((utilities.electricity_on_time_ratio + utilities.water_on_time_ratio) / 2) * 0.35
        + min(1.0, utilities.payment_months_observed / 24) * 0.2
    )
    confidence = _confidence_from_quality(quality)
    return AgentScoreOutput(
        score=_clamp_score(score),
        confidence=confidence,
        reasoning=(
            "Repayment behavior was inferred from rent and utility bill discipline. "
            "High on-time payment consistency improved the score, while payment gaps "
            "or late events reduced it."
        ),
        flags=flags,
    )


async def lifestyle_risk_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.15)
    mobile = payload.mobile
    upi = payload.upi

    score = 45.0
    score += mobile.consistency_score * 20
    score += mobile.finance_app_usage_score * 20
    score -= mobile.risky_app_usage_score * 25
    score += min(10, upi.merchant_diversity_score * 10)
    score += min(8, mobile.recharge_frequency_per_month * 1.2)

    flags: list[str] = []
    if mobile.risky_app_usage_score > 0.5:
        flags.append("Elevated risky app usage pattern detected")
    if mobile.consistency_score < 0.4:
        flags.append("Mobile recharge behavior appears inconsistent")

    quality = (
        mobile.consistency_score * 0.45
        + mobile.finance_app_usage_score * 0.35
        + (1 - mobile.risky_app_usage_score) * 0.2
    )
    confidence = _confidence_from_quality(quality)
    return AgentScoreOutput(
        score=_clamp_score(score),
        confidence=confidence,
        reasoning=(
            "Lifestyle risk considered recharge consistency, app usage quality, and "
            "spending diversity. Financial app engagement generally improved this "
            "score, while risky usage patterns reduced it."
        ),
        flags=flags,
    )


async def compliance_and_fraud_agent(payload: BorrowerSignalInput) -> ComplianceAgentOutput:
    await asyncio.sleep(0.1)
    flags: list[str] = []

    sensitive_keys = {k.strip().lower() for k in payload.declared_attributes.keys()}
    prohibited_found = sorted(PROHIBITED_SIGNALS.intersection(sensitive_keys))
    if prohibited_found:
        flags.append(
            "Prohibited sensitive attributes present in input: " + ", ".join(prohibited_found)
        )

    if payload.employment.monthly_income_inr > 300_000 and payload.upi.average_transaction_value_inr < 200:
        flags.append("Declared income appears inconsistent with transaction behavior")
    if payload.gst and payload.gst.is_applicable and payload.gst.missed_filings_last_12m >= 4:
        flags.append("High GST filing irregularity detected")
    if payload.rent.longest_gap_months >= 4 and payload.utilities.electricity_on_time_ratio < 0.6:
        flags.append("Multiple repayment stress indicators detected")

    if prohibited_found or len(flags) >= 3:
        fraud_risk = "high"
    elif len(flags) >= 1:
        fraud_risk = "medium"
    else:
        fraud_risk = "low"

    rbi_compliant = not prohibited_found
    return ComplianceAgentOutput(
        rbi_compliant=rbi_compliant,
        fraud_risk=fraud_risk,
        flags=flags,
        notes=(
            "Compliance checks evaluate signal consistency and RBI-sensitive attribute "
            "violations. Any sensitive-attribute usage triggers non-compliance."
        ),
    )


async def run_all_agents(payload: BorrowerSignalInput) -> dict[str, AgentScoreOutput | ComplianceAgentOutput]:
    income, repayment, lifestyle, compliance = await asyncio.gather(
        income_stability_agent(payload),
        repayment_behaviour_agent(payload),
        lifestyle_risk_agent(payload),
        compliance_and_fraud_agent(payload),
    )
    return {
        "income": income,
        "repayment": repayment,
        "lifestyle": lifestyle,
        "compliance": compliance,
    }
