from __future__ import annotations

import asyncio

from .schemas import AgentScoreOutput, BorrowerSignalInput, ComplianceAgentOutput, GSTSignal

PROHIBITED_SIGNALS = {"religion", "caste", "gender", "political_affiliation"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_score(score: float) -> int:
    return int(round(max(0.0, min(100.0, score))))


def _ratio(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return _clamp01(value / target)


def _inverse_ratio(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return _clamp01(1.0 - (value / threshold))


def _trend_score(trend_pct: float, worst: float = -30.0, best: float = 25.0) -> float:
    if best <= worst:
        return 0.0
    return _clamp01((trend_pct - worst) / (best - worst))


def _band_score(value: float, low: float, high: float, hard_upper: float) -> float:
    if value < 0:
        return 0.0
    if low <= value <= high:
        return 1.0
    if value < low:
        return _clamp01(value / max(low, 1e-6))
    if value >= hard_upper:
        return 0.0
    return _clamp01(1.0 - ((value - high) / max(hard_upper - high, 1e-6)))


def _confidence_from_quality(data_quality: float) -> str:
    if data_quality >= 0.78:
        return "high"
    if data_quality >= 0.55:
        return "medium"
    return "low"


def _income_proof_score(proof_type: str) -> float:
    mapping = {
        "salary_slip": 1.0,
        "bank_statement": 0.95,
        "invoice": 0.9,
        "self_declared": 0.55,
    }
    return mapping.get(proof_type, 0.7)


def _gst_quality(gst: GSTSignal | None) -> float:
    if not gst or not gst.is_applicable:
        return 0.8
    filing_score = gst.filing_consistency_score
    missed_filings_score = _inverse_ratio(gst.missed_filings_last_12m, 6)
    trend_score = _trend_score(gst.revenue_trend_pct, worst=-20, best=20)
    return _clamp01((filing_score * 0.55) + (missed_filings_score * 0.25) + (trend_score * 0.2))


async def income_stability_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.05)
    upi = payload.upi
    gst = payload.gst
    employment = payload.employment

    upi_frequency_score = _ratio(upi.transaction_frequency_per_month, 160)
    upi_history_score = _ratio(upi.months_of_history, 24)
    upi_trend_score = _trend_score(upi.monthly_volume_trend_pct, worst=-30, best=25)
    work_tenure_score = _ratio(employment.months_in_current_work, 60)
    proof_score = _income_proof_score(employment.income_proof_type)
    gst_score = _gst_quality(gst)

    quality = _clamp01(
        (upi.regularity_score * 0.22)
        + (upi_frequency_score * 0.16)
        + (upi_history_score * 0.1)
        + (upi.merchant_diversity_score * 0.1)
        + (employment.income_stability_score * 0.22)
        + (work_tenure_score * 0.1)
        + (proof_score * 0.05)
        + (gst_score * 0.05)
    )

    penalties = 0.0
    flags: list[str] = []
    if upi.monthly_volume_trend_pct < -10:
        penalties += min(0.12, abs(upi.monthly_volume_trend_pct + 10) / 120)
        flags.append("UPI transaction volume trend is declining")
    if employment.income_proof_type == "self_declared":
        penalties += 0.08
        flags.append("Income proof is self-declared")
    if gst and gst.is_applicable:
        missed_penalty = min(0.22, gst.missed_filings_last_12m * 0.03)
        penalties += missed_penalty
        if gst.missed_filings_last_12m > 0:
            flags.append(f"{gst.missed_filings_last_12m} missed GST filing(s) in last 12 months")
        if gst.revenue_trend_pct < -15:
            penalties += 0.05
            flags.append("GST-reported revenue trend is strongly negative")

    final_quality = _clamp01(quality - penalties)
    score = _clamp_score(final_quality * 100)
    confidence = _confidence_from_quality((final_quality * 0.8) + (upi_history_score * 0.2))

    return AgentScoreOutput(
        score=score,
        confidence=confidence,
        reasoning=(
            "Income stability blends UPI consistency, historical depth, work tenure, income proof quality, "
            "and GST behavior when applicable."
        ),
        flags=flags,
    )


async def repayment_behaviour_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.05)
    rent = payload.rent
    utilities = payload.utilities
    emi_ratio = payload.existing_emi_on_time_ratio

    utility_score = (utilities.electricity_on_time_ratio + utilities.water_on_time_ratio) / 2
    tenancy_score = _ratio(rent.tenancy_months, 36)
    gap_score = _inverse_ratio(rent.longest_gap_months, 6)
    late_payment_score = _inverse_ratio(rent.late_payments_last_24m, 10)

    quality = _clamp01(
        (rent.on_time_payment_ratio * 0.36)
        + (utility_score * 0.22)
        + (emi_ratio * 0.2)
        + (tenancy_score * 0.1)
        + (gap_score * 0.07)
        + (late_payment_score * 0.05)
    )

    penalties = 0.0
    flags: list[str] = []
    if rent.longest_gap_months >= 2:
        penalties += min(0.2, (rent.longest_gap_months - 1) * 0.04)
        flags.append(f"Rental payment gap of {rent.longest_gap_months} month(s) observed")
    if rent.late_payments_last_24m > 0:
        penalties += min(0.16, rent.late_payments_last_24m * 0.02)
        flags.append(f"{rent.late_payments_last_24m} late rent payment(s) in 24 months")
    if emi_ratio < 0.85:
        penalties += min(0.15, (0.85 - emi_ratio) * 0.8)
        flags.append("Existing EMI repayment ratio is below preferred threshold")

    final_quality = _clamp01(quality - penalties)
    score = _clamp_score(final_quality * 100)
    confidence = _confidence_from_quality(
        (final_quality * 0.75) + (_ratio(utilities.payment_months_observed, 24) * 0.25)
    )

    return AgentScoreOutput(
        score=score,
        confidence=confidence,
        reasoning=(
            "Repayment behavior is driven by rent timeliness, utility bill discipline, EMI consistency, "
            "and payment-gap risk."
        ),
        flags=flags,
    )


async def lifestyle_risk_agent(payload: BorrowerSignalInput) -> AgentScoreOutput:
    await asyncio.sleep(0.05)
    mobile = payload.mobile
    upi = payload.upi

    safe_app_score = 1 - mobile.risky_app_usage_score
    recharge_regularity_score = _band_score(
        mobile.recharge_frequency_per_month,
        low=0.8,
        high=2.5,
        hard_upper=8.0,
    )
    data_usage_score = _band_score(
        mobile.monthly_data_usage_gb,
        low=4.0,
        high=50.0,
        hard_upper=180.0,
    )

    quality = _clamp01(
        (mobile.consistency_score * 0.25)
        + (mobile.finance_app_usage_score * 0.2)
        + (safe_app_score * 0.25)
        + (upi.merchant_diversity_score * 0.15)
        + (recharge_regularity_score * 0.1)
        + (data_usage_score * 0.05)
    )

    penalties = 0.0
    flags: list[str] = []
    if mobile.risky_app_usage_score > 0.6:
        penalties += min(0.2, (mobile.risky_app_usage_score - 0.6) * 0.6)
        flags.append("Elevated risky app usage pattern detected")
    if mobile.consistency_score < 0.4:
        penalties += 0.08
        flags.append("Mobile recharge behavior appears inconsistent")

    final_quality = _clamp01(quality - penalties)
    score = _clamp_score(final_quality * 100)
    confidence = _confidence_from_quality((final_quality * 0.8) + (_ratio(upi.months_of_history, 24) * 0.2))

    return AgentScoreOutput(
        score=score,
        confidence=confidence,
        reasoning=(
            "Lifestyle score evaluates digital consistency, app-risk exposure, spending diversity, "
            "and recharge/data usage regularity."
        ),
        flags=flags,
    )


async def compliance_and_fraud_agent(payload: BorrowerSignalInput) -> ComplianceAgentOutput:
    await asyncio.sleep(0.05)
    flags: list[str] = []
    severity = 0

    sensitive_keys = {k.strip().lower() for k in payload.declared_attributes.keys()}
    prohibited_found = sorted(PROHIBITED_SIGNALS.intersection(sensitive_keys))
    if prohibited_found:
        severity += 5
        flags.append(
            "Prohibited sensitive attributes present in input: " + ", ".join(prohibited_found)
        )

    if payload.employment.monthly_income_inr > 200_000 and payload.upi.average_transaction_value_inr < 400:
        severity += 2
        flags.append("Declared income appears inconsistent with transaction behavior")

    if payload.gst and payload.gst.is_applicable:
        if payload.gst.missed_filings_last_12m >= 4:
            severity += 2
            flags.append("High GST filing irregularity detected")
        elif payload.gst.missed_filings_last_12m >= 2:
            severity += 1
            flags.append("Moderate GST filing irregularity detected")

    if payload.rent.longest_gap_months >= 4 and payload.utilities.electricity_on_time_ratio < 0.6:
        severity += 2
        flags.append("Multiple repayment stress indicators detected")

    if payload.existing_emi_on_time_ratio < 0.75:
        severity += 2
        flags.append("Severe EMI repayment stress detected")

    if payload.mobile.risky_app_usage_score > 0.75:
        severity += 1
        flags.append("Very high risky app usage pattern detected")

    if severity >= 5:
        fraud_risk = "high"
    elif severity >= 2:
        fraud_risk = "medium"
    else:
        fraud_risk = "low"

    rbi_compliant = not prohibited_found
    return ComplianceAgentOutput(
        rbi_compliant=rbi_compliant,
        fraud_risk=fraud_risk,
        flags=flags,
        notes=(
            "Compliance checks evaluate RBI-sensitive attribute usage and cross-signal consistency. "
            "Higher severity indicates stronger review requirement."
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
