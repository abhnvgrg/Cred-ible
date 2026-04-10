from __future__ import annotations

from .schemas import (
    AgentBreakdown,
    AgentScoreOutput,
    BorrowerSignalInput,
    ComplianceAgentOutput,
    ScoreResponse,
)

CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}
DISCLAIMER = "This score is indicative and not a guarantee of creditworthiness."


def _scale_to_credit_band(score_0_100: float) -> int:
    scaled = int(round(300 + (max(0, min(100, score_0_100)) * 6)))
    return max(300, min(900, scaled))


def _loan_limit_from_score(final_score: int) -> str:
    if final_score < 500:
        return "₹20,000 - ₹50,000"
    if final_score < 650:
        return "₹50,000 - ₹1,50,000"
    if final_score < 750:
        return "₹1,50,000 - ₹3,00,000"
    return "₹3,00,000 - ₹6,00,000"


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


def resolve_scores(
    payload: BorrowerSignalInput,
    income: AgentScoreOutput,
    repayment: AgentScoreOutput,
    lifestyle: AgentScoreOutput,
    compliance: ComplianceAgentOutput,
    processing_time_ms: int,
) -> ScoreResponse:
    scoring_agents = [income, repayment, lifestyle]
    weighted_numerator = sum(s.score * CONFIDENCE_WEIGHT[s.confidence] for s in scoring_agents)
    weighted_denominator = sum(CONFIDENCE_WEIGHT[s.confidence] for s in scoring_agents)
    weighted_avg = weighted_numerator / max(weighted_denominator, 1e-6)

    score_values = [income.score, repayment.score, lifestyle.score]
    spread = max(score_values) - min(score_values)
    conflict_detected = spread >= 25

    if conflict_detected:
        reliability_scores = {
            "income": _income_reliability(payload, income),
            "repayment": _repayment_reliability(payload, repayment),
            "lifestyle": _lifestyle_reliability(payload, lifestyle),
        }
        most_reliable_name = max(reliability_scores, key=reliability_scores.get)
        most_reliable_score = {
            "income": income.score,
            "repayment": repayment.score,
            "lifestyle": lifestyle.score,
        }[most_reliable_name]
        final_internal = (weighted_avg * 0.6) + (most_reliable_score * 0.4)
        conflict_explanation = (
            f"Agent outputs showed divergence (spread {spread} points), so the resolver "
            f"prioritized the {most_reliable_name} signal due to stronger reliability indicators."
        )
    else:
        final_internal = weighted_avg
        conflict_explanation = (
            f"Agent outputs were reasonably aligned (spread {spread} points), so confidence-weighted averaging was used."
        )

    confidence = _base_confidence(scoring_agents)
    rbi_flags = list(compliance.flags)
    if compliance.fraud_risk == "high":
        final_internal -= 15
        confidence = "low"
        rbi_flags.append("High fraud-risk pattern detected")
    elif compliance.fraud_risk == "medium":
        final_internal -= 7

    if not compliance.rbi_compliant:
        confidence = "low"
        rbi_flags.append("Potential RBI non-compliance in submitted attributes")

    final_score = _scale_to_credit_band(final_internal)
    recommended_loan_limit = _loan_limit_from_score(final_score)
    compliance_status = "pass" if compliance.rbi_compliant and compliance.fraud_risk != "high" else "review"

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
