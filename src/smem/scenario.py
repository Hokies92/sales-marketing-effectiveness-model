"""Scenarios as first-class objects (spec §5).

A :class:`Scenario` is a named bundle of :class:`Intervention` objects applied to a
baseline. Each intervention moves one or more :class:`LeverSet` dimensions and may
carry its own economics: recurring programme cost, one-time cost, months before the
benefit starts, and a probability of success. Scenarios inherit everything from the
baseline except what they explicitly change, so side-by-side comparison is meaningful.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat

from smem.assumptions import Horizon
from smem.inputs import MONTHS_PER_YEAR


class Lever(StrEnum):
    """The six dimensions a scenario can move. ``R = N·(12P/C)·w·A``, bounded by demand."""

    TERRITORIES = "territories"  # T  (and employed sellers)
    CAPACITY = "capacity"  # P  concurrent opportunities per seller
    CLOSE_RATE = "close_rate"  # w
    CYCLE_TIME = "cycle_time"  # C  (reduction is the improvement)
    DEAL_SIZE = "deal_size"  # A
    DEMAND = "demand"  # qualified opportunities available


class LeverSet(BaseModel):
    """Proportional changes. Positive is always *improvement* (cycle: a reduction)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    territory_change: float = Field(0.0, ge=-1.0)
    capacity_change: float = Field(0.0, ge=-1.0)
    close_rate_change: float = Field(0.0, ge=-1.0)
    cycle_time_reduction: float = Field(0.0, lt=1.0)
    deal_size_change: float = Field(0.0, ge=-1.0)
    demand_change: float = Field(0.0, ge=-1.0)

    def get(self, lever: Lever) -> float:
        """Read the change for ``lever``."""
        return float(getattr(self, _FIELD[lever]))

    @classmethod
    def single(cls, lever: Lever, change: float) -> LeverSet:
        """Build a lever set that moves exactly one lever."""
        return cls(**{_FIELD[lever]: change})

    def scaled(self, fraction: float) -> LeverSet:
        """Every change multiplied by ``fraction`` (used for partial-year realisation)."""
        return LeverSet(**{f: getattr(self, f) * fraction for f in _FIELD.values()})

    def compose(self, other: LeverSet) -> LeverSet:
        """Multiplicative composition: ``(1+a)(1+b) − 1``; cycle uses ``1 − (1−a)(1−b)``."""
        out: dict[str, float] = {}
        for lever, f in _FIELD.items():
            a, b = getattr(self, f), getattr(other, f)
            if lever is Lever.CYCLE_TIME:
                out[f] = 1.0 - (1.0 - a) * (1.0 - b)
            else:
                out[f] = (1.0 + a) * (1.0 + b) - 1.0
        return LeverSet(**out)

    @property
    def is_empty(self) -> bool:
        """True when nothing moves."""
        return all(getattr(self, f) == 0.0 for f in _FIELD.values())


_FIELD: dict[Lever, str] = {
    Lever.TERRITORIES: "territory_change",
    Lever.CAPACITY: "capacity_change",
    Lever.CLOSE_RATE: "close_rate_change",
    Lever.CYCLE_TIME: "cycle_time_reduction",
    Lever.DEAL_SIZE: "deal_size_change",
    Lever.DEMAND: "demand_change",
}


class Intervention(BaseModel):
    """One deliberate change with its own economics.

    The original workbook modelled every improvement as free and instantaneous.
    Here each one may cost money, take time, and fail.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    levers: LeverSet = Field(default_factory=LeverSet)
    annual_cost: NonNegativeFloat = Field(0.0, description="Recurring programme cost per year")
    one_time_cost: NonNegativeFloat = Field(0.0, description="Charged in year one only")
    months_to_benefit: float = Field(
        0.0, ge=0.0, le=MONTHS_PER_YEAR, description="Delay before the lever change takes effect"
    )
    success_probability: float = Field(1.0, ge=0.0, le=1.0)

    def effective_levers(self, horizon: Horizon) -> LeverSet:
        """Lever changes realised within ``horizon``.

        Year one credits the average over the year under a step benefit profile:
        ``(12 − months_to_benefit) / 12``. Steady state credits the full change.
        """
        if horizon is Horizon.STEADY_STATE:
            return self.levers
        return self.levers.scaled((MONTHS_PER_YEAR - self.months_to_benefit) / MONTHS_PER_YEAR)

    def cost(self, horizon: Horizon) -> float:
        """Programme cost charged in ``horizon``."""
        one_time = self.one_time_cost if horizon is Horizon.YEAR_ONE else 0.0
        return self.annual_cost + one_time


class Scenario(BaseModel):
    """A named, reproducible bundle of interventions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    interventions: tuple[Intervention, ...] = ()
    description: str = ""

    @classmethod
    def baseline(cls) -> Scenario:
        """Build the do-nothing scenario."""
        return cls(name="baseline")

    @classmethod
    def of(cls, name: str, levers: LeverSet, **intervention_kwargs: float) -> Scenario:
        """Build a one-intervention scenario from a lever set."""
        return cls(
            name=name,
            interventions=(Intervention(name=name, levers=levers, **intervention_kwargs),),
        )

    def effective_levers(self, horizon: Horizon) -> LeverSet:
        """All interventions composed multiplicatively."""
        total = LeverSet()
        for i in self.interventions:
            total = total.compose(i.effective_levers(horizon))
        return total

    def programme_cost(self, horizon: Horizon) -> float:
        """Sum of intervention costs in ``horizon`` (discretionary cost line)."""
        return sum(i.cost(horizon) for i in self.interventions)

    def joint_success_probability(self) -> float:
        """Product of intervention probabilities (independence assumed)."""
        p = 1.0
        for i in self.interventions:
            p *= i.success_probability
        return p

    def with_intervention(self, intervention: Intervention) -> Scenario:
        """Return a new scenario with one more intervention."""
        return self.model_copy(update={"interventions": (*self.interventions, intervention)})


def combine(name: str, scenarios: Iterable[Scenario]) -> Scenario:
    """Merge several scenarios' interventions into one."""
    interventions: list[Intervention] = []
    for s in scenarios:
        interventions.extend(s.interventions)
    return Scenario(name=name, interventions=tuple(interventions))


__all__ = ["Intervention", "Lever", "LeverSet", "Scenario", "combine"]
