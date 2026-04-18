from __future__ import annotations

from .schemas import (
    AgentBreakdown,
    AgentScoreOutput,
    BorrowerSignalInput,
    ComplianceAgentOutput,
    ScoreResponse,
)

CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
BASE_SIGNAL_WEIGHT = {"income": 0.4, "repayment": 0.4, "lifestyle": 0.2}
DISCLAIMER = "This score is indicative and not a guarantee of creditworthiness."


def _scale_to_credit_band(score_0_100: float) -> int:
    scaled = int(round(300 + (max(0, min(100, score_0_100)) * 6)))
    return max(300, min(900, scaled))


def _format_inr(value: int) -> str:
    number = str(max(0, int(round(value))))
    if len(number) <= 3:
        return f"₹{number}"

    last_three = number[-3:]
    remaining = number[:-3]
    groups: list[str] = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    return f"₹{','.join(groups + [last_three])}"


def _base_loan_band(final_score: int) -> tuple[int, int]:
    if final_score < 500:
        return (20_000, 50_000)
    if final_score < 650:
        return (50_000, 150_000)
    if final_score < 750:
        return (150_000, 300_000)
    if final_score < 820:
        return (220_000, 450_000)
    return (300_000, 650_000)


def _loan_limit_from_profile(final_score: int, payload: BorrowerSignalInput) -> str:
    base_min, base_max = _base_loan_band(final_score)
    monthly_income = payload.employment.monthly_income_inr
    income_factor = 0.8 + min(0.8, monthly_income / 150_000)
    stability_factor = 0.9 + (
        ((payload.employment.income_stability_score + payload.rent.on_time_payment_ratio) / 2) * 0.2
    )
    stress_penalty = min(
        0.28,
        (payload.rent.longest_gap_months * 0.025)
        + (payload.rent.late_payments_last_24m * 0.008)
        + max(0.0, 0.95 - payload.existing_emi_on_time_ratio) * 0.5,
    )
    profile_multiplier = max(0.75, min(1.75, income_factor * stability_factor * (1 - stress_penalty)))

    adjusted_min = int(round(base_min * profile_multiplier))
    adjusted_max = int(round(base_max * profile_multiplier))
    if adjusted_max - adjusted_min < 40_000:
        adjusted_max = adjusted_min + 40_000
    return f"{_format_inr(adjusted_min)} - {_format_inr(adjusted_max)}"


def _base_confidence(scores: list[AgentScoreOutput]) -> str:
    weights = [CONFIDENCE_WEIGHT[s.confidence] for s in scores]
    avg = sum(weights) / len(weights)
    if avg >= 0.85:
        return "high"
    if avg >= 0.6:
        return "medium"
    return "low"


def _income_reliability(payload: BorrowerSignalInput, income: AgentScoreOutput) -> float:
    proof_bonus = 0.2 if payload.employment.income_proof_type != "self_declared" else 0.05
    history_bonus = min(0.25, payload.upi.months_of_history / 48)
    return CONFIDENCE_WEIGHT[income.confidence] + proof_bonus + history_bonus


def _repayment_reliability(payload: BorrowerSignalInput, repayment: AgentScoreOutput) -> float:
    payment_quality = (
        payload.rent.on_time_payment_ratio * 0.6
        + ((payload.utilities.electricity_on_time_ratio + payload.utilities.water_on_time_ratio) / 2) * 0.4
    )
    return CONFIDENCE_WEIGHT[repayment.confidence] + (payment_quality * 0.4)


def _lifestyle_reliability(payload: BorrowerSignalInput, lifestyle: AgentScoreOutput) -> float:
    behavior_quality = (
        payload.mobile.consistency_score * 0.5
        + payload.mobile.finance_app_usage_score * 0.35
        + (1 - payload.mobile.risky_app_usage_score) * 0.15
    )
    return CONFIDENCE_WEIGHT[lifestyle.confidence] + (behavior_quality * 0.25)


def _normalized_signal_weights(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
) -> dict[str, float]:
    reliability = {
        "income": _income_reliability(payload, income),
        "repayment": _repayment_reliability(payload, repayment),
        "lifestyle": _lifestyle_reliability(payload, lifestyle),
    }
    confidence_boost = {
        "income": 0.7 + (0.3 * CONFIDENCE_WEIGHT[income.confidence]),
        "repayment": 0.7 + (0.3 * CONFIDENCE_WEIGHT[repayment.confidence]),
        "lifestyle": 0.7 + (0.3 * CONFIDENCE_WEIGHT[lifestyle.confidence]),
    }

    raw_weights = {
        signal: BASE_SIGNAL_WEIGHT[signal]
        * confidence_boost[signal]
        * (0.65 + 0.35 * min(1.0, reliability[signal] / 1.5))
        for signal in BASE_SIGNAL_WEIGHT
    }
    total = max(1e-6, sum(raw_weights.values()))
    return {signal: weight / total for signal, weight in raw_weights.items()}


def _compliance_penalty(compliance: ComplianceAgentOutput) -> float:
    penalty = float(len(compliance.flags)) * 1.2
    if compliance.fraud_risk == "high":
        penalty += 12.0
    elif compliance.fraud_risk == "medium":
        penalty += 6.0
    if not compliance.rbi_compliant:
        penalty += 8.0
    return penalty


def _resolved_confidence(
    scores: list[AgentScoreOutput],
    spread: int,
    compliance: ComplianceAgentOutput,
) -> str:
    confidence_score = sum(CONFIDENCE_WEIGHT[s.confidence] for s in scores) / len(scores)
    confidence_score -= min(0.2, max(0.0, spread - 16) * 0.01)
    if compliance.fraud_risk == "medium":
        confidence_score -= 0.1
    elif compliance.fraud_risk == "high":
        confidence_score -= 0.25
    if not compliance.rbi_compliant:
        confidence_score -= 0.2

    if confidence_score >= 0.82:
        return "high"
    if confidence_score >= 0.55:
        return "medium"
    return "low"


def _top_unique_messages(candidates: list[tuple[float, str]], limit: int = 3) -> list[str]:
    if not candidates:
        return []

    selected: list[str] = []
    seen: set[str] = set()
    for _, message in sorted(candidates, key=lambda item: item[0], reverse=True):
        if message in seen:
            continue
        selected.append(message)
        seen.add(message)
        if len(selected) >= limit:
            break
    return selected


def _derive_positive_factors(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
) -> list[str]:
    candidates: list[tuple[float, str]] = []
    if income.score >= 80:
        candidates.append(
            (
                income.score / 100,
                (
                    f"Income stability is strong ({income.score}/100) with "
                    f"{payload.upi.transaction_frequency_per_month} UPI transactions/month."
                ),
            )
        )
    if repayment.score >= 80:
        on_time_pct = int(round(payload.rent.on_time_payment_ratio * 100))
        candidates.append(
            (
                repayment.score / 100,
                f"Repayment discipline is healthy with {on_time_pct}% on-time rent payments.",
            )
        )
    if lifestyle.score >= 80:
        candidates.append(
            (
                lifestyle.score / 100,
                (
                    "Digital behavior quality is supportive (good app usage mix and controlled "
                    "risky-app exposure)."
                ),
            )
        )
    if payload.employment.income_proof_type != "self_declared":
        candidates.append((0.76, "Income proof is document-backed, improving lender confidence."))
    if payload.gst and payload.gst.is_applicable and payload.gst.missed_filings_last_12m == 0:
        candidates.append((0.74, "GST compliance is consistent with no missed filings in the last 12 months."))
    if payload.upi.monthly_volume_trend_pct > 0:
        candidates.append(
            (
                min(0.9, 0.65 + (payload.upi.monthly_volume_trend_pct / 100)),
                f"UPI transaction volume trend is positive at {payload.upi.monthly_volume_trend_pct:.0f}%.",
            )
        )
    if payload.rent.tenancy_months >= 24:
        candidates.append((0.7, f"Stable tenancy history observed over {payload.rent.tenancy_months} months."))

    top = _top_unique_messages(candidates)
    return top if top else ["Signals show stable income and repayment behavior."]


def _derive_risk_factors(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
    compliance: ComplianceAgentOutput,
) -> list[str]:
    candidates: list[tuple[float, str]] = []
    has_late_rent_flag = any("late rent payment" in flag.lower() for flag in repayment.flags)
    has_payment_gap_flag = any("payment gap" in flag.lower() for flag in repayment.flags)
    for flag in income.flags:
        candidates.append((0.9, flag))
    for flag in repayment.flags:
        candidates.append((0.95, flag))
    for flag in lifestyle.flags:
        candidates.append((0.85, flag))
    for flag in compliance.flags:
        candidates.append((1.0, flag))

    if payload.rent.late_payments_last_24m > 0 and not has_late_rent_flag:
        candidates.append(
            (
                min(0.95, 0.7 + (payload.rent.late_payments_last_24m / 20)),
                f"{payload.rent.late_payments_last_24m} late rent payment(s) in the last 24 months.",
            )
        )
    if payload.rent.longest_gap_months > 0 and not has_payment_gap_flag:
        candidates.append(
            (
                min(0.98, 0.72 + (payload.rent.longest_gap_months / 10)),
                f"Rental payment gap reached {payload.rent.longest_gap_months} month(s).",
            )
        )
    if payload.existing_emi_on_time_ratio < 0.95:
        candidates.append(
            (
                min(0.92, 0.7 + ((0.95 - payload.existing_emi_on_time_ratio) * 2)),
                f"Existing EMI on-time ratio is {payload.existing_emi_on_time_ratio:.2f}, indicating tighter buffer.",
            )
        )
    if payload.mobile.risky_app_usage_score >= 0.2:
        candidates.append(
            (
                min(0.9, 0.65 + payload.mobile.risky_app_usage_score),
                (
                    "Risky app usage pattern is higher than preferred and should be "
                    "kept under control."
                ),
            )
        )
    if payload.gst and payload.gst.is_applicable and payload.gst.missed_filings_last_12m > 0:
        candidates.append(
            (
                min(0.9, 0.7 + (payload.gst.missed_filings_last_12m / 20)),
                f"GST filing irregularity observed ({payload.gst.missed_filings_last_12m} missed filing(s)).",
            )
        )
    if payload.upi.monthly_volume_trend_pct < 0:
        candidates.append(
            (
                min(0.9, 0.7 + (abs(payload.upi.monthly_volume_trend_pct) / 100)),
                f"UPI transaction volume trend is negative at {payload.upi.monthly_volume_trend_pct:.0f}%.",
            )
        )
    if compliance.fraud_risk != "low":
        candidates.append((0.96, f"Compliance agent marked {compliance.fraud_risk} fraud-risk level."))

    top = _top_unique_messages(candidates)
    return top if top else ["No material repayment or compliance stress indicators detected."]


def resolve_scores(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
    compliance: ComplianceAgentOutput,
    processing_time_ms: int,
) -> ScoreResponse:
    scoring_agents = [income, repayment, lifestyle]
    score_values = {"income": income.score, "repayment": repayment.score, "lifestyle": lifestyle.score}
    spread = max(score_values.values()) - min(score_values.values())
    signal_weights = _normalized_signal_weights(payload, income, repayment, lifestyle)
    weighted_avg = sum(score_values[signal] * signal_weights[signal] for signal in score_values)

    # Penalize high disagreement smoothly instead of using hard conflict branches.
    disagreement_penalty = max(0.0, spread - 18) * 0.22
    compliance_penalty = _compliance_penalty(compliance)
    final_internal = max(0.0, min(100.0, weighted_avg - disagreement_penalty - compliance_penalty))

    confidence = _resolved_confidence(scoring_agents, spread, compliance)
    rbi_flags = list(compliance.flags)
    if compliance.fraud_risk == "high":
        rbi_flags.append("High fraud-risk pattern detected")

    if not compliance.rbi_compliant:
        rbi_flags.append("Potential RBI non-compliance in submitted attributes")

    final_score = _scale_to_credit_band(final_internal)
    recommended_loan_limit = _loan_limit_from_profile(final_score, payload)
    positive_factors = _derive_positive_factors(payload, income, repayment, lifestyle)
    risk_factors = _derive_risk_factors(payload, income, repayment, lifestyle, compliance)
    compliance_status = "pass" if compliance.rbi_compliant and compliance.fraud_risk != "high" else "review"
    dominant_signal = max(signal_weights, key=signal_weights.get)
    conflict_explanation = (
        f"Resolver weights were income {signal_weights['income']:.2f}, repayment {signal_weights['repayment']:.2f}, "
        f"and lifestyle {signal_weights['lifestyle']:.2f} with {dominant_signal} as the leading signal. "
        f"Agent spread was {spread} points, resulting in a disagreement penalty of {disagreement_penalty:.1f}."
    )

    explanation = (
        f"Income score is {income.score}, repayment score is {repayment.score}, and lifestyle score is "
        f"{lifestyle.score}. {conflict_explanation} {income.reasoning} {repayment.reasoning} "
        f"Overall borrower risk is {'moderate-low' if final_score >= 650 else 'moderate' if final_score >= 550 else 'elevated'}."
    )

    return ScoreResponse(
        final_score=final_score,
        confidence=confidence,
        explanation=explanation,
        agent_breakdown=AgentBreakdown(
            income=income.score,
            repayment=repayment.score,
            lifestyle=lifestyle.score,
            compliance=compliance_status,
        ),
        rbi_flags=rbi_flags,
        positive_factors=positive_factors,
        risk_factors=risk_factors,
        recommended_loan_limit=recommended_loan_limit,
        processing_time_ms=processing_time_ms,
        disclaimer=DISCLAIMER,
        agent_outputs={
            "income": income,
            "repayment": repayment,
            "lifestyle": lifestyle,
            "compliance": compliance,
        },
    )
