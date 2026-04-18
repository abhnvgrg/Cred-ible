from __future__ import annotations

import math
import time
from secrets import token_urlsafe
from uuid import uuid4

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


def _bounded_shift_gain(shift: int, current_component: int, max_gain: float) -> float:
    if shift <= 0:
        return 0.0
    normalized_shift = min(1.0, shift / 20)
    headroom = max(0.0, min(1.0, (100 - current_component) / 100))
    # Square-root scaling keeps monotonic gains while introducing realistic diminishing returns.
    return max_gain * math.sqrt(normalized_shift) * (0.35 + (0.65 * headroom))


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
    return (
        _clamp_component(internal_score + 3),
        _clamp_component(internal_score + 1),
        _clamp_component(internal_score - 2),
    )


def _scenario_confidence(
    payload: WhatIfRequest,
    base_breakdown_was_derived: bool,
) -> ConfidenceLevel:
    magnitude = payload.income_shift + payload.compliance_boost + payload.debt_reduction
    if magnitude <= 16:
        confidence: ConfidenceLevel = "high"
    elif magnitude <= 38:
        confidence = "medium"
    else:
        confidence = "low"

    if base_breakdown_was_derived and confidence == "high":
        return "medium"
    if base_breakdown_was_derived and confidence == "medium":
        return "low"
    return confidence


def _recommendation_impact(value: float) -> str:
    if value >= 12:
        return "high"
    if value >= 6:
        return "medium"
    return "low"


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

    income_gain = _bounded_shift_gain(payload.income_shift, base_income, max_gain=15.0)
    compliance_repayment_gain = _bounded_shift_gain(
        payload.compliance_boost,
        base_repayment,
        max_gain=10.5,
    )
    compliance_lifestyle_gain = _bounded_shift_gain(
        payload.compliance_boost,
        base_lifestyle,
        max_gain=6.5,
    )
    debt_repayment_gain = _bounded_shift_gain(payload.debt_reduction, base_repayment, max_gain=14.0)
    debt_income_gain = _bounded_shift_gain(payload.debt_reduction, base_income, max_gain=4.5)
    debt_lifestyle_gain = _bounded_shift_gain(payload.debt_reduction, base_lifestyle, max_gain=3.0)

    projected_income = _clamp_component(base_income + income_gain + debt_income_gain)
    projected_repayment = _clamp_component(base_repayment + compliance_repayment_gain + debt_repayment_gain)
    projected_lifestyle = _clamp_component(base_lifestyle + compliance_lifestyle_gain + debt_lifestyle_gain)

    base_internal_from_components = (
        (base_income * 0.4) + (base_repayment * 0.4) + (base_lifestyle * 0.2)
    )
    projected_internal_from_components = (
        (projected_income * 0.4) + (projected_repayment * 0.4) + (projected_lifestyle * 0.2)
    )
    internal_alignment = _internal_from_score(payload.base_score) - base_internal_from_components

    compliance_penalty = float(payload.rbi_flags_count) * 1.2
    if payload.compliance_status == "review":
        compliance_penalty += 4.0
    elif payload.compliance_status == "fail":
        compliance_penalty += 9.0

    penalty_relief = min(0.75, payload.compliance_boost / 26)
    projected_penalty = compliance_penalty * (1 - penalty_relief)

    projected_internal = projected_internal_from_components + internal_alignment - projected_penalty
    projected_score = _score_from_internal(projected_internal)
    if payload.income_shift == 0 and payload.compliance_boost == 0 and payload.debt_reduction == 0:
        projected_score = payload.base_score
    else:
        projected_score = max(payload.base_score, projected_score)

    delta = projected_score - payload.base_score
    confidence = _scenario_confidence(payload, base_breakdown_was_derived)
    base_risk = _risk_level_from_score(payload.base_score)
    projected_risk = _risk_level_from_score(projected_score)

    component_impacts = {
        "income": projected_income - base_income,
        "repayment": projected_repayment - base_repayment,
        "lifestyle": projected_lifestyle - base_lifestyle,
    }
    projected_compliance = "pass" if payload.compliance_boost >= 10 and payload.rbi_flags_count <= 1 else "review"

    recommendations = [
        WhatIfRecommendation(
            title="Income stability uplift",
            impact=_recommendation_impact(income_gain + debt_income_gain),
            note=(
                "Prioritize recurring proof-backed inflows and reduce month-to-month volatility to lift the "
                "income component."
            ),
        ),
        WhatIfRecommendation(
            title="Compliance regularity",
            impact=_recommendation_impact(compliance_repayment_gain + compliance_lifestyle_gain),
            note=(
                "Clear compliance flags first: on-time GST/utility discipline creates a direct score lift and "
                "reduces penalty drag."
            ),
        ),
        WhatIfRecommendation(
            title="Debt stress reduction",
            impact=_recommendation_impact(debt_repayment_gain),
            note=(
                "Lower utilization and smooth repayment cycles to improve repayment resilience in underwriting windows."
            ),
        ),
    ]

    explanation = (
        f"Starting from {payload.base_score}, simulated adjustments produced a projected score of "
        f"{projected_score} ({delta:+d}). Risk level moved from {base_risk} to {projected_risk}. "
        f"Component impact: income {component_impacts['income']:+d}, repayment {component_impacts['repayment']:+d}, "
        f"lifestyle {component_impacts['lifestyle']:+d}."
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
