from __future__ import annotations

from .schemas import (
    AgentBreakdown,
    AgentScoreOutput,
    BorrowerSignalInput,
    ComplianceAgentOutput,
    ScoreResponse,
)

CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
COMPONENT_WEIGHTS = {"income": 0.4, "repayment": 0.4, "lifestyle": 0.2}
DISCLAIMER = "This score is indicative and not a guarantee of creditworthiness."


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _scale_to_credit_band(score_0_100: float) -> int:
    scaled = int(round(300 + (max(0.0, min(100.0, score_0_100)) * 6)))
    return max(300, min(900, scaled))


def _risk_level_from_score(score: int) -> str:
    if score >= 760:
        return "low"
    if score >= 620:
        return "medium"
    return "high"


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


def _compliance_penalty(compliance: ComplianceAgentOutput) -> float:
    penalty = min(14.0, len(compliance.flags) * 1.8)
    if compliance.fraud_risk == "medium":
        penalty += 8.0
    elif compliance.fraud_risk == "high":
        penalty += 18.0
    if not compliance.rbi_compliant:
        penalty += 10.0
    return min(36.0, penalty)


def _resolved_confidence(
    scoring_agents: list[AgentScoreOutput],
    spread: int,
    compliance: ComplianceAgentOutput,
    compliance_penalty: float,
) -> str:
    base_confidence = sum(CONFIDENCE_WEIGHT[s.confidence] for s in scoring_agents) / len(scoring_agents)
    spread_penalty = min(0.2, spread / 120)
    compliance_confidence_penalty = min(0.25, compliance_penalty / 120)
    non_compliance_penalty = 0.18 if not compliance.rbi_compliant else 0.0
    confidence_score = _clamp01(
        base_confidence - spread_penalty - compliance_confidence_penalty - non_compliance_penalty
    )

    if confidence_score >= 0.78:
        return "high"
    if confidence_score >= 0.52:
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
                f"Income stability is strong ({income.score}/100) with consistent UPI and work continuity.",
            )
        )
    if repayment.score >= 80:
        candidates.append(
            (
                repayment.score / 100,
                f"Repayment behavior is healthy ({repayment.score}/100) with solid rent/utility timeliness.",
            )
        )
    if lifestyle.score >= 80:
        candidates.append(
            (
                lifestyle.score / 100,
                "Digital behavior profile is stable with controlled risky-app exposure.",
            )
        )
    if payload.employment.income_proof_type != "self_declared":
        candidates.append((0.72, "Income proof is document-backed, improving lender confidence."))
    if payload.gst and payload.gst.is_applicable and payload.gst.missed_filings_last_12m == 0:
        candidates.append((0.75, "GST discipline is consistent with no missed filings in the last 12 months."))

    top = _top_unique_messages(candidates)
    return top if top else ["Signals indicate stable repayment and income behavior."]


def _derive_risk_factors(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
    compliance: ComplianceAgentOutput,
) -> list[str]:
    candidates: list[tuple[float, str]] = []
    for flag in repayment.flags:
        candidates.append((0.95, flag))
    for flag in income.flags:
        candidates.append((0.88, flag))
    for flag in lifestyle.flags:
        candidates.append((0.84, flag))
    for flag in compliance.flags:
        candidates.append((1.0, flag))

    if payload.existing_emi_on_time_ratio < 0.95:
        candidates.append(
            (
                min(0.9, 0.7 + ((0.95 - payload.existing_emi_on_time_ratio) * 2)),
                f"Existing EMI on-time ratio is {payload.existing_emi_on_time_ratio:.2f}, indicating tighter repayment buffer.",
            )
        )
    if payload.upi.monthly_volume_trend_pct < 0:
        candidates.append(
            (
                min(0.9, 0.68 + (abs(payload.upi.monthly_volume_trend_pct) / 120)),
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
    component_scores = {
        "income": income.score,
        "repayment": repayment.score,
        "lifestyle": lifestyle.score,
    }
    component_internal = (
        (component_scores["income"] * COMPONENT_WEIGHTS["income"])
        + (component_scores["repayment"] * COMPONENT_WEIGHTS["repayment"])
        + (component_scores["lifestyle"] * COMPONENT_WEIGHTS["lifestyle"])
    )
    component_contributions = {
        "income": round(component_scores["income"] * COMPONENT_WEIGHTS["income"], 2),
        "repayment": round(component_scores["repayment"] * COMPONENT_WEIGHTS["repayment"], 2),
        "lifestyle": round(component_scores["lifestyle"] * COMPONENT_WEIGHTS["lifestyle"], 2),
    }
    spread = max(component_scores.values()) - min(component_scores.values())
    compliance_penalty = _compliance_penalty(compliance)

    final_internal = max(0.0, min(100.0, component_internal - compliance_penalty))
    final_score = _scale_to_credit_band(final_internal)
    risk_level = _risk_level_from_score(final_score)
    confidence = _resolved_confidence(
        [income, repayment, lifestyle],
        spread=spread,
        compliance=compliance,
        compliance_penalty=compliance_penalty,
    )

    rbi_flags = list(compliance.flags)
    if compliance.fraud_risk == "high":
        rbi_flags.append("High fraud-risk pattern detected")
    if not compliance.rbi_compliant:
        rbi_flags.append("Potential RBI non-compliance in submitted attributes")

    compliance_status = "pass" if compliance.rbi_compliant and compliance.fraud_risk == "low" else "review"
    recommended_loan_limit = _loan_limit_from_profile(final_score, payload)
    positive_factors = _derive_positive_factors(payload, income, repayment, lifestyle)
    risk_factors = _derive_risk_factors(payload, income, repayment, lifestyle, compliance)

    explanation = (
        f"Income={income.score}, repayment={repayment.score}, lifestyle={lifestyle.score}. "
        f"Weighted component score is {component_internal:.1f}/100 using weights "
        "income 40%, repayment 40%, lifestyle 20%. "
        f"Compliance penalty is {compliance_penalty:.1f} points, producing final internal "
        f"{final_internal:.1f}/100 and credit score {final_score}."
    )

    return ScoreResponse(
        final_score=final_score,
        risk_level=risk_level,
        confidence=confidence,
        explanation=explanation,
        agent_breakdown=AgentBreakdown(
            income=income.score,
            repayment=repayment.score,
            lifestyle=lifestyle.score,
            compliance=compliance_status,
        ),
        component_weights={key: round(value, 4) for key, value in COMPONENT_WEIGHTS.items()},
        component_contributions=component_contributions,
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
