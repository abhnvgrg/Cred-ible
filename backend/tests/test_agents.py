from __future__ import annotations

import pytest

from app.agents import (
    _band_score,
    _inverse_ratio,
    _ratio,
    _trend_score,
    compliance_and_fraud_agent,
    income_stability_agent,
    lifestyle_risk_agent,
    repayment_behaviour_agent,
    run_all_agents,
)
from tests.factories import strong_borrower, weak_borrower

pytestmark = pytest.mark.asyncio

SCORING_AGENTS = [
    income_stability_agent,
    repayment_behaviour_agent,
    lifestyle_risk_agent,
]


@pytest.mark.parametrize(
    "value,target,expected",
    [(0, 100, 0.0), (50, 100, 0.5), (100, 100, 1.0), (200, 100, 1.0), (-10, 100, 0.0)],
)
async def test_ratio_is_clamped_to_the_unit_interval(value, target, expected):
    assert _ratio(value, target) == pytest.approx(expected)


async def test_inverse_ratio_falls_as_the_value_rises():
    assert _inverse_ratio(0, 10) > _inverse_ratio(5, 10) > _inverse_ratio(10, 10)


async def test_inverse_ratio_is_clamped():
    assert 0.0 <= _inverse_ratio(1000, 10) <= 1.0


async def test_a_declining_trend_scores_below_a_rising_one():
    assert _trend_score(-50) < _trend_score(0) < _trend_score(50)


async def test_trend_scores_stay_in_the_unit_interval():
    for trend in range(-100, 300, 10):
        assert 0.0 <= _trend_score(float(trend)) <= 1.0


async def test_band_score_peaks_inside_the_band():
    inside = _band_score(50, low=40, high=60, hard_upper=100)
    below = _band_score(10, low=40, high=60, hard_upper=100)
    above = _band_score(95, low=40, high=60, hard_upper=100)

    assert inside >= below
    assert inside >= above


@pytest.mark.parametrize("agent", SCORING_AGENTS)
async def test_every_scoring_agent_stays_inside_its_range(agent):
    for payload in (strong_borrower(), weak_borrower()):
        result = await agent(payload)
        assert 0 <= result.score <= 100
        assert result.confidence in {"high", "medium", "low"}
        assert len(result.reasoning) >= 10


@pytest.mark.parametrize("agent", SCORING_AGENTS)
async def test_every_scoring_agent_prefers_the_strong_profile(agent):
    strong = await agent(strong_borrower())
    weak = await agent(weak_borrower())

    assert strong.score > weak.score


@pytest.mark.parametrize("agent", SCORING_AGENTS)
async def test_every_scoring_agent_is_deterministic(agent):
    payload = strong_borrower()
    first = await agent(payload)
    second = await agent(payload)

    assert first.score == second.score
    assert first.flags == second.flags


async def test_income_falls_when_upi_volume_is_collapsing():
    steady = await income_stability_agent(
        strong_borrower(upi={"monthly_volume_trend_pct": 5.0})
    )
    collapsing = await income_stability_agent(
        strong_borrower(upi={"monthly_volume_trend_pct": -60.0})
    )

    assert collapsing.score < steady.score
    assert any("declining" in flag.lower() for flag in collapsing.flags)


async def test_self_declared_income_is_penalised_and_flagged():
    documented = await income_stability_agent(
        strong_borrower(employment={"income_proof_type": "salary_slip"})
    )
    declared = await income_stability_agent(
        strong_borrower(employment={"income_proof_type": "self_declared"})
    )

    assert declared.score < documented.score
    assert any("self-declared" in flag.lower() for flag in declared.flags)


async def test_missed_gst_filings_are_counted_in_the_flag():
    result = await income_stability_agent(
        strong_borrower(gst={"missed_filings_last_12m": 3})
    )

    assert any("3 missed GST filing" in flag for flag in result.flags)


async def test_more_missed_filings_score_lower():
    few = await income_stability_agent(strong_borrower(gst={"missed_filings_last_12m": 1}))
    many = await income_stability_agent(strong_borrower(gst={"missed_filings_last_12m": 9}))

    assert many.score < few.score


async def test_a_borrower_without_gst_is_still_scored():
    result = await income_stability_agent(strong_borrower(gst=None))

    assert 0 <= result.score <= 100


async def test_longer_work_tenure_scores_higher():
    new = await income_stability_agent(
        strong_borrower(employment={"months_in_current_work": 1})
    )
    established = await income_stability_agent(
        strong_borrower(employment={"months_in_current_work": 120})
    )

    assert established.score > new.score


async def test_repayment_falls_with_missed_rent():
    reliable = await repayment_behaviour_agent(
        strong_borrower(rent={"on_time_payment_ratio": 1.0, "late_payments_last_24m": 0})
    )
    unreliable = await repayment_behaviour_agent(
        strong_borrower(rent={"on_time_payment_ratio": 0.4, "late_payments_last_24m": 15})
    )

    assert unreliable.score < reliable.score


async def test_repayment_falls_with_missed_utilities():
    paid = await repayment_behaviour_agent(
        strong_borrower(
            utilities={"electricity_on_time_ratio": 1.0, "water_on_time_ratio": 1.0}
        )
    )
    unpaid = await repayment_behaviour_agent(
        strong_borrower(
            utilities={"electricity_on_time_ratio": 0.3, "water_on_time_ratio": 0.2}
        )
    )

    assert unpaid.score < paid.score


async def test_a_long_payment_gap_lowers_repayment():
    unbroken = await repayment_behaviour_agent(strong_borrower(rent={"longest_gap_months": 0}))
    broken = await repayment_behaviour_agent(strong_borrower(rent={"longest_gap_months": 9}))

    assert broken.score < unbroken.score


async def test_existing_emi_discipline_matters():
    disciplined = await repayment_behaviour_agent(
        strong_borrower(existing_emi_on_time_ratio=1.0)
    )
    erratic = await repayment_behaviour_agent(
        strong_borrower(existing_emi_on_time_ratio=0.3)
    )

    assert erratic.score < disciplined.score


async def test_risky_app_usage_lowers_lifestyle():
    clean = await lifestyle_risk_agent(strong_borrower(mobile={"risky_app_usage_score": 0.0}))
    risky = await lifestyle_risk_agent(strong_borrower(mobile={"risky_app_usage_score": 0.95}))

    assert risky.score < clean.score


async def test_finance_app_usage_helps_lifestyle():
    none = await lifestyle_risk_agent(strong_borrower(mobile={"finance_app_usage_score": 0.0}))
    engaged = await lifestyle_risk_agent(
        strong_borrower(mobile={"finance_app_usage_score": 1.0})
    )

    assert engaged.score >= none.score


async def test_erratic_recharges_lower_lifestyle():
    consistent = await lifestyle_risk_agent(strong_borrower(mobile={"consistency_score": 0.95}))
    erratic = await lifestyle_risk_agent(strong_borrower(mobile={"consistency_score": 0.05}))

    assert erratic.score < consistent.score


async def test_a_clean_borrower_passes_compliance():
    result = await compliance_and_fraud_agent(strong_borrower())

    assert result.rbi_compliant is True
    assert result.fraud_risk == "low"


async def test_compliance_output_is_well_formed():
    for payload in (strong_borrower(), weak_borrower()):
        result = await compliance_and_fraud_agent(payload)
        assert result.fraud_risk in {"low", "medium", "high"}
        assert isinstance(result.rbi_compliant, bool)
        assert len(result.notes) >= 5


async def test_a_weak_borrower_attracts_more_scrutiny():
    clean = await compliance_and_fraud_agent(strong_borrower())
    risky = await compliance_and_fraud_agent(weak_borrower())

    order = {"low": 0, "medium": 1, "high": 2}
    assert order[risky.fraud_risk] >= order[clean.fraud_risk]


async def test_prohibited_attributes_are_caught():
    result = await compliance_and_fraud_agent(
        strong_borrower(declared_attributes={"religion": "hindu", "caste": "general"})
    )

    assert result.rbi_compliant is False
    assert result.flags


async def test_neutral_attributes_are_not_caught():
    result = await compliance_and_fraud_agent(
        strong_borrower(declared_attributes={"city": "Delhi", "language": "Hindi"})
    )

    assert result.rbi_compliant is True


async def test_running_all_agents_returns_every_output():
    outputs = await run_all_agents(strong_borrower())

    assert set(outputs) == {"income", "repayment", "lifestyle", "compliance"}
    for name in ("income", "repayment", "lifestyle"):
        assert 0 <= outputs[name].score <= 100
    assert outputs["compliance"].fraud_risk in {"low", "medium", "high"}


async def test_running_all_agents_is_deterministic():
    payload = strong_borrower()
    first = await run_all_agents(payload)
    second = await run_all_agents(payload)

    scores = lambda out: [out[name].score for name in ("income", "repayment", "lifestyle")]
    assert scores(first) == scores(second)


async def test_the_orchestrator_matches_the_individual_agents_without_an_llm():
    payload = strong_borrower()
    outputs = await run_all_agents(payload)

    assert outputs["income"].score == (await income_stability_agent(payload)).score
    assert outputs["repayment"].score == (await repayment_behaviour_agent(payload)).score
    assert outputs["lifestyle"].score == (await lifestyle_risk_agent(payload)).score


async def test_extreme_but_valid_inputs_do_not_break_any_agent():
    floor = weak_borrower(
        upi={
            "transaction_frequency_per_month": 0,
            "average_transaction_value_inr": 0.0,
            "merchant_diversity_score": 0.0,
            "regularity_score": 0.0,
            "months_of_history": 1,
            "monthly_volume_trend_pct": -100.0,
        },
        employment={"monthly_income_inr": 0.0, "months_in_current_work": 0},
        existing_emi_on_time_ratio=0.0,
    )

    outputs = await run_all_agents(floor)

    for name in ("income", "repayment", "lifestyle"):
        assert 0 <= outputs[name].score <= 100
    assert outputs["compliance"].fraud_risk in {"low", "medium", "high"}
