"""Faithful reproduction of the original 2011 workbook, *including its defects*.

This module exists for one reason: regression. If :func:`legacy_workbook_values`
reproduces every computed cell of the shipped ``.xls`` to the cent, we have
proven that we understand the model well enough to rebuild it. The corrected
engine lives in :mod:`smem.engine`; nothing in production should call this.

Defects reproduced (see ``docs/model_teardown.md`` for the full list):

``Q1``
    Sheet 2 row 11 ("Average fully loaded salary") is a hard-coded ``87,750``
    in every column instead of linking to Data-entry ``F15`` (``116,850``).
    ``87,750 = 75,000 × 1.17`` — a stale value from an earlier edition.
``Q2``
    Sheet 2 ``K25`` (combined revenue) subtracts the *productive* share of the
    new hires' revenue, at *baseline* revenue-per-rep, instead of the
    unproductive share at scenario revenue-per-rep. With ramp = 12 months the
    subtraction is zero, so the "Improve all" column silently credits every
    new hire with a full year of improved revenue while the "Hire" column
    credits them with none.
"""

from __future__ import annotations

from smem.engine import apply_levers, ramp_productivity, rep_economics
from smem.inputs import ModelInputs
from smem.scenarios import ImprovementRates, Scenario

LEGACY_LOADED_SALARY = 87_750.0
"""Hard-coded value found in '2) Performance breakdown'!C11, F11, G11, H11, J11."""

_COLUMNS: dict[Scenario, str] = {
    Scenario.HIRE: "E",
    Scenario.CLOSE: "F",
    Scenario.CYCLE: "G",
    Scenario.DEAL: "H",
    Scenario.PRODUCTIVITY: "J",
    Scenario.ALL: "K",
}

S2 = "'2) Performance breakdown'"
S3 = "'3) Impact Analysis'"


def legacy_workbook_values(
    inputs: ModelInputs | None = None,
    rates: ImprovementRates | None = None,
) -> dict[str, float]:
    """Return ``{"'<sheet>'!<cell>": value}`` for every numeric formula cell on sheets 2 and 3.

    Only the cells that carry model logic are returned (labels and cross-sheet
    echoes of inputs are omitted).
    """
    inputs = inputs or ModelInputs()
    rates = rates or ImprovementRates()
    out: dict[str, float] = {}

    base_rep = rep_economics(inputs)
    overhead = inputs.overhead.total
    marketing = inputs.marketing.total
    ratios = inputs.ratios

    def column(col: str, scenario_inputs: ModelInputs, revenue: float) -> None:
        """Write one scenario column of sheets 2 and 3."""
        rep = rep_economics(scenario_inputs)
        territories = scenario_inputs.territories
        # Q1 — hard-coded loaded salary replaces the linked value.
        cost_per_rep = LEGACY_LOADED_SALARY + rep.travel + rep.commission
        rep_costs = cost_per_rep * territories

        out[f"{S2}!{col}9"] = territories
        out[f"{S2}!{col}10"] = scenario_inputs.avg_revenue_per_transaction
        out[f"{S2}!{col}11"] = LEGACY_LOADED_SALARY
        out[f"{S2}!{col}12"] = rep.travel
        out[f"{S2}!{col}13"] = rep.commission
        out[f"{S2}!{col}14"] = cost_per_rep
        out[f"{S2}!{col}16"] = scenario_inputs.mechanics.concurrent_opportunities
        out[f"{S2}!{col}17"] = scenario_inputs.mechanics.cycle_months
        out[f"{S2}!{col}18"] = scenario_inputs.mechanics.ramp_months
        out[f"{S2}!{col}19"] = scenario_inputs.mechanics.close_rate
        out[f"{S2}!{col}21"] = rep.opportunities_per_year
        out[f"{S2}!{col}22"] = rep.deals_per_year
        out[f"{S2}!{col}23"] = rep.revenue
        out[f"{S2}!{col}25"] = revenue
        out[f"{S2}!{col}26"] = rep_costs

        total_sales = rep_costs + overhead
        sm = total_sales + marketing
        cogs = revenue * ratios.cost_of_revenue
        rd = revenue * ratios.research_and_development
        ga = revenue * ratios.general_and_administrative
        opex = cogs + rd + sm + ga

        out[f"{S3}!{col}8"] = revenue
        out[f"{S3}!{col}13"] = total_sales
        out[f"{S3}!{col}14"] = marketing
        out[f"{S3}!{col}15"] = sm
        out[f"{S3}!{col}18"] = cogs
        out[f"{S3}!{col}19"] = rd
        out[f"{S3}!{col}20"] = sm
        out[f"{S3}!{col}21"] = ga
        out[f"{S3}!{col}22"] = opex
        out[f"{S3}!{col}23"] = revenue - opex
        out[f"{S3}!{col}27"] = (revenue - sm) / sm

    # Baseline column C.
    base_revenue = base_rep.revenue * inputs.territories
    column("C", inputs, base_revenue)
    base_rep_costs = out[f"{S2}!C26"]

    for scenario, col in _COLUMNS.items():
        scen = apply_levers(inputs, rates.levers_for(scenario))
        rep = rep_economics(scen)
        delta_t = scen.territories - inputs.territories
        productive = ramp_productivity(scen.mechanics.ramp_months)

        if scenario is Scenario.HIRE:
            # E25: =((((12-E18)/12)*E23)*(E9-C9))+C25
            revenue = productive * rep.revenue * delta_t + base_revenue
        elif scenario is Scenario.ALL:
            # Q2 — K25: =(K23*K9)-((((12-E18)/12)*E23)*(E9-C9))
            revenue = rep.revenue * scen.territories - productive * base_rep.revenue * delta_t
        else:
            revenue = rep.revenue * scen.territories

        column(col, scen, revenue)
        out[f"{S3}!{col}9"] = revenue - base_revenue
        out[f"{S3}!{col}12"] = out[f"{S2}!{col}26"] - base_rep_costs
        out[f"{S3}!{col}26"] = (out[f"{S3}!{col}9"] - out[f"{S3}!{col}12"]) / base_revenue

    return out
