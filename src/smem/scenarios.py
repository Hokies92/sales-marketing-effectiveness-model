"""The six scenario columns of the original ``2) Performance breakdown`` sheet.

Four single-lever scenarios (10% each by default), plus two combinations:
the three "productivity" levers together, and all four together.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from smem.engine import Impact, Levers, impact
from smem.inputs import ModelInputs


class Scenario(StrEnum):
    """Column identifiers, in workbook order."""

    HIRE = "hire_more_reps"
    CLOSE = "increase_close_rate"
    CYCLE = "decrease_cycle_time"
    DEAL = "increase_deal_size"
    PRODUCTIVITY = "close_deal_and_cycle"
    ALL = "improve_all"


SCENARIO_LABELS: Mapping[Scenario, str] = {
    Scenario.HIRE: "Hire more sales people",
    Scenario.CLOSE: "Increase close rate",
    Scenario.CYCLE: "Decrease sales cycle time",
    Scenario.DEAL: "Increase average revenue / transaction",
    Scenario.PRODUCTIVITY: "Increase close and deal size; decrease cycle",
    Scenario.ALL: "Improve all scenarios",
}


class ImprovementRates(BaseModel):
    """Row 7 of the workbook: the % improvement assumed for each single lever."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hire: float = Field(0.10, ge=-1.0)
    close: float = Field(0.10, ge=-1.0)
    cycle: float = Field(0.10, lt=1.0)
    deal: float = Field(0.10, ge=-1.0)

    def levers_for(self, scenario: Scenario) -> Levers:
        """Build the :class:`Levers` the workbook used for ``scenario``."""
        match scenario:
            case Scenario.HIRE:
                return Levers(territory_change=self.hire)
            case Scenario.CLOSE:
                return Levers(close_rate_change=self.close)
            case Scenario.CYCLE:
                return Levers(cycle_time_reduction=self.cycle)
            case Scenario.DEAL:
                return Levers(deal_size_change=self.deal)
            case Scenario.PRODUCTIVITY:
                return Levers(
                    close_rate_change=self.close,
                    cycle_time_reduction=self.cycle,
                    deal_size_change=self.deal,
                )
            case Scenario.ALL:
                return Levers(
                    territory_change=self.hire,
                    close_rate_change=self.close,
                    cycle_time_reduction=self.cycle,
                    deal_size_change=self.deal,
                )


def run_all(
    inputs: ModelInputs,
    rates: ImprovementRates | None = None,
) -> dict[Scenario, Impact]:
    """Evaluate every scenario column against the baseline."""
    rates = rates or ImprovementRates()
    return {s: impact(inputs, rates.levers_for(s)) for s in Scenario}
