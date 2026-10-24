"""Spec §8 test matrix for engine v2.

baseline identity · scenario isolation · financial reconciliation · ramp consistency ·
cost integrity · input validation · dependency integrity · constraint enforcement ·
interaction · legacy parity.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from smem import Levers, ModelInputs
from smem import evaluate as v1_evaluate
from smem.assumptions import Baseline, Horizon, OperatingPolicy, RampPolicy, Source
from smem.compare import (
    CostToImprove,
    break_even_investment,
    equal_investment,
    equal_percentage,
    goal_seek,
    interaction_effect,
    risk_adjusted_delta,
    sensitivity,
)
from smem.finance import CostKind, evaluate, run
from smem.operating import managers_required, ramp_fraction, resolve
from smem.scenario import Intervention, Lever, LeverSet, Scenario, combine

B = Baseline.from_defaults()
HIRE = Scenario.of("hire", LeverSet(territory_change=0.10))
CLOSE = Scenario.of("close", LeverSet(close_rate_change=0.10))
CYCLE = Scenario.of("cycle", LeverSet(cycle_time_reduction=0.10))
DEAL = Scenario.of("deal", LeverSet(deal_size_change=0.10))
FIXED_PER_REP = 116_850 + 47_500


# ------------------------------------------------------------------ baseline identity


def test_empty_scenario_reproduces_baseline() -> None:
    b = run(B, Scenario.baseline())
    assert b.delta == 0
    assert [st.key for st in b.steps] == ["revenue"]  # revenue bar is always shown
    assert all(st.amount == 0 for st in b.steps)


def test_v2_baseline_equals_v1_engine_at_defaults() -> None:
    o = evaluate(B)
    v1 = v1_evaluate(ModelInputs())
    assert o.revenue == pytest.approx(v1.revenue)
    assert o.operating_income == pytest.approx(v1.operating_income)
    assert o.sales_and_marketing == pytest.approx(v1.sales_and_marketing)


@pytest.mark.parametrize("scenario", [CLOSE, CYCLE, DEAL])
def test_v2_matches_v1_for_free_instant_productivity_levers(scenario: Scenario) -> None:
    """Where the original's rules were already causally sound, v2 agrees with v1."""
    lv = scenario.effective_levers(Horizon.YEAR_ONE)
    v1 = v1_evaluate(
        ModelInputs(),
        Levers(
            close_rate_change=lv.close_rate_change,
            cycle_time_reduction=lv.cycle_time_reduction,
            deal_size_change=lv.deal_size_change,
        ),
    )
    assert evaluate(B, scenario).operating_income == pytest.approx(v1.operating_income)


# ------------------------------------------------------------------ scenario isolation


def test_scenarios_are_immutable_and_independent() -> None:
    s1 = Scenario.of("a", LeverSet(close_rate_change=0.1))
    s2 = s1.with_intervention(Intervention(name="b", levers=LeverSet(deal_size_change=0.1)))
    assert len(s1.interventions) == 1
    assert len(s2.interventions) == 2
    with pytest.raises(ValidationError):
        s1.name = "x"  # type: ignore[misc]


def test_baseline_with_value_does_not_mutate_original() -> None:
    b2 = B.with_value("mechanics.close_rate", 0.30, Source.ACTUAL, "CRM FY25")
    assert B.inputs.mechanics.close_rate == 0.25
    assert b2.inputs.mechanics.close_rate == 0.30
    assert b2.source_of("mechanics.close_rate") is Source.ACTUAL
    assert B.source_of("mechanics.close_rate") is Source.DEFAULT


# ------------------------------------------------------------------ reconciliation


@pytest.mark.parametrize(
    "scenario", [HIRE, CLOSE, CYCLE, DEAL, combine("all", [HIRE, CLOSE, CYCLE, DEAL])]
)
@pytest.mark.parametrize("horizon", list(Horizon))
def test_bridge_has_no_residual(scenario: Scenario, horizon: Horizon) -> None:
    b = run(B, scenario, horizon)
    assert b.residual == pytest.approx(0.0, abs=1e-6)
    assert b.scenario.revenue - b.scenario.total_expenses == pytest.approx(
        b.scenario.operating_income
    )
    assert sum(s.amount for s in b.steps) == pytest.approx(b.delta)


def test_bridge_steps_are_only_lines_that_changed() -> None:
    b = run(B, CLOSE)
    keys = {s.key for s in b.steps}
    assert keys == {"revenue", "cogs", "rd", "ga", "commission"}


# ------------------------------------------------------------------ ramp consistency


@pytest.mark.parametrize(
    ("ramp", "policy", "horizon", "expected"),
    [
        (12, RampPolicy.STEP, Horizon.YEAR_ONE, 0.0),
        (6, RampPolicy.STEP, Horizon.YEAR_ONE, 0.5),
        (12, RampPolicy.LINEAR, Horizon.YEAR_ONE, 0.5),
        (6, RampPolicy.LINEAR, Horizon.YEAR_ONE, 0.75),
        (12, RampPolicy.STEP, Horizon.STEADY_STATE, 1.0),
    ],
)
def test_ramp_fraction(ramp: float, policy: RampPolicy, horizon: Horizon, expected: float) -> None:
    assert ramp_fraction(ramp, policy, horizon) == pytest.approx(expected)


def test_combined_scenario_uses_same_ramp_as_hire_alone() -> None:
    """Regression for the original's defect Q2 at the v2 level."""
    both = run(B, combine("all", [HIRE, CLOSE, CYCLE, DEAL])).scenario.operating
    prod = run(B, combine("prod", [CLOSE, CYCLE, DEAL])).scenario.operating
    assert both.productive_equivalents == pytest.approx(100.0)  # 12-month ramp → hires add nothing
    assert both.revenue == pytest.approx(prod.revenue)


def test_removed_sellers_remove_full_capacity() -> None:
    st = resolve(B, LeverSet(territory_change=-0.2))
    assert st.productive_equivalents == pytest.approx(80)
    assert st.new_hires == 0


# ------------------------------------------------------------------ cost integrity


def test_no_commission_for_sellers_who_sell_nothing() -> None:
    """Causal rule: commission follows realised revenue, not headcount."""
    b = run(B, HIRE, Horizon.YEAR_ONE)
    assert b.revenue_delta == 0
    assert b.scenario.cost("commission") == b.baseline.cost("commission")
    assert b.delta == pytest.approx(-10 * FIXED_PER_REP)


def test_draw_is_charged_only_for_unproductive_seller_years() -> None:
    bd = B.with_policy(ramping_hire_draw=40_000)
    y1 = evaluate(bd, HIRE, Horizon.YEAR_ONE)
    ss = evaluate(bd, HIRE, Horizon.STEADY_STATE)
    assert y1.cost("draw") == pytest.approx(10 * 40_000)
    assert ss.cost("draw") == 0


def test_step_fixed_manager_cost() -> None:
    assert managers_required(100, 8) == 13
    assert managers_required(96, 8) == 12
    assert managers_required(100, None) == 0
    bm = B.with_policy(manager_span=10, manager_loaded_cost=200_000)
    assert evaluate(bm).cost("managers") == 0  # baseline managers are already in overhead
    assert evaluate(bm, HIRE).cost("managers") == pytest.approx(200_000)  # 110/10 = 11 vs 10


def test_every_cost_line_follows_its_declared_kind() -> None:
    o = evaluate(B, CLOSE)
    base = evaluate(B)
    for line in o:
        if line.kind is CostKind.FIXED:
            assert line.amount == base.cost(line.key)
        if line.kind is CostKind.VARIABLE:
            assert line.amount / o.revenue == pytest.approx(base.cost(line.key) / base.revenue)
        if line.kind is CostKind.FIXED_PER_SELLER and line.key == "rep_fixed":
            assert line.amount == pytest.approx(o.operating.employed_sellers * FIXED_PER_REP)


def test_programme_cost_is_discretionary_and_horizon_aware() -> None:
    s = Scenario.of(
        "enablement", LeverSet(close_rate_change=0.1), annual_cost=400_000, one_time_cost=250_000
    )
    assert evaluate(B, s, Horizon.YEAR_ONE).programme_cost == 650_000
    assert evaluate(B, s, Horizon.STEADY_STATE).programme_cost == 400_000


# ------------------------------------------------------------------ input validation


def test_invalid_inputs_rejected() -> None:
    with pytest.raises(ValidationError):
        LeverSet(cycle_time_reduction=1.0)
    with pytest.raises(ValidationError):
        Intervention(name="x", months_to_benefit=13)
    with pytest.raises(ValidationError):
        OperatingPolicy(manager_span=0)
    with pytest.raises(KeyError):
        B.with_value("mechanics.nope", 1, Source.ACTUAL)
    with pytest.raises(ValidationError):
        B.with_value("mechanics.close_rate", 1.5, Source.ACTUAL)


# ------------------------------------------------------------------ dependency integrity


def test_derived_values_follow_their_sources() -> None:
    b2 = B.with_value("compensation.base_salary", 100_000, Source.ACTUAL)
    assert b2.inputs.compensation.fully_loaded_salary == pytest.approx(123_000)
    assert evaluate(b2).cost("rep_fixed") == pytest.approx(100 * (123_000 + 47_500))


def test_discrepancy_between_assumed_and_derived_deal_size() -> None:
    d = B.discrepancies()
    assert len(d) == 1
    assert d[0].path == "avg_revenue_per_transaction"
    assert d[0].gap_pct == pytest.approx(75_000 / (25_000_000 / 755) - 1)
    assert B.overrides_actuals() == ["avg_revenue_per_transaction"]
    reconciled = B.with_value("avg_revenue_per_transaction", 25_000_000 / 755, Source.DERIVED)
    assert reconciled.discrepancies() == []


def test_inputs_by_source_covers_every_path() -> None:
    groups = B.inputs_by_source()
    assert sum(len(v) for v in groups.values()) == 4 + 3 + 7 + 4 + 5 + 8 + 3
    assert groups[Source.ACTUAL] == []


# ------------------------------------------------------------------ constraints


def test_demand_bound_caps_throughput_and_makes_hiring_worthless() -> None:
    bd = B.with_policy(qualified_demand_per_year=5_000)
    base = evaluate(bd)
    assert base.operating.demand_bound
    assert base.operating.utilisation == pytest.approx(5_000 / 6_000)
    assert base.revenue == pytest.approx(5_000 * 0.25 * 75_000)
    hire = run(bd, HIRE, Horizon.STEADY_STATE)
    assert hire.revenue_delta == 0
    assert hire.delta == pytest.approx(-10 * FIXED_PER_REP)
    # Raising demand is the lever that pays here.
    assert run(bd, Scenario.of("demand", LeverSet(demand_change=0.1))).revenue_delta > 0


def test_capacity_lever_behaves_like_territories_at_steady_state_but_without_heads() -> None:
    cap = run(B, Scenario.of("cap", LeverSet(capacity_change=0.1)), Horizon.STEADY_STATE)
    hire = run(B, HIRE, Horizon.STEADY_STATE)
    assert cap.revenue_delta == pytest.approx(hire.revenue_delta)
    assert cap.delta - hire.delta == pytest.approx(10 * FIXED_PER_REP)


def test_close_rate_is_capped() -> None:
    assert resolve(B, LeverSet(close_rate_change=10)).close_rate == 1.0


# ------------------------------------------------------------------ interaction


def test_three_lever_interaction_matches_multiplicative_identity() -> None:
    rev, oi = interaction_effect(B, [CLOSE, CYCLE, DEAL])
    assert rev == pytest.approx(
        112_500_000 * (1.1 * 1.1 / 0.9 - 1) - 112_500_000 * (0.1 + 0.1 + 1 / 0.9 - 1)
    )
    assert rev == pytest.approx(3_750_000)
    assert oi > 0


def test_lever_composition_is_multiplicative() -> None:
    a = LeverSet(close_rate_change=0.1, cycle_time_reduction=0.1)
    c = a.compose(a)
    assert c.close_rate_change == pytest.approx(0.21)
    assert c.cycle_time_reduction == pytest.approx(0.19)


def test_months_to_benefit_scales_year_one_only() -> None:
    i = Intervention(name="x", levers=LeverSet(close_rate_change=0.2), months_to_benefit=6)
    assert i.effective_levers(Horizon.YEAR_ONE).close_rate_change == pytest.approx(0.1)
    assert i.effective_levers(Horizon.STEADY_STATE).close_rate_change == pytest.approx(0.2)


# ------------------------------------------------------------------ comparison modes


def test_equal_percentage_cycle_is_hyperbolic() -> None:
    r = equal_percentage(B, 0.10, levers=[Lever.CLOSE_RATE, Lever.CYCLE_TIME, Lever.DEAL_SIZE])
    assert r[Lever.CLOSE_RATE].revenue_delta == pytest.approx(r[Lever.DEAL_SIZE].revenue_delta)
    assert r[Lever.CYCLE_TIME].revenue_delta / r[Lever.CLOSE_RATE].revenue_delta == pytest.approx(
        (1 / 0.9 - 1) / 0.1
    )


def test_break_even_investment_identity() -> None:
    """At steady state: budget = ΔT × (loaded salary + travel). Year one adds the ramp penalty."""
    ss = break_even_investment(B, CLOSE, HIRE, Horizon.STEADY_STATE)
    assert ss.budget == pytest.approx(10 * FIXED_PER_REP)
    y1 = break_even_investment(B, CLOSE, HIRE, Horizon.YEAR_ONE)
    assert y1.budget == pytest.approx(5_983_875 + 10 * FIXED_PER_REP)
    assert y1.budget > ss.budget


def test_break_even_accounts_for_cost_already_in_preferred() -> None:
    costly = Scenario.of("close", LeverSet(close_rate_change=0.1), annual_cost=1_000_000)
    free = break_even_investment(B, CLOSE, HIRE, Horizon.STEADY_STATE).budget
    paid = break_even_investment(B, costly, HIRE, Horizon.STEADY_STATE).budget
    assert paid == pytest.approx(free)  # headroom is measured before programme cost


def test_equal_investment_charges_budget_and_respects_ceiling() -> None:
    costs = {
        Lever.CLOSE_RATE: CostToImprove(annual_cost_per_point=100_000, max_change=0.05),
        Lever.CAPACITY: CostToImprove(annual_cost_per_point=100_000),
    }
    r = equal_investment(B, 1_000_000, costs, Horizon.STEADY_STATE)
    assert r[Lever.CLOSE_RATE].scenario.programme_cost == 1_000_000
    assert r[Lever.CLOSE_RATE].scenario.operating.close_rate == pytest.approx(0.25 * 1.05)  # capped
    assert r[Lever.CAPACITY].scenario.operating.concurrent_opportunities == pytest.approx(
        33
    )  # 10 pts


def test_goal_seek() -> None:
    x = goal_seek(B, Lever.CLOSE_RATE, 5_000_000)
    assert x is not None
    assert run(B, Scenario.of("s", LeverSet.single(Lever.CLOSE_RATE, x))).delta == pytest.approx(
        5_000_000, rel=1e-4
    )
    assert (
        goal_seek(B, Lever.TERRITORIES, 5_000_000, Horizon.YEAR_ONE) is None
    )  # hiring can't get there in y1
    assert goal_seek(B, Lever.CLOSE_RATE, 0.0) == 0.0


def test_risk_adjusted_delta() -> None:
    s = Scenario(
        name="r",
        interventions=(
            Intervention(
                name="x",
                levers=LeverSet(close_rate_change=0.1),
                annual_cost=500_000,
                success_probability=0.6,
            ),
        ),
    )
    success = run(B, s).delta
    assert risk_adjusted_delta(B, s) == pytest.approx(0.6 * success + 0.4 * -500_000)


def test_sensitivity_is_monotone_for_close_rate() -> None:
    grid = [x for x, _ in sensitivity(B, Lever.CLOSE_RATE, [0, 0.05, 0.1, 0.2])]
    deltas = [b.delta for _, b in sensitivity(B, Lever.CLOSE_RATE, grid)]
    assert deltas == sorted(deltas)
    assert math.isclose(deltas[0], 0.0)
