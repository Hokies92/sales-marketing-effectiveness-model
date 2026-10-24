"""Pure computational core of the Sales & Marketing Effectiveness Model.

The model is a **throughput system**. For one rep:

    opportunities_per_year = (12 / cycle_months) * concurrent_opportunities   (Little's Law)
    deals_per_year         = opportunities_per_year * close_rate
    revenue_per_rep        = deals_per_year * avg_revenue_per_transaction

and for the company:

    revenue = territories * revenue_per_rep

so the whole revenue engine collapses to one identity with four levers:

    R = T · (12·P / C) · w · A

        T  territories          (lever: hire / cut)
        P  concurrent capacity  (implicit lever — the original workbook never varied it)
        C  cycle months         (lever: shorten)
        w  close rate           (lever: raise)
        A  avg revenue / deal   (lever: raise)

Every function here is deterministic and side-effect free. Nothing imports
openpyxl, FastAPI or anything else: this module is the single source of truth
that the workbook builder, the API and the tests all consume.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from smem.inputs import MONTHS_PER_YEAR, ModelInputs

# --------------------------------------------------------------------------- levers


class Levers(BaseModel):
    """Proportional changes applied to the four scenario drivers.

    All values are fractions. ``Levers()`` is the baseline (no change).
    ``cycle_time_reduction=0.10`` means the cycle becomes 90% as long.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    territory_change: float = Field(0.0, ge=-1.0, description="+0.10 → 10% more territories")
    close_rate_change: float = Field(0.0, ge=-1.0, description="+0.10 → close rate × 1.10")
    cycle_time_reduction: float = Field(
        0.0, ge=-10.0, lt=1.0, description="+0.10 → cycle months × 0.90"
    )
    deal_size_change: float = Field(0.0, ge=-1.0, description="+0.10 → deal size × 1.10")

    @property
    def is_baseline(self) -> bool:
        """True when no lever is pulled."""
        return not any(
            (
                self.territory_change,
                self.close_rate_change,
                self.cycle_time_reduction,
                self.deal_size_change,
            )
        )


def apply_levers(base: ModelInputs, levers: Levers) -> ModelInputs:
    """Return a new :class:`ModelInputs` with the levers applied to ``base``."""
    if levers.is_baseline:
        return base
    mech = base.mechanics
    new_close = min(1.0, mech.close_rate * (1.0 + levers.close_rate_change))
    return base.model_copy(
        update={
            "territories": base.territories * (1.0 + levers.territory_change),
            "avg_revenue_per_transaction": base.avg_revenue_per_transaction
            * (1.0 + levers.deal_size_change),
            "mechanics": mech.model_copy(
                update={
                    "cycle_months": mech.cycle_months * (1.0 - levers.cycle_time_reduction),
                    "close_rate": new_close,
                }
            ),
        }
    )


# --------------------------------------------------------------------------- per-rep


@dataclass(frozen=True, slots=True)
class RepEconomics:
    """Unit economics of one fully-ramped rep for one year (workbook rows 11-14, 21-23)."""

    opportunities_per_year: float
    deals_per_year: float
    revenue: float
    loaded_salary: float
    travel: float
    commission: float

    @property
    def total_cost(self) -> float:
        """Workbook row 14: salary + travel + commission."""
        return self.loaded_salary + self.travel + self.commission

    @property
    def fixed_cost(self) -> float:
        """Cost incurred whether or not the rep sells anything."""
        return self.loaded_salary + self.travel

    @property
    def contribution(self) -> float:
        """Revenue minus the rep's own fully-loaded cost."""
        return self.revenue - self.total_cost


def rep_economics(inputs: ModelInputs) -> RepEconomics:
    """Compute one rep's annual throughput, revenue and cost from ``inputs``."""
    m = inputs.mechanics
    opps = (MONTHS_PER_YEAR / m.cycle_months) * m.concurrent_opportunities
    deals = opps * m.close_rate
    revenue = deals * inputs.avg_revenue_per_transaction
    return RepEconomics(
        opportunities_per_year=opps,
        deals_per_year=deals,
        revenue=revenue,
        loaded_salary=inputs.compensation.fully_loaded_salary,
        travel=inputs.travel.annual_cost,
        commission=revenue * inputs.compensation.commission_rate,
    )


def ramp_productivity(ramp_months: float) -> float:
    """Fraction of a new hire's first year that is productive (workbook step rule).

    The original model treats a new rep as contributing nothing for ``ramp_months``
    and full productivity afterwards: ``(12 - ramp) / 12``, floored at zero.
    """
    return max(0.0, (MONTHS_PER_YEAR - ramp_months) / MONTHS_PER_YEAR)


# --------------------------------------------------------------------------- company


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Company-level outcome of one scenario (workbook sheets 2 and 3, one column)."""

    inputs: ModelInputs
    levers: Levers
    rep: RepEconomics

    revenue: float
    rep_costs: float
    sales_overhead: float
    marketing: float
    cost_of_revenue: float
    research_and_development: float
    general_and_administrative: float

    @property
    def total_sales_costs(self) -> float:
        """Sheet 3 row 13: rep costs + sales overhead."""
        return self.rep_costs + self.sales_overhead

    @property
    def sales_and_marketing(self) -> float:
        """Sheet 3 rows 15/20."""
        return self.total_sales_costs + self.marketing

    @property
    def total_operating_expenses(self) -> float:
        """Sheet 3 row 22."""
        return (
            self.cost_of_revenue
            + self.research_and_development
            + self.sales_and_marketing
            + self.general_and_administrative
        )

    @property
    def operating_income(self) -> float:
        """Sheet 3 row 23."""
        return self.revenue - self.total_operating_expenses

    @property
    def operating_margin(self) -> float:
        """Operating income ÷ revenue (0 when revenue is 0)."""
        return self.operating_income / self.revenue if self.revenue else 0.0

    @property
    def sales_and_marketing_roi(self) -> float:
        """Sheet 3 row 27: ``(revenue − S&M) / S&M``.

        Note this is a revenue-over-spend ratio, not a profit ROI; the name is
        preserved from the original workbook.
        """
        sm = self.sales_and_marketing
        return (self.revenue - sm) / sm if sm else 0.0


def evaluate(
    base: ModelInputs,
    levers: Levers | None = None,
) -> ScenarioResult:
    """Evaluate the company under ``base`` inputs with ``levers`` applied.

    Revenue treatment of a change in territories follows the workbook's intent,
    applied consistently (the original applied it inconsistently — see
    ``docs/model_teardown.md``):

    * **Added** territories earn ``ramp_productivity`` of a full rep-year in year one.
    * **Removed** territories simply disappear.
    * Rep **costs** are incurred in full for every territory, ramped or not.
    """
    levers = levers or Levers()
    scenario = apply_levers(base, levers)
    rep = rep_economics(scenario)

    delta_t = scenario.territories - base.territories
    if delta_t > 0:
        productive = base.territories + delta_t * ramp_productivity(scenario.mechanics.ramp_months)
    else:
        productive = scenario.territories
    revenue = rep.revenue * productive

    r = scenario.ratios
    return ScenarioResult(
        inputs=scenario,
        levers=levers,
        rep=rep,
        revenue=revenue,
        rep_costs=rep.total_cost * scenario.territories,
        sales_overhead=scenario.overhead.total,
        marketing=scenario.marketing.total,
        cost_of_revenue=revenue * r.cost_of_revenue,
        research_and_development=revenue * r.research_and_development,
        general_and_administrative=revenue * r.general_and_administrative,
    )


# --------------------------------------------------------------------------- comparison


@dataclass(frozen=True, slots=True)
class Impact:
    """Difference between a scenario and its baseline (sheet 3 rows 9, 12, 26)."""

    baseline: ScenarioResult
    scenario: ScenarioResult

    @property
    def revenue_delta(self) -> float:
        """Sheet 3 row 9."""
        return self.scenario.revenue - self.baseline.revenue

    @property
    def rep_cost_delta(self) -> float:
        """Sheet 3 row 12."""
        return self.scenario.rep_costs - self.baseline.rep_costs

    @property
    def operating_income_delta(self) -> float:
        """Change in operating income."""
        return self.scenario.operating_income - self.baseline.operating_income

    @property
    def net_gain_pct(self) -> float:
        """Sheet 3 row 26: ``(Δrevenue − Δrep_costs) / base revenue``."""
        return (
            (self.revenue_delta - self.rep_cost_delta) / self.baseline.revenue
            if self.baseline.revenue
            else 0.0
        )

    @property
    def revenue_growth_pct(self) -> float:
        """Δrevenue ÷ base revenue."""
        return self.revenue_delta / self.baseline.revenue if self.baseline.revenue else 0.0

    @property
    def operating_income_growth_pct(self) -> float:
        """Δoperating income ÷ base operating income."""
        oi = self.baseline.operating_income
        return self.operating_income_delta / oi if oi else 0.0


def impact(base: ModelInputs, levers: Levers) -> Impact:
    """Evaluate baseline and scenario and return their :class:`Impact`."""
    return Impact(baseline=evaluate(base), scenario=evaluate(base, levers))
