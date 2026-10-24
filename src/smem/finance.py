"""Financial engine and true-up (spec §4).

Every scenario produces an income statement built from typed cost lines, and a
**bridge** from the baseline's operating income to the scenario's with no
unexplained residual. Two integrity rules are enforced as functions, not hoped for:

* accounting integrity — ``revenue − expenses − operating_income == 0``
* bridge integrity — ``Σ bridge steps == scenario OI − baseline OI``

and one causal rule the original violated: commission is charged on *realised*
revenue, so a hire that sells nothing earns no commission (an explicit draw may
be configured instead).
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from smem.assumptions import Baseline, Horizon
from smem.operating import OperatingState, managers_required, resolve
from smem.scenario import Scenario


class CostKind(StrEnum):
    """Cost behaviour categories."""

    VARIABLE = "variable"  # moves with revenue
    FIXED_PER_SELLER = "fixed_per_seller"  # moves with employed heads
    STEP_FIXED = "step_fixed"  # jumps at thresholds (managers per span)
    FIXED = "fixed"  # constant across scenarios
    DISCRETIONARY = "discretionary"  # chosen as part of the scenario


@dataclass(frozen=True, slots=True)
class CostLine:
    """One expense line with its behaviour and driver."""

    key: str
    label: str
    kind: CostKind
    amount: float
    driver: str


@dataclass(frozen=True, slots=True)
class Outcome:
    """Income statement for one scenario at one horizon."""

    scenario: Scenario
    horizon: Horizon
    operating: OperatingState
    revenue: float
    costs: tuple[CostLine, ...]

    def __iter__(self) -> Iterator[CostLine]:
        """Iterate over cost lines."""
        return iter(self.costs)

    def cost(self, key: str) -> float:
        """Amount of the cost line ``key`` (0 if absent)."""
        return next((c.amount for c in self.costs if c.key == key), 0.0)

    def costs_of_kind(self, kind: CostKind) -> float:
        """Total of all lines with behaviour ``kind``."""
        return sum(c.amount for c in self.costs if c.kind is kind)

    @property
    def total_expenses(self) -> float:
        """Σ cost lines."""
        return sum(c.amount for c in self.costs)

    @property
    def operating_income(self) -> float:
        """Revenue − total expenses."""
        return self.revenue - self.total_expenses

    @property
    def operating_margin(self) -> float:
        """OI ÷ revenue."""
        return self.operating_income / self.revenue if self.revenue else 0.0

    @property
    def sales_and_marketing(self) -> float:
        """Rep costs + draw + managers + overhead + marketing + programmes."""
        keys = (
            "commission",
            "draw",
            "rep_fixed",
            "managers",
            "sales_overhead",
            "marketing",
            "programmes",
        )
        return sum(self.cost(k) for k in keys)

    @property
    def programme_cost(self) -> float:
        """Discretionary intervention spend in this horizon."""
        return self.cost("programmes")

    def check(self) -> None:
        """Accounting integrity: raise if revenue − expenses − OI ≠ 0."""
        residual = self.revenue - self.total_expenses - self.operating_income
        if not math.isclose(residual, 0.0, abs_tol=1e-6):  # pragma: no cover - arithmetic identity
            msg = f"accounting residual {residual!r}"
            raise AssertionError(msg)


def evaluate(
    baseline: Baseline, scenario: Scenario | None = None, horizon: Horizon | None = None
) -> Outcome:
    """Evaluate ``scenario`` on ``baseline`` and return its income statement."""
    scenario = scenario or Scenario.baseline()
    horizon = horizon or baseline.policy.horizon
    i, pol = baseline.inputs, baseline.policy

    base_state = resolve(baseline, scenario.baseline().effective_levers(horizon), horizon)
    op = resolve(baseline, scenario.effective_levers(horizon), horizon)
    revenue = op.revenue

    comp, travel, r = i.compensation, i.travel, i.ratios
    base_managers = managers_required(base_state.employed_sellers, pol.manager_span)
    managers = managers_required(op.employed_sellers, pol.manager_span)

    costs = (
        CostLine(
            "cogs", "Cost of revenue", CostKind.VARIABLE, revenue * r.cost_of_revenue, "revenue"
        ),
        CostLine(
            "rd",
            "Research and development",
            CostKind.VARIABLE,
            revenue * r.research_and_development,
            "revenue",
        ),
        CostLine(
            "ga",
            "General and administrative",
            CostKind.VARIABLE,
            revenue * r.general_and_administrative,
            "revenue",
        ),
        CostLine(
            "commission",
            "Sales commission",
            CostKind.VARIABLE,
            revenue * comp.commission_rate,
            "revenue",
        ),
        CostLine(
            "draw",
            "Draw for ramping hires",
            CostKind.FIXED_PER_SELLER,
            op.unproductive_seller_years * pol.ramping_hire_draw,
            "unproductive seller-years",
        ),
        CostLine(
            "rep_fixed",
            "Seller salary and travel",
            CostKind.FIXED_PER_SELLER,
            op.employed_sellers * (comp.fully_loaded_salary + travel.annual_cost),
            "employed sellers",
        ),
        CostLine(
            "managers",
            "Incremental first-line managers",
            CostKind.STEP_FIXED,
            (managers - base_managers) * pol.manager_loaded_cost,
            f"ceil(sellers / {pol.manager_span})",
        ),
        CostLine("sales_overhead", "Sales overhead", CostKind.FIXED, i.overhead.total, "constant"),
        CostLine("marketing", "Marketing", CostKind.FIXED, i.marketing.total, "constant"),
        CostLine(
            "programmes",
            "Improvement programmes",
            CostKind.DISCRETIONARY,
            scenario.programme_cost(horizon),
            "scenario",
        ),
    )
    out = Outcome(scenario=scenario, horizon=horizon, operating=op, revenue=revenue, costs=costs)
    out.check()
    return out


# ------------------------------------------------------------------------- bridge


@dataclass(frozen=True, slots=True)
class BridgeStep:
    """One bar of the operating-income waterfall."""

    key: str
    label: str
    amount: float  # signed effect on operating income


@dataclass(frozen=True, slots=True)
class Bridge:
    """Baseline OI → scenario OI, fully explained."""

    baseline: Outcome
    scenario: Outcome
    steps: tuple[BridgeStep, ...]

    @property
    def start(self) -> float:
        """Baseline operating income."""
        return self.baseline.operating_income

    @property
    def end(self) -> float:
        """Scenario operating income."""
        return self.scenario.operating_income

    @property
    def delta(self) -> float:
        """End − start."""
        return self.end - self.start

    @property
    def residual(self) -> float:
        """Δ − Σ steps. Must be 0."""
        return self.delta - sum(s.amount for s in self.steps)

    @property
    def revenue_delta(self) -> float:
        """Scenario revenue − baseline revenue."""
        return self.scenario.revenue - self.baseline.revenue

    def check(self) -> None:
        """Bridge integrity: raise if any residual remains."""
        if not math.isclose(self.residual, 0.0, abs_tol=1e-6):  # pragma: no cover - identity
            msg = f"bridge residual {self.residual!r}"
            raise AssertionError(msg)


def bridge(baseline_outcome: Outcome, scenario_outcome: Outcome) -> Bridge:
    """Build the waterfall between two outcomes of the same baseline."""
    steps = [BridgeStep("revenue", "Revenue", scenario_outcome.revenue - baseline_outcome.revenue)]
    for line in scenario_outcome.costs:
        delta = line.amount - baseline_outcome.cost(line.key)
        if delta:
            steps.append(BridgeStep(line.key, line.label, -delta))
    b = Bridge(baseline=baseline_outcome, scenario=scenario_outcome, steps=tuple(steps))
    b.check()
    return b


def run(baseline: Baseline, scenario: Scenario, horizon: Horizon | None = None) -> Bridge:
    """Evaluate baseline and scenario at the same horizon and bridge them."""
    horizon = horizon or baseline.policy.horizon
    return bridge(evaluate(baseline, None, horizon), evaluate(baseline, scenario, horizon))


__all__ = ["Bridge", "BridgeStep", "CostKind", "CostLine", "Outcome", "bridge", "evaluate", "run"]
