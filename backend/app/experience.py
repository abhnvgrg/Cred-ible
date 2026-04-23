from __future__ import annotations

import time
from secrets import token_urlsafe
from uuid import uuid4

from .resolver import COMPONENT_WEIGHTS
from .schemas import (
    AgentBreakdown,
    AuthResponse,
    ConfidenceLevel,
    LoginRequest,
    MarketplaceOffer,
    MarketplaceResponse,
    RegisterRequest,
    WhatIfRecommendation,
    WhatIfRequest,
    WhatIfResponse,
)

WHAT_IF_DISCLAIMER = "This score is indicative and not a guarantee of creditworthiness."
MARKETPLACE_DISCLAIMER = (
    "Marketplace suggestions are indicative references and do not constitute sanctioned credit."
)


def _is_email_like(value: str) -> bool:
    trimmed = value.strip()
    return "@" in trimmed and "." in trimmed.split("@")[-1]


def authenticate_user(payload: LoginRequest) -> AuthResponse:
    if not _is_email_like(payload.email):
        raise ValueError("Please provide a valid work email.")

    local_name = payload.email.split("@")[0].replace(".", " ").replace("_", " ").strip()
    full_name = " ".join(part.capitalize() for part in local_name.split() if part) or "Workspace User"
    domain = payload.email.split("@")[-1].split(".")[0]
    organization = " ".join(part.capitalize() for part in domain.replace("-", " ").split())

    return AuthResponse(
        user_id=f"user_{uuid4().hex[:10]}",
        full_name=full_name,
        work_email=payload.email.strip().lower(),
        organization=organization or "Cred-ible Partner",
        role="analyst",
        session_token=token_urlsafe(32),
        expires_in_seconds=8 * 60 * 60,
        message="Signed in successfully.",
    )


def register_user(payload: RegisterRequest) -> AuthResponse:
    if not _is_email_like(payload.work_email):
        raise ValueError("Please provide a valid work email.")
    if payload.password != payload.confirm_password:
        raise ValueError("Password and confirm password must match.")

    return AuthResponse(
        user_id=f"user_{uuid4().hex[:10]}",
        full_name=payload.full_name.strip(),
        work_email=payload.work_email.strip().lower(),
        organization=payload.organization.strip(),
        role="admin",
        session_token=token_urlsafe(32),
        expires_in_seconds=8 * 60 * 60,
        message="Workspace account created successfully.",
    )


def _clamp_score(value: float) -> int:
    return max(300, min(900, int(round(value))))


def _clamp_component(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _internal_from_score(score: int) -> float:
    return max(0.0, min(100.0, (score - 300) / 6))


def _score_from_internal(value: float) -> int:
    return _clamp_score(300 + (max(0.0, min(100.0, value)) * 6))


def _component_internal(income: int, repayment: int, lifestyle: int) -> float:
    return (
        (income * COMPONENT_WEIGHTS["income"])
        + (repayment * COMPONENT_WEIGHTS["repayment"])
        + (lifestyle * COMPONENT_WEIGHTS["lifestyle"])
    )


def _derive_base_breakdown(payload: WhatIfRequest) -> tuple[int, int, int]:
    provided = (
        payload.base_income_score is not None
        and payload.base_repayment_score is not None
        and payload.base_lifestyle_score is not None
    )
    if provided:
        return (
            _clamp_component(payload.base_income_score or 0),
            _clamp_component(payload.base_repayment_score or 0),
            _clamp_component(payload.base_lifestyle_score or 0),
        )

    internal_score = _internal_from_score(payload.base_score)
    baseline_component = _clamp_component(internal_score)
    return (baseline_component, baseline_component, baseline_component)


def _scenario_confidence(
    payload: WhatIfRequest,
    base_breakdown_was_derived: bool,
    baseline_penalty: float,
) -> ConfidenceLevel:
    confidence_value = 0.84 if not base_breakdown_was_derived else 0.7
    scenario_magnitude = payload.income_shift + payload.compliance_boost + payload.debt_reduction
    confidence_value -= min(0.22, scenario_magnitude / 90)
    confidence_value -= min(0.12, baseline_penalty / 80)

    if confidence_value >= 0.76:
        return "high"
    if confidence_value >= 0.5:
        return "medium"
    return "low"


def _recommendation_impact(value: float) -> str:
    if value >= 10:
        return "high"
    if value >= 5:
        return "medium"
    return "low"


def _base_compliance_penalty(payload: WhatIfRequest) -> float:
    status_penalty = 0.0
    if payload.compliance_status == "review":
        status_penalty = 6.0
    elif payload.compliance_status == "fail":
        status_penalty = 12.0
    flag_penalty = min(18.0, payload.rbi_flags_count * 1.5)
    return min(30.0, status_penalty + flag_penalty)


def _shift_gain(shift: int, base_component: int, max_gain: float) -> float:
    if shift <= 0:
        return 0.0
    normalized_shift = min(1.0, shift / 20)
    headroom = max(0.0, min(1.0, (100 - base_component) / 100))
    return max_gain * normalized_shift * (0.3 + (0.7 * headroom))


def _risk_level_from_score(score: int) -> str:
    if score >= 760:
        return "low"
    if score >= 620:
        return "medium"
    return "high"


def run_what_if_simulation(payload: WhatIfRequest) -> WhatIfResponse:
    started = time.perf_counter()
    base_income, base_repayment, base_lifestyle = _derive_base_breakdown(payload)
    base_breakdown_was_derived = (
        payload.base_income_score is None
        or payload.base_repayment_score is None
        or payload.base_lifestyle_score is None
    )

    income_gain = _shift_gain(payload.income_shift, base_income, max_gain=18.0)
    compliance_repayment_gain = _shift_gain(payload.compliance_boost, base_repayment, max_gain=12.0)
    compliance_lifestyle_gain = _shift_gain(payload.compliance_boost, base_lifestyle, max_gain=8.0)
    debt_repayment_gain = _shift_gain(payload.debt_reduction, base_repayment, max_gain=20.0)
    debt_income_gain = _shift_gain(payload.debt_reduction, base_income, max_gain=4.0)
    debt_lifestyle_gain = _shift_gain(payload.debt_reduction, base_lifestyle, max_gain=3.0)

    projected_income = _clamp_component(base_income + income_gain + debt_income_gain)
    projected_repayment = _clamp_component(base_repayment + compliance_repayment_gain + debt_repayment_gain)
    projected_lifestyle = _clamp_component(base_lifestyle + compliance_lifestyle_gain + debt_lifestyle_gain)

    base_penalty = _base_compliance_penalty(payload)
    penalty_relief = min(base_penalty, (payload.compliance_boost / 20) * min(12.0, base_penalty))
    projected_penalty = max(0.0, base_penalty - penalty_relief)

    base_model_internal = _component_internal(base_income, base_repayment, base_lifestyle) - base_penalty
    projected_model_internal = (
        _component_internal(projected_income, projected_repayment, projected_lifestyle) - projected_penalty
    )
    alignment = _internal_from_score(payload.base_score) - base_model_internal
    projected_internal = projected_model_internal + alignment
    projected_score = _score_from_internal(projected_internal)

    if payload.income_shift == 0 and payload.compliance_boost == 0 and payload.debt_reduction == 0:
        projected_score = payload.base_score
    else:
        projected_score = max(payload.base_score, projected_score)

    delta = projected_score - payload.base_score
    confidence = _scenario_confidence(payload, base_breakdown_was_derived, baseline_penalty=base_penalty)
    base_risk = _risk_level_from_score(payload.base_score)
    projected_risk = _risk_level_from_score(projected_score)

    component_impacts = {
        "income": projected_income - base_income,
        "repayment": projected_repayment - base_repayment,
        "lifestyle": projected_lifestyle - base_lifestyle,
    }
    if projected_penalty <= 2.0 and payload.compliance_status in {"pass", None}:
        projected_compliance = "pass"
    elif projected_penalty <= 6.0 and payload.compliance_boost >= 12:
        projected_compliance = "pass"
    elif payload.compliance_status == "fail" and projected_penalty > 8.0:
        projected_compliance = "fail"
    else:
        projected_compliance = "review"

    recommendations = [
        WhatIfRecommendation(
            title="Income stability uplift",
            impact=_recommendation_impact(income_gain + debt_income_gain),
            note=(
                "Increase recurring verified inflows and reduce month-to-month volatility to improve the income component."
            ),
        ),
        WhatIfRecommendation(
            title="Compliance regularity",
            impact=_recommendation_impact(compliance_repayment_gain + compliance_lifestyle_gain),
            note=(
                "Clearing compliance flags provides direct score uplift by lowering compliance penalty drag."
            ),
        ),
        WhatIfRecommendation(
            title="Debt stress reduction",
            impact=_recommendation_impact(debt_repayment_gain),
            note=(
                "Lower utilization and smoother repayment cycles improve repayment resilience and score stability."
            ),
        ),
    ]

    explanation = (
        f"Starting from {payload.base_score}, simulated adjustments produced a projected score of "
        f"{projected_score} ({delta:+d}). Risk level moved from {base_risk} to {projected_risk}. "
        f"Component impact: income {component_impacts['income']:+d}, repayment {component_impacts['repayment']:+d}, "
        f"lifestyle {component_impacts['lifestyle']:+d}. Compliance penalty moved from {base_penalty:.1f} to {projected_penalty:.1f}."
    )

    processing_time_ms = int((time.perf_counter() - started) * 1000)
    return WhatIfResponse(
        base_score=payload.base_score,
        projected_score=projected_score,
        score_delta=delta,
        projected_risk_level=projected_risk,
        confidence=confidence,
        explanation=explanation,
        projected_breakdown=AgentBreakdown(
            income=projected_income,
            repayment=projected_repayment,
            lifestyle=projected_lifestyle,
            compliance=projected_compliance,
        ),
        component_impacts=component_impacts,
        recommendations=recommendations,
        processing_time_ms=processing_time_ms,
        disclaimer=WHAT_IF_DISCLAIMER,
    )


def _risk_rate_adjustment(score: int) -> float:
    if score >= 780:
        return -1.6
    if score >= 720:
        return -0.8
    if score >= 650:
        return 0.0
    if score >= 580:
        return 1.4
    return 2.8


def _match(score: int, base: int, index: int) -> int:
    adjusted = base + round((score - 700) / 22) - index
    return max(55, min(99, adjusted))


def get_marketplace_offers(score: int) -> MarketplaceResponse:
    normalized_score = _clamp_score(score)
    rate_shift = _risk_rate_adjustment(normalized_score)

    base_offers = [
        {
            "lender": "SwiftBank",
            "product_type": "Working capital",
            "eligible_amount_inr": 500_000,
            "indicative_rate_apr": 10.5,
            "tenure_months": 24,
            "ai_match_pct": 96,
            "rationale": "Strong transaction regularity and repayment confidence.",
            "requires_additional_docs": False,
        },
        {
            "lender": "Apex Capital",
            "product_type": "Business expansion",
            "eligible_amount_inr": 1_250_000,
            "indicative_rate_apr": 11.2,
            "tenure_months": 36,
            "ai_match_pct": 86,
            "rationale": "Balanced income and compliance profile suitable for growth lending.",
            "requires_additional_docs": True,
        },
        {
            "lender": "NeoLend",
            "product_type": "Personal loan",
            "eligible_amount_inr": 375_000,
            "indicative_rate_apr": 9.9,
            "tenure_months": 18,
            "ai_match_pct": 82,
            "rationale": "Good lifestyle and payment discipline with moderate risk exposure.",
            "requires_additional_docs": False,
        },
    ]

    offers = [
        MarketplaceOffer(
            lender=offer["lender"],
            product_type=offer["product_type"],
            eligible_amount_inr=max(
                20_000, int(round(offer["eligible_amount_inr"] * (0.72 + (normalized_score / 1000))))
            ),
            indicative_rate_apr=round(
                max(7.0, min(36.0, offer["indicative_rate_apr"] + rate_shift)),
                2,
            ),
            tenure_months=offer["tenure_months"],
            ai_match_pct=_match(normalized_score, offer["ai_match_pct"], idx),
            rationale=offer["rationale"],
            requires_additional_docs=offer["requires_additional_docs"],
        )
        for idx, offer in enumerate(base_offers)
    ]

    offers.sort(key=lambda item: item.ai_match_pct, reverse=True)
    confidence: ConfidenceLevel = "high" if normalized_score >= 700 else "medium" if normalized_score >= 580 else "low"
    return MarketplaceResponse(
        score_used=normalized_score,
        confidence=confidence,
        offers=offers,
        disclaimer=MARKETPLACE_DISCLAIMER,
    )
