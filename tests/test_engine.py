"""Behavioural tests for the corrected engine."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from smem import (
    ImprovementRates,
    Levers,
    ModelInputs,
    SalesMechanics,
    Scenario,
    apply_levers,
    evaluate,
    impact,
    ramp_productivity,
    rep_economics,
    run_all,
)
from smem.legacy import LEGACY_LOADED_SALARY

BASE = ModelInputs()


# ----------------------------------------------------------------- inputs


def test_defaults_reproduce_data_entry_sheet() -> None:
    assert BASE.compensation.fully_loaded_salary == pytest.approx(116_850)
    assert BASE.travel.cost_per_trip == pytest.approx(1_900)
    assert BASE.travel.annual_cost == pytest.approx(47_500)
    assert BASE.overhead.total == pytest.approx(10_800_000)
    assert BASE.marketing.total == pytest.approx(3_700_000)
    assert BASE.total_sales_and_marketing_overhead == pytest.approx(14_500_000)
    assert BASE.implied_avg_revenue_per_transaction == pytest.approx(25_000_000 / 755)


def test_inputs_are_immutable_and_strict() -> None:
    with pytest.raises(ValidationError):
        BASE.territories = 1  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelInputs(territoriez=5)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        SalesMechanics(close_rate=1.5)
    with pytest.raises(ValidationError):
        SalesMechanics(cycle_months=0)


# ----------------------------------------------------------------- per-rep


def test_rep_economics_baseline() -> None:
    rep = rep_economics(BASE)
    assert rep.opportunities_per_year == pytest.approx(60)
    assert rep.deals_per_year == pytest.approx(15)
    assert rep.revenue == pytest.approx(1_125_000)
    assert rep.commission == pytest.approx(90_000)
    # Corrected: uses the linked 116,850, not the legacy 87,750.
    assert rep.total_cost == pytest.approx(116_850 + 47_500 + 90_000)
    assert rep.total_cost - (LEGACY_LOADED_SALARY + 47_500 + 90_000) == pytest.approx(29_100)


def test_revenue_engine_identity() -> None:
    """R = T · (12P/C) · w · A."""
    m = BASE.mechanics
    expected = (
        BASE.territories
        * (12 * m.concurrent_opportunities / m.cycle_months)
        * m.close_rate
        * BASE.avg_revenue_per_transaction
    )
    assert evaluate(BASE).revenue == pytest.approx(expected)


# ----------------------------------------------------------------- levers


def test_apply_levers_is_identity_at_baseline() -> None:
    assert apply_levers(BASE, Levers()) is BASE


def test_levers_scale_the_right_fields() -> None:
    s = apply_levers(
        BASE,
        Levers(
            territory_change=0.1,
            close_rate_change=0.1,
            cycle_time_reduction=0.1,
            deal_size_change=0.1,
        ),
    )
    assert s.territories == pytest.approx(110)
    assert s.mechanics.close_rate == pytest.approx(0.275)
    assert s.mechanics.cycle_months == pytest.approx(5.4)
    assert s.avg_revenue_per_transaction == pytest.approx(82_500)
    # untouched
    assert s.mechanics.concurrent_opportunities == BASE.mechanics.concurrent_opportunities
    assert s.compensation == BASE.compensation


def test_close_rate_is_capped_at_one() -> None:
    s = apply_levers(BASE, Levers(close_rate_change=5.0))
    assert s.mechanics.close_rate == 1.0


# ----------------------------------------------------------------- elasticity


def test_cycle_time_lever_is_hyperbolic_not_linear() -> None:
    """A 10% cycle cut yields 1/0.9 − 1 = 11.1% revenue, versus 10% for the linear levers."""
    close = impact(BASE, Levers(close_rate_change=0.10)).revenue_growth_pct
    deal = impact(BASE, Levers(deal_size_change=0.10)).revenue_growth_pct
    cycle = impact(BASE, Levers(cycle_time_reduction=0.10)).revenue_growth_pct
    assert close == pytest.approx(0.10)
    assert deal == pytest.approx(0.10)
    assert cycle == pytest.approx(1 / 0.9 - 1)


# ----------------------------------------------------------------- ramp


@pytest.mark.parametrize(("ramp", "expected"), [(0, 1.0), (6, 0.5), (12, 0.0), (18, 0.0)])
def test_ramp_productivity(ramp: float, expected: float) -> None:
    assert ramp_productivity(ramp) == expected


def test_hiring_with_full_year_ramp_adds_cost_but_no_revenue() -> None:
    i = impact(BASE, Levers(territory_change=0.10))
    assert i.revenue_delta == 0
    assert i.rep_cost_delta == pytest.approx(10 * rep_economics(BASE).total_cost)
    assert i.net_gain_pct < 0


def test_removing_territories_removes_full_revenue() -> None:
    i = impact(BASE, Levers(territory_change=-0.10))
    assert i.revenue_delta == pytest.approx(-0.10 * i.baseline.revenue)


def test_combined_scenario_is_consistent_with_hire_scenario() -> None:
    """Regression for legacy defect Q2.

    New hires in the combined column must earn exactly what new hires earn in the
    hire-only column, scaled by the improved revenue-per-rep — never a full year.
    """
    six_month_ramp = BASE.model_copy(
        update={"mechanics": BASE.mechanics.model_copy(update={"ramp_months": 6.0})}
    )
    rates = ImprovementRates()
    results = run_all(six_month_ramp, rates)
    prod = results[Scenario.PRODUCTIVITY].scenario
    combined = results[Scenario.ALL].scenario
    new_reps = combined.inputs.territories - six_month_ramp.territories
    expected = prod.revenue + new_reps * prod.rep.revenue * 0.5
    assert combined.revenue == pytest.approx(expected)


# ----------------------------------------------------------------- income statement


def test_income_statement_sums() -> None:
    r = evaluate(BASE)
    assert r.total_sales_costs == pytest.approx(r.rep_costs + 10_800_000)
    assert r.sales_and_marketing == pytest.approx(r.total_sales_costs + 3_700_000)
    assert r.total_operating_expenses == pytest.approx(
        r.cost_of_revenue
        + r.research_and_development
        + r.sales_and_marketing
        + r.general_and_administrative
    )
    assert r.operating_income == pytest.approx(r.revenue - r.total_operating_expenses)
    assert 0 < r.operating_margin < 1


def test_operating_income_is_affine_in_revenue() -> None:
    """OI = R·(1 − c − cogs − rd − ga) − T·fixed_rep − OH − M."""
    r = evaluate(BASE)
    variable = 1 - BASE.compensation.commission_rate - BASE.ratios.total
    fixed = BASE.territories * r.rep.fixed_cost + BASE.overhead.total + BASE.marketing.total
    assert r.operating_income == pytest.approx(r.revenue * variable - fixed)


def test_run_all_returns_every_scenario() -> None:
    results = run_all(BASE)
    assert set(results) == set(Scenario)
    # Monotone: the all-levers column is at least as good on revenue as any single lever.
    best_single = max(
        results[s].scenario.revenue for s in (Scenario.CLOSE, Scenario.CYCLE, Scenario.DEAL)
    )
    assert results[Scenario.ALL].scenario.revenue >= best_single
