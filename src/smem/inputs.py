"""Validated input schema for the Sales & Marketing Effectiveness Model.

Every quantity the original workbook asked for on sheet ``1) Data entry`` is
represented here, grouped the way the sheet grouped them. Defaults are the
"fictitious company" values that shipped with the workbook, so
``ModelInputs()`` with no arguments reproduces the original baseline.

All rates are fractions (``0.23`` not ``23``). All money is in the same
currency unit; the engine never converts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveFloat

MONTHS_PER_YEAR = 12.0


class _Frozen(BaseModel):
    """Immutable, strictly-validated base for every input block."""

    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=True)


class RepCompensation(_Frozen):
    """Cost of one quota-carrying rep, excluding travel.

    Workbook cells: E16 (salary), E17 (load rate), F28 (commission).
    """

    base_salary: NonNegativeFloat = Field(95_000, description="Average salary per sales rep")
    load_rate: NonNegativeFloat = Field(
        0.23, le=2.0, description="Corporate benefits/overhead load rate applied to salary"
    )
    commission_rate: NonNegativeFloat = Field(
        0.08, le=1.0, description="Average commission as a fraction of revenue booked"
    )

    @property
    def fully_loaded_salary(self) -> float:
        """Workbook F15: ``=E16+(E16*E17)``."""
        return self.base_salary * (1.0 + self.load_rate)


class TravelProfile(_Frozen):
    """Cost structure of a single sales trip and the number of trips per year.

    Workbook cells E20..E26. The original model treats travel as a fixed
    annual cost per rep — it does **not** scale with opportunities or deals.
    """

    transport_round_trip: NonNegativeFloat = Field(750, description="Air fare, train, mileage")
    ground: NonNegativeFloat = Field(200, description="Cabs, tolls, car rental")
    meals_per_day: NonNegativeFloat = Field(100)
    lodging_per_night: NonNegativeFloat = Field(250)
    days_per_trip: NonNegativeFloat = Field(2)
    entertainment_per_trip: NonNegativeFloat = Field(250, description="Client dinners etc.")
    trips_per_year: NonNegativeFloat = Field(25)

    @property
    def cost_per_trip(self) -> float:
        """Fixed per-trip items plus per-day items times days away."""
        fixed = self.transport_round_trip + self.ground + self.entertainment_per_trip
        per_day = self.meals_per_day + self.lodging_per_night
        return fixed + per_day * self.days_per_trip

    @property
    def annual_cost(self) -> float:
        """Workbook F19."""
        return self.cost_per_trip * self.trips_per_year


class SalesMechanics(_Frozen):
    """The throughput parameters of a single rep's pipeline.

    Workbook cells F31 (capacity), F33 (cycle), F35 (ramp), F37 (close rate).

    Together these form a Little's-Law system: a rep holds ``concurrent_opportunities``
    units of work-in-process, each unit resides for ``cycle_months``, so annual
    throughput of opportunities is ``12 / cycle_months * concurrent_opportunities``.
    """

    concurrent_opportunities: PositiveFloat = Field(
        30, description="Pipeline opportunities one rep can manage at the same time"
    )
    cycle_months: PositiveFloat = Field(
        6.0, description="Months from qualified opportunity to signed agreement"
    )
    ramp_months: NonNegativeFloat = Field(
        12.0, description="Months for a new hire to reach full productivity"
    )
    close_rate: NonNegativeFloat = Field(
        0.25, le=1.0, description="Fraction of worked opportunities that close"
    )


class SalesOverhead(_Frozen):
    """Non-variable costs of running the sales organisation (workbook E42..E46)."""

    non_quota_manager_salaries: NonNegativeFloat = Field(2_750_000)
    sales_engineers_and_support: NonNegativeFloat = Field(6_000_000)
    sales_admin_and_operations: NonNegativeFloat = Field(800_000)
    training: NonNegativeFloat = Field(500_000)
    incentives_non_quota: NonNegativeFloat = Field(750_000)

    @property
    def total(self) -> float:
        """Workbook F41."""
        return (
            self.non_quota_manager_salaries
            + self.sales_engineers_and_support
            + self.sales_admin_and_operations
            + self.training
            + self.incentives_non_quota
        )


class MarketingSpend(_Frozen):
    """All marketing investment lines (workbook E49..E56)."""

    personnel: NonNegativeFloat = Field(1_000_000)
    website: NonNegativeFloat = Field(250_000)
    events: NonNegativeFloat = Field(500_000)
    advertising: NonNegativeFloat = Field(500_000)
    direct_mail: NonNegativeFloat = Field(250_000)
    telemarketing_lead_gen: NonNegativeFloat = Field(250_000)
    branding_and_pr: NonNegativeFloat = Field(200_000)
    collateral: NonNegativeFloat = Field(750_000)

    @property
    def total(self) -> float:
        """Workbook F48."""
        return (
            self.personnel
            + self.website
            + self.events
            + self.advertising
            + self.direct_mail
            + self.telemarketing_lead_gen
            + self.branding_and_pr
            + self.collateral
        )


class IncomeStatementRatios(_Frozen):
    """Industry-average cost lines expressed as a fraction of revenue.

    Workbook ``3) Impact Analysis`` C30..C32. Treated as fully variable with revenue.
    """

    cost_of_revenue: NonNegativeFloat = Field(0.1322, le=1.0)
    research_and_development: NonNegativeFloat = Field(0.1019, le=1.0)
    general_and_administrative: NonNegativeFloat = Field(0.154, le=1.0)

    @property
    def total(self) -> float:
        """Sum of the three variable ratios."""
        return (
            self.cost_of_revenue + self.research_and_development + self.general_and_administrative
        )


class ModelInputs(_Frozen):
    """Everything sheet ``1) Data entry`` collects, with the shipped defaults.

    ``contracts_last_year`` and ``revenue_from_contracts`` were captured by the
    original workbook but never wired into any formula; ``avg_revenue_per_transaction``
    was a hard-coded 75,000 instead. Both are kept so the implied figure can be
    surfaced to the user (see :pyattr:`implied_avg_revenue_per_transaction`).
    """

    territories: PositiveFloat = Field(100, description="Open sales territories last year")
    avg_revenue_per_transaction: PositiveFloat = Field(
        75_000, description="Average deal size used by the model"
    )
    contracts_last_year: PositiveFloat | None = Field(755, description="Informational")
    revenue_from_contracts: NonNegativeFloat | None = Field(25_000_000, description="Informational")

    compensation: RepCompensation = Field(default_factory=RepCompensation)
    travel: TravelProfile = Field(default_factory=TravelProfile)
    mechanics: SalesMechanics = Field(default_factory=SalesMechanics)
    overhead: SalesOverhead = Field(default_factory=SalesOverhead)
    marketing: MarketingSpend = Field(default_factory=MarketingSpend)
    ratios: IncomeStatementRatios = Field(default_factory=IncomeStatementRatios)

    @property
    def implied_avg_revenue_per_transaction(self) -> float | None:
        """Revenue ÷ contracts, if both were supplied. Not used by the engine."""
        if self.contracts_last_year and self.revenue_from_contracts is not None:
            return self.revenue_from_contracts / self.contracts_last_year
        return None

    @property
    def total_sales_and_marketing_overhead(self) -> float:
        """Workbook F39: ``=F41+F48``."""
        return self.overhead.total + self.marketing.total
