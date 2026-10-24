"""Scenario comparison and decision support (spec §6).

Comparison modes, in the order a user meets them:

1. **Equal percentage** — move each lever by the same %, see sensitivities.
2. **Break-even investment** — how much may one strategy cost before another is better.
3. **Equal investment** — what each lever yields for the same budget, given a cost-to-improve.
4. **Goal seek** — how far must a lever move to deliver a target change in operating income.
5. **Risk-adjusted** — expected value when an intervention may fail.

All functions are deterministic and return bridges, so every number is explained.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat

from smem.assumptions import Baseline, Horizon
from smem.finance import Bridge, run
from smem.scenario import Intervention, Lever, LeverSet, Scenario, combine

LEVER_LABELS: Mapping[Lever, str] = {
    Lever.TERRITORIES: "Add sellers",
    Lever.CAPACITY: "Raise opportunity capacity per seller",
    Lever.CLOSE_RATE: "Raise close rate",
    Lever.CYCLE_TIME: "Shorten sales cycle",
    Lever.DEAL_SIZE: "Raise average deal size",
    Lever.DEMAND: "Raise qualified demand",
}


# ------------------------------------------------------------------ 1. equal percentage


def equal_percentage(
    baseline: Baseline,
    change: float = 0.10,
    levers: Iterable[Lever] = tuple(Lever),
    horizon: Horizon | None = None,
) -> dict[Lever, Bridge]:
    """One single-lever scenario per lever, each moved by ``change``."""
    return {
        lever: run(
            baseline, Scenario.of(LEVER_LABELS[lever], LeverSet.single(lever, change)), horizon
        )
        for lever in levers
    }


def interaction_effect(
    baseline: Baseline, scenarios: Iterable[Scenario], horizon: Horizon | None = None
) -> tuple[float, float]:
    """(Δrevenue, ΔOI) of the combination beyond the sum of the parts.

    Positive values are the multiplicative "compounding" the original workbook
    illustrates; negative values would signal a binding constraint (e.g. demand).
    """
    scenarios = tuple(scenarios)
    singles = [run(baseline, s, horizon) for s in scenarios]
    combined = run(baseline, combine("combined", scenarios), horizon)
    rev = combined.revenue_delta - sum(b.revenue_delta for b in singles)
    oi = combined.delta - sum(b.delta for b in singles)
    return rev, oi


# ------------------------------------------------------------------ 2. break-even investment


@dataclass(frozen=True, slots=True)
class BreakEven:
    """Maximum annual spend on ``preferred`` before ``alternative`` yields more OI."""

    preferred: Bridge
    alternative: Bridge
    budget: float

    @property
    def budget_pct_of_revenue(self) -> float:
        """Budget as a share of baseline revenue."""
        rev = self.preferred.baseline.revenue
        return self.budget / rev if rev else 0.0


def break_even_investment(
    baseline: Baseline,
    preferred: Scenario,
    alternative: Scenario,
    horizon: Horizon | None = None,
) -> BreakEven:
    """Return the extra annual cost ``preferred`` can bear and still beat ``alternative``.

    At steady state with revenue-proportional costs, this reduces to the alternative's
    fixed cost difference — e.g. for "improve close rate 10%" vs "hire 10% more sellers"
    it is exactly ``ΔT × (loaded salary + travel)``.
    """
    p, a = run(baseline, preferred, horizon), run(baseline, alternative, horizon)
    headroom = (p.end + p.scenario.programme_cost) - (a.end + a.scenario.programme_cost)
    return BreakEven(preferred=p, alternative=a, budget=headroom)


# ------------------------------------------------------------------ 3. equal investment


class CostToImprove(BaseModel):
    """What it costs to move one lever: a linear price per percentage point, with a ceiling.

    Difficulty is represented by observable components (spec §6.3), not a score:
    annual cost per point, the maximum achievable change, and months to benefit.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    annual_cost_per_point: PositiveFloat = Field(
        description="Currency per 1 pp of relative change per year"
    )
    max_change: float = Field(0.5, gt=0.0, description="Ceiling on achievable relative change")
    months_to_benefit: float = Field(0.0, ge=0.0, le=12.0)
    success_probability: float = Field(1.0, ge=0.0, le=1.0)

    def change_for(self, budget: float) -> float:
        """Relative change purchasable with ``budget`` per year."""
        return min(self.max_change, budget / self.annual_cost_per_point / 100.0)

    def intervention(self, lever: Lever, budget: float) -> Intervention:
        """Build the intervention this budget buys on ``lever``."""
        return Intervention(
            name=f"{LEVER_LABELS[lever]} (budget {budget:,.0f})",
            levers=LeverSet.single(lever, self.change_for(budget)),
            annual_cost=budget,
            months_to_benefit=self.months_to_benefit,
            success_probability=self.success_probability,
        )


def equal_investment(
    baseline: Baseline,
    budget: float,
    costs: Mapping[Lever, CostToImprove],
    horizon: Horizon | None = None,
) -> dict[Lever, Bridge]:
    """Spend the same ``budget`` on each lever and compare the resulting bridges."""
    return {
        lever: run(
            baseline,
            Scenario(name=LEVER_LABELS[lever], interventions=(c.intervention(lever, budget),)),
            horizon,
        )
        for lever, c in costs.items()
    }


# ------------------------------------------------------------------ 4. goal seek


def goal_seek(
    baseline: Baseline,
    lever: Lever,
    target_oi_delta: float,
    horizon: Horizon | None = None,
    upper: float | None = None,
    tol: float = 1e-6,
) -> float | None:
    """Find the smallest change on ``lever`` delivering ``target_oi_delta`` (None if unattainable).

    Bisection on a monotone response. Returns None when even ``upper`` falls short
    (or when the lever does not increase OI at this horizon, e.g. hiring in year one
    under a 12-month ramp).
    """
    hi = upper if upper is not None else (0.95 if lever is Lever.CYCLE_TIME else 5.0)

    def oi_delta(x: float) -> float:
        return run(baseline, Scenario.of("seek", LeverSet.single(lever, x)), horizon).delta

    if oi_delta(hi) < target_oi_delta:
        return None
    if target_oi_delta <= 0.0:
        return 0.0
    lo = 0.0
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if oi_delta(mid) >= target_oi_delta:
            hi = mid
        else:
            lo = mid
    return hi


# ------------------------------------------------------------------ 5. risk adjusted


def risk_adjusted_delta(
    baseline: Baseline, scenario: Scenario, horizon: Horizon | None = None
) -> float:
    """``p × ΔOI(success) + (1 − p) × ΔOI(failure)`` where failure still incurs programme cost."""
    p = scenario.joint_success_probability()
    success = run(baseline, scenario, horizon).delta
    failed = Scenario(
        name=f"{scenario.name} (failed)",
        interventions=tuple(
            i.model_copy(update={"levers": LeverSet()}) for i in scenario.interventions
        ),
    )
    failure = run(baseline, failed, horizon).delta
    return p * success + (1.0 - p) * failure


# ------------------------------------------------------------------ sensitivity


def sensitivity(
    baseline: Baseline,
    lever: Lever,
    changes: Iterable[float],
    horizon: Horizon | None = None,
) -> list[tuple[float, Bridge]]:
    """OI bridge for each change in ``changes`` on one lever."""
    return [
        (x, run(baseline, Scenario.of("sens", LeverSet.single(lever, x)), horizon)) for x in changes
    ]


__all__ = [
    "LEVER_LABELS",
    "BreakEven",
    "CostToImprove",
    "break_even_investment",
    "equal_investment",
    "equal_percentage",
    "goal_seek",
    "interaction_effect",
    "risk_adjusted_delta",
    "sensitivity",
]
