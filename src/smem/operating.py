"""Commercial operating engine (spec §3): capacity, demand, conversion, velocity.

Separates three ideas the original conflated:

* **territories** — coverage units (``T``);
* **employed sellers** — filled seats that incur cost;
* **productive seller-equivalents** — ``N``, what actually generates throughput
  once ramp is applied.

and bounds throughput by demand:

    realisable_opportunities = min(capacity, qualified_demand)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from smem.assumptions import Baseline, Horizon, RampPolicy
from smem.inputs import MONTHS_PER_YEAR, ModelInputs
from smem.scenario import LeverSet


def ramp_fraction(ramp_months: float, policy: RampPolicy, horizon: Horizon) -> float:
    """Share of a first year that a new hire is productive."""
    if horizon is Horizon.STEADY_STATE:
        return 1.0
    r = min(max(ramp_months, 0.0), MONTHS_PER_YEAR)
    if policy is RampPolicy.LINEAR:
        # Linear 0→1 over r months, then 1: average over 12 months = 1 − r/24.
        return 1.0 - r / (2.0 * MONTHS_PER_YEAR)
    return (MONTHS_PER_YEAR - r) / MONTHS_PER_YEAR


@dataclass(frozen=True, slots=True)
class OperatingState:
    """Resolved operating quantities for one scenario and horizon."""

    territories: float
    employed_sellers: float
    new_hires: float  # > 0 when the scenario adds seats (0 when it removes)
    productive_equivalents: float  # N
    unproductive_seller_years: float  # employed − productive (hires still ramping)

    concurrent_opportunities: float  # P
    cycle_months: float  # C
    close_rate: float  # w
    avg_deal_size: float  # A

    capacity_opportunities: float  # N · 12P/C
    qualified_demand: float | None
    realised_opportunities: float  # min(capacity, demand)

    @property
    def opportunities_per_seller_year(self) -> float:
        """Little's Law throughput of one fully ramped seller."""
        return MONTHS_PER_YEAR / self.cycle_months * self.concurrent_opportunities

    @property
    def deals(self) -> float:
        """Realised opportunities × close rate."""
        return self.realised_opportunities * self.close_rate

    @property
    def revenue(self) -> float:
        """Deals × average deal size (bookings = revenue in v2)."""
        return self.deals * self.avg_deal_size

    @property
    def utilisation(self) -> float:
        """Realised ÷ capacity. 1.0 when capacity-bound, < 1 when demand-bound."""
        return (
            self.realised_opportunities / self.capacity_opportunities
            if self.capacity_opportunities
            else 0.0
        )

    @property
    def demand_bound(self) -> bool:
        """True when demand, not selling capacity, limits throughput."""
        return (
            self.qualified_demand is not None
            and self.qualified_demand < self.capacity_opportunities
        )

    @property
    def revenue_per_productive_seller(self) -> float:
        """Revenue ÷ N."""
        return self.revenue / self.productive_equivalents if self.productive_equivalents else 0.0


def resolve(baseline: Baseline, levers: LeverSet, horizon: Horizon | None = None) -> OperatingState:
    """Apply ``levers`` to ``baseline`` and resolve the operating state."""
    i: ModelInputs = baseline.inputs
    pol = baseline.policy
    horizon = horizon or pol.horizon

    base_t = i.territories
    base_employed = pol.employed_sellers if pol.employed_sellers is not None else base_t
    territories = base_t * (1.0 + levers.territory_change)
    # Seats scale with territories; vacancies (if any) are preserved proportionally.
    employed = base_employed * (1.0 + levers.territory_change)
    delta = employed - base_employed
    new_hires = max(0.0, delta)
    frac = ramp_fraction(i.mechanics.ramp_months, pol.ramp_policy, horizon)
    productive = base_employed + new_hires * frac if delta > 0 else employed

    capacity_p = i.mechanics.concurrent_opportunities * (1.0 + levers.capacity_change)
    cycle = i.mechanics.cycle_months * (1.0 - levers.cycle_time_reduction)
    close = min(1.0, i.mechanics.close_rate * (1.0 + levers.close_rate_change))
    deal = i.avg_revenue_per_transaction * (1.0 + levers.deal_size_change)

    capacity_opps = productive * MONTHS_PER_YEAR / cycle * capacity_p
    demand = (
        pol.qualified_demand_per_year * (1.0 + levers.demand_change)
        if pol.qualified_demand_per_year is not None
        else None
    )
    realised = min(capacity_opps, demand) if demand is not None else capacity_opps

    return OperatingState(
        territories=territories,
        employed_sellers=employed,
        new_hires=new_hires,
        productive_equivalents=productive,
        unproductive_seller_years=max(0.0, employed - productive),
        concurrent_opportunities=capacity_p,
        cycle_months=cycle,
        close_rate=close,
        avg_deal_size=deal,
        capacity_opportunities=capacity_opps,
        qualified_demand=demand,
        realised_opportunities=realised,
    )


def managers_required(employed_sellers: float, span: float | None) -> float:
    """Step-fixed headcount: ``ceil(sellers / span)``; 0 when no span is set."""
    return math.ceil(employed_sellers / span - 1e-9) if span else 0.0


__all__ = ["OperatingState", "managers_required", "ramp_fraction", "resolve"]
