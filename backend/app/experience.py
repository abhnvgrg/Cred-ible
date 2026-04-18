from __future__ import annotations

import time
from secrets import token_urlsafe
from uuid import uuid4

from .schemas import (
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


def _confidence_from_delta(delta: int) -> ConfidenceLevel:
    magnitude = abs(delta)
    if magnitude <= 24:
        return "high"
    if magnitude <= 55:
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

    modifier = (
        payload.income_shift * 2.1
        + payload.compliance_boost * 2.7
        + payload.debt_reduction * 1.8
    )
    projected_score = _clamp_score(payload.base_score + modifier)
    delta = projected_score - payload.base_score
    confidence = _confidence_from_delta(delta)
    base_risk = _risk_level_from_score(payload.base_score)
    projected_risk = _risk_level_from_score(projected_score)

    recommendations = [
        WhatIfRecommendation(
            title="Income stability uplift",
            impact="high" if payload.income_shift >= 12 else "medium",
            note="Maintain recurring inflows and proof-backed income records for 90+ days.",
        ),
        WhatIfRecommendation(
            title="Compliance regularity",
            impact="high" if payload.compliance_boost >= 12 else "medium",
            note="Sustain on-time GST/utility behavior to improve lender trust calibration.",
        ),
        WhatIfRecommendation(
            title="Debt stress reduction",
            impact="high" if payload.debt_reduction >= 12 else "low",
            note="Lower utilization and avoid clustered inquiries during underwriting windows.",
        ),
    ]

    explanation = (
        f"Starting from {payload.base_score}, simulated adjustments produced a projected score of "
        f"{projected_score} ({delta:+d}). Risk level moved from {base_risk} to {projected_risk}. "
        "The strongest effect came from compliance and income stability movements, while debt stress "
        "reduction provided a supporting lift."
    )

    processing_time_ms = int((time.perf_counter() - started) * 1000)
    return WhatIfResponse(
        base_score=payload.base_score,
        projected_score=projected_score,
        score_delta=delta,
        projected_risk_level=projected_risk,
        confidence=confidence,
        explanation=explanation,
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
