from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

import joblib
import numpy as np
from fastapi import APIRouter

from ..ml_model import MODEL_PATH, model_is_trained
from ..schemas.simulate import (
    AgentDeltas,
    ScoreSimulationRequest,
    ScoreSimulationResponse,
)

router = APIRouter(prefix="/score", tags=["score-simulation"])

FEATURE_COEFFICIENTS: dict[str, float] = {
    "utility_bill_ontime_pct": 0.45,
    "savings_rate_pct": 0.38,
    "upi_monthly_txn_count": 1.2,
    "months_of_history": 3.5,
    "debt_to_income_ratio": -85.0,
    "gst_compliance_score": 42.0,
}

FEATURE_TO_AGENT_WEIGHTS: dict[str, dict[str, float]] = {
    "utility_bill_ontime_pct": {"repayment_agent": 0.7, "lifestyle_agent": 0.2, "compliance_agent": 0.1},
    "savings_rate_pct": {"lifestyle_agent": 0.5, "income_agent": 0.3, "repayment_agent": 0.2},
    "upi_monthly_txn_count": {"lifestyle_agent": 0.6, "income_agent": 0.4},
    "months_of_history": {"income_agent": 0.5, "compliance_agent": 0.5},
    "debt_to_income_ratio": {"repayment_agent": 1.0},
    "gst_compliance_score": {"compliance_agent": 1.0},
}


def _clip_score(value: float) -> int:
    return int(max(300, min(900, round(value))))


def _safe_float(value: float) -> float:
    if isfinite(value):
        return float(value)
    return 0.0


def _derive_coefficients_from_model() -> dict[str, float]:
    if not model_is_trained() or not MODEL_PATH.exists():
        return FEATURE_COEFFICIENTS

    try:
        artifact: dict = joblib.load(MODEL_PATH)
        pipeline = artifact.get("pipeline")
        if pipeline is None:
            return FEATURE_COEFFICIENTS

        model = pipeline.named_steps.get("model")
        preprocessor = pipeline.named_steps.get("preprocessor")
        if model is None or preprocessor is None or not hasattr(model, "feature_importances_"):
            return FEATURE_COEFFICIENTS

        feature_names = preprocessor.get_feature_names_out()
        importances = np.asarray(model.feature_importances_, dtype=float)
        if len(feature_names) != len(importances):
            return FEATURE_COEFFICIENTS

        buckets: dict[str, float] = {key: 0.0 for key in FEATURE_COEFFICIENTS}
        for name, importance in zip(feature_names, importances):
            lowered = str(name).lower()
            if "upi" in lowered and ("txn" in lowered or "transaction" in lowered):
                buckets["upi_monthly_txn_count"] += float(importance)
            if "utility" in lowered or "electricity" in lowered or "water" in lowered:
                buckets["utility_bill_ontime_pct"] += float(importance)
            if "cash" in lowered or "flow" in lowered or "income" in lowered or "balance" in lowered:
                buckets["savings_rate_pct"] += float(importance)
            if "month" in lowered or "history" in lowered:
                buckets["months_of_history"] += float(importance)
            if "debt" in lowered or "emi" in lowered or "loan" in lowered:
                buckets["debt_to_income_ratio"] += float(importance)
            if "gst" in lowered or "compliance" in lowered:
                buckets["gst_compliance_score"] += float(importance)

        total_bucket_weight = sum(buckets.values())
        if total_bucket_weight <= 0:
            return FEATURE_COEFFICIENTS

        fallback_total = sum(abs(value) for value in FEATURE_COEFFICIENTS.values())
        if fallback_total <= 0:
            return FEATURE_COEFFICIENTS

        derived: dict[str, float] = {}
        for feature, fallback_value in FEATURE_COEFFICIENTS.items():
            if buckets[feature] <= 0:
                derived[feature] = fallback_value
                continue
            scaled = (buckets[feature] / total_bucket_weight) * fallback_total
            derived[feature] = scaled if fallback_value >= 0 else -scaled

        return derived
    except Exception:
        return FEATURE_COEFFICIENTS


def _delta_breakdown(
    current: Mapping[str, float],
    projected: Mapping[str, float],
    coefficients: Mapping[str, float],
) -> dict[str, float]:
    delta_by_feature: dict[str, float] = {}
    for feature, coefficient in coefficients.items():
        current_value = _safe_float(current.get(feature, 0.0))
        projected_value = _safe_float(projected.get(feature, 0.0))
        delta_by_feature[feature] = (projected_value - current_value) * coefficient
    return delta_by_feature


def _agent_deltas(delta_by_feature: Mapping[str, float]) -> AgentDeltas:
    buckets = {
        "income_agent": 0.0,
        "repayment_agent": 0.0,
        "lifestyle_agent": 0.0,
        "compliance_agent": 0.0,
    }
    for feature, feature_delta in delta_by_feature.items():
        for agent, weight in FEATURE_TO_AGENT_WEIGHTS.get(feature, {}).items():
            buckets[agent] += feature_delta * weight

    return AgentDeltas(
        income_agent=int(round(buckets["income_agent"])),
        repayment_agent=int(round(buckets["repayment_agent"])),
        lifestyle_agent=int(round(buckets["lifestyle_agent"])),
        compliance_agent=int(round(buckets["compliance_agent"])),
    )


def _confidence(delta_by_feature: Mapping[str, float], model_backed: bool) -> float:
    changed_features = sum(1 for value in delta_by_feature.values() if abs(value) > 0.01)
    change_bonus = min(0.12, changed_features * 0.02)
    base = 0.78 + change_bonus
    if model_backed:
        base += 0.06
    return max(0.55, min(0.95, round(base, 2)))


@router.post("/simulate", response_model=ScoreSimulationResponse)
async def simulate_score(payload: ScoreSimulationRequest) -> ScoreSimulationResponse:
    current_signals = payload.current_signals.model_dump()
    projected_signals = payload.projected_signals.model_dump()

    model_coefficients = _derive_coefficients_from_model()
    model_backed = model_coefficients is not FEATURE_COEFFICIENTS

    baseline_score = payload.baseline_score if payload.baseline_score is not None else 300

    feature_deltas = _delta_breakdown(current_signals, projected_signals, model_coefficients)
    raw_delta = sum(feature_deltas.values())
    projected_score = _clip_score(float(baseline_score) + raw_delta)
    delta = projected_score - baseline_score

    positive_impacts = {key: value for key, value in feature_deltas.items() if value > 0}
    if positive_impacts:
        top_improvement = max(positive_impacts.items(), key=lambda item: item[1])[0]
    else:
        top_improvement = "utility_bill_ontime_pct"

    explanation = (
        f"{top_improvement} contributed the most to your projected score movement. "
        "Simulation uses calibrated signal coefficients and applies weighted feature deltas."
    )

    return ScoreSimulationResponse(
        baseline_score=baseline_score,
        projected_score=projected_score,
        delta=delta,
        top_improvement=top_improvement,
        explanation=explanation,
        agent_deltas=_agent_deltas(feature_deltas),
        confidence=_confidence(feature_deltas, model_backed=model_backed),
    )
