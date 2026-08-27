from __future__ import annotations

import pytest

from app.resolver import (
    COMPONENT_WEIGHTS,
    _base_loan_band,
    _compliance_penalty,
    _format_inr,
    _risk_level_from_score,
    _scale_to_credit_band,
    resolve_scores,
)
from tests.factories import agent_score, compliance, strong_borrower, weak_borrower


def resolve(
    payload=None,
    income: int = 70,
    repayment: int = 70,
    lifestyle: int = 70,
    income_confidence: str = "high",
    repayment_confidence: str = "high",
    lifestyle_confidence: str = "high",
    rbi_compliant: bool = True,
    fraud_risk: str = "low",
    compliance_flags: list[str] | None = None,
):
    return resolve_scores(
        payload=payload if payload is not None else strong_borrower(),
        income=agent_score(income, income_confidence),
        repayment=agent_score(repayment, repayment_confidence),
        lifestyle=agent_score(lifestyle, lifestyle_confidence),
        compliance=compliance(rbi_compliant, fraud_risk, compliance_flags),
        processing_time_ms=42,
    )


def test_the_component_weights_sum_to_one():
    assert sum(COMPONENT_WEIGHTS.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "internal,expected",
    [(0.0, 300), (100.0, 850), (50.0, 575), (-10.0, 300), (200.0, 850)],
)
def test_the_internal_score_maps_onto_the_credit_band(internal, expected):
    assert _scale_to_credit_band(internal) == expected


def test_the_credit_band_never_leaves_its_bounds():
    for internal in range(-50, 200):
        assert 300 <= _scale_to_credit_band(float(internal)) <= 850


@pytest.mark.parametrize(
    "score,expected",
    [(850, "low"), (760, "low"), (759, "medium"), (620, "medium"), (619, "high"), (300, "high")],
)
def test_risk_bands_are_contiguous_at_their_boundaries(score, expected):
    assert _risk_level_from_score(score) == expected


@pytest.mark.parametrize(
    "amount,formatted",
    [
        (0, "₹0"),
        (999, "₹999"),
        (1000, "₹1,000"),
        (100000, "₹1,00,000"),
        (10000000, "₹1,00,00,000"),
    ],
)
def test_amounts_are_grouped_in_the_indian_system(amount, formatted):
    assert _format_inr(amount) == formatted


def test_negative_amounts_are_floored_at_zero():
    assert _format_inr(-5000) == "₹0"


def test_a_better_profile_never_scores_lower():
    weak = resolve(income=20, repayment=20, lifestyle=20)
    strong = resolve(income=90, repayment=90, lifestyle=90)

    assert strong.final_score > weak.final_score


@pytest.mark.parametrize("component", ["income", "repayment", "lifestyle"])
def test_raising_any_component_raises_the_score(component):
    baseline = resolve(income=50, repayment=50, lifestyle=50)
    raised = resolve(**{component: 90}, **{
        other: 50 for other in ("income", "repayment", "lifestyle") if other != component
    })

    assert raised.final_score > baseline.final_score


def test_income_and_repayment_move_the_score_more_than_lifestyle():
    baseline = resolve(income=50, repayment=50, lifestyle=50)
    via_income = resolve(income=90, repayment=50, lifestyle=50)
    via_lifestyle = resolve(income=50, repayment=50, lifestyle=90)

    income_gain = via_income.final_score - baseline.final_score
    lifestyle_gain = via_lifestyle.final_score - baseline.final_score

    assert income_gain > lifestyle_gain


def test_component_contributions_reconstruct_the_weighted_score():
    result = resolve(income=80, repayment=60, lifestyle=40)
    total = sum(result.component_contributions.values())

    assert total == pytest.approx(80 * 0.4 + 60 * 0.4 + 40 * 0.2)
    assert result.final_score == _scale_to_credit_band(total)


def test_the_explanation_quotes_the_scores_it_used():
    result = resolve(income=81, repayment=62, lifestyle=43)

    assert "81" in result.explanation
    assert "62" in result.explanation
    assert "43" in result.explanation
    assert str(result.final_score) in result.explanation


def test_a_perfect_profile_reaches_the_top_of_the_band():
    assert resolve(income=100, repayment=100, lifestyle=100).final_score == 850


def test_a_zero_profile_sits_at_the_floor():
    assert resolve(income=0, repayment=0, lifestyle=0).final_score == 300


@pytest.mark.parametrize(
    "fraud_risk,expected_extra", [("low", 0.0), ("medium", 8.0), ("high", 18.0)]
)
def test_fraud_risk_adds_a_graded_penalty(fraud_risk, expected_extra):
    assert _compliance_penalty(compliance(fraud_risk=fraud_risk)) == expected_extra


def test_non_compliance_adds_a_penalty():
    assert _compliance_penalty(compliance(rbi_compliant=False)) == 10.0


def test_compliance_flags_add_a_capped_penalty():
    few = _compliance_penalty(compliance(flags=["a", "b"]))
    many = _compliance_penalty(compliance(flags=[str(n) for n in range(50)]))

    assert few == pytest.approx(3.6)
    assert many == 14.0


def test_the_total_compliance_penalty_is_capped():
    worst = _compliance_penalty(
        compliance(
            rbi_compliant=False,
            fraud_risk="high",
            flags=[str(n) for n in range(50)],
        )
    )
    assert worst == 36.0


def test_compliance_penalties_lower_the_final_score():
    clean = resolve(income=80, repayment=80, lifestyle=80)
    flagged = resolve(income=80, repayment=80, lifestyle=80, fraud_risk="high")

    assert flagged.final_score < clean.final_score


def test_a_high_fraud_risk_is_surfaced_as_a_flag():
    result = resolve(fraud_risk="high")

    assert any("fraud" in flag.lower() for flag in result.rbi_flags)
    assert result.agent_breakdown.compliance == "review"


def test_non_compliance_is_surfaced_as_a_flag():
    result = resolve(rbi_compliant=False)

    assert any("RBI" in flag for flag in result.rbi_flags)
    assert result.agent_breakdown.compliance == "review"


def test_a_clean_profile_passes_compliance():
    assert resolve().agent_breakdown.compliance == "pass"


def test_compliance_flags_are_carried_through():
    result = resolve(compliance_flags=["Address mismatch"])

    assert "Address mismatch" in result.rbi_flags


def test_agreeing_high_confidence_agents_give_high_confidence():
    assert resolve(income=80, repayment=80, lifestyle=80).confidence == "high"


def test_low_confidence_agents_drag_confidence_down():
    result = resolve(
        income_confidence="low", repayment_confidence="low", lifestyle_confidence="low"
    )
    assert result.confidence == "low"


def test_disagreement_between_agents_lowers_confidence():
    agreed = resolve(income=70, repayment=70, lifestyle=70)
    split = resolve(income=100, repayment=70, lifestyle=0)

    order = {"low": 0, "medium": 1, "high": 2}
    assert order[split.confidence] <= order[agreed.confidence]


def test_non_compliance_lowers_confidence():
    clean = resolve(income=75, repayment=75, lifestyle=75)
    dirty = resolve(income=75, repayment=75, lifestyle=75, rbi_compliant=False)

    order = {"low": 0, "medium": 1, "high": 2}
    assert order[dirty.confidence] < order[clean.confidence]


@pytest.mark.parametrize(
    "score,expected_floor",
    [(450, 20_000), (600, 50_000), (700, 150_000), (800, 220_000), (840, 300_000)],
)
def test_loan_bands_rise_with_the_score(score, expected_floor):
    assert _base_loan_band(score)[0] == expected_floor


def test_loan_bands_are_ordered_and_non_overlapping():
    floors = [_base_loan_band(score)[0] for score in (450, 600, 700, 800, 840)]
    assert floors == sorted(floors)
    for score in (450, 600, 700, 800, 840):
        low, high = _base_loan_band(score)
        assert low < high


def test_the_recommended_limit_is_a_formatted_range():
    limit = resolve().recommended_loan_limit

    assert "₹" in limit
    assert " - " in limit


def test_a_higher_income_recommends_a_higher_limit():
    modest = resolve(payload=strong_borrower(employment={"monthly_income_inr": 25000.0}))
    wealthy = resolve(payload=strong_borrower(employment={"monthly_income_inr": 200000.0}))

    def floor(text: str) -> int:
        return int(text.split(" - ")[0].replace("₹", "").replace(",", ""))

    assert floor(wealthy.recommended_loan_limit) > floor(modest.recommended_loan_limit)


def test_repayment_stress_lowers_the_recommended_limit():
    steady = resolve(payload=strong_borrower())
    stressed = resolve(
        payload=strong_borrower(
            rent={"longest_gap_months": 6, "late_payments_last_24m": 12},
            existing_emi_on_time_ratio=0.4,
        )
    )

    def floor(text: str) -> int:
        return int(text.split(" - ")[0].replace("₹", "").replace(",", ""))

    assert floor(stressed.recommended_loan_limit) < floor(steady.recommended_loan_limit)


def test_a_strong_profile_produces_positive_factors():
    result = resolve(payload=strong_borrower(), income=85, repayment=85, lifestyle=85)

    assert result.positive_factors
    assert len(result.positive_factors) <= 3


def test_a_weak_profile_produces_risk_factors():
    result = resolve(payload=weak_borrower(), income=25, repayment=25, lifestyle=25)

    assert result.risk_factors
    assert len(result.risk_factors) <= 3


def test_factor_messages_are_not_duplicated():
    result = resolve(payload=weak_borrower(), income=20, repayment=20, lifestyle=20)

    assert len(set(result.risk_factors)) == len(result.risk_factors)


def test_the_disclaimer_is_always_present():
    assert "not a guarantee" in resolve().disclaimer


def test_the_processing_time_is_reported_as_given():
    assert resolve().processing_time_ms == 42


def test_the_agent_outputs_are_returned_for_audit():
    result = resolve(income=61, repayment=62, lifestyle=63)

    assert result.agent_outputs["income"].score == 61
    assert result.agent_outputs["repayment"].score == 62
    assert result.agent_outputs["lifestyle"].score == 63
    assert result.agent_outputs["compliance"].rbi_compliant is True


def test_scoring_is_deterministic():
    first = resolve(payload=strong_borrower(), income=73, repayment=64, lifestyle=55)
    second = resolve(payload=strong_borrower(), income=73, repayment=64, lifestyle=55)

    assert first.final_score == second.final_score
    assert first.confidence == second.confidence
    assert first.recommended_loan_limit == second.recommended_loan_limit
