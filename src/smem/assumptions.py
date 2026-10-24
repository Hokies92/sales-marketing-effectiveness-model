"""Assumption management: every baseline input carries a source and status.

Principle (spec §2): *assumptions do not need to equal actuals, but the model
must always know which it is using.* A :class:`Baseline` wraps a
:class:`~smem.inputs.ModelInputs` with per-field provenance and an
:class:`OperatingPolicy`, and can report where an assumption disagrees with
a value derivable from actuals.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveFloat

from smem.inputs import ModelInputs


class Source(StrEnum):
    """Where a value came from, in ascending order of precedence."""

    DEFAULT = "default"  # shipped illustrative value
    DERIVED = "derived"  # calculated from other inputs (e.g. revenue ÷ contracts)
    ASSUMPTION = "assumption"  # user-supplied estimate or deliberate override
    ACTUAL = "actual"  # observed company data


_PRECEDENCE: dict[Source, int] = {s: i for i, s in enumerate(Source)}


class Provenance(BaseModel):
    """Source and optional note for one input path such as ``mechanics.close_rate``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Source
    note: str = ""


class RampPolicy(StrEnum):
    """How a new hire's first-year productivity is counted."""

    STEP = "step"  # 0 until ramp_months, then 100 %  → (12 − ramp)/12
    LINEAR = "linear"  # linear 0→100 % over ramp_months → 1 − ramp/24


class Horizon(StrEnum):
    """Which year the scenario reports."""

    YEAR_ONE = "year_one"  # ramp, time-to-benefit and one-time costs apply
    STEADY_STATE = "steady_state"  # everyone ramped, benefits fully realised


class OperatingPolicy(BaseModel):
    """Behavioural rules the original workbook left implicit (spec §3–§4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    employed_sellers: PositiveFloat | None = Field(
        None, description="Filled seats. None → equals territories (the original's assumption)."
    )
    qualified_demand_per_year: PositiveFloat | None = Field(
        None,
        description="Qualified opportunities available per year. None → capacity is never "
        "demand-limited (the original's assumption).",
    )
    ramp_policy: RampPolicy = RampPolicy.STEP
    horizon: Horizon = Horizon.YEAR_ONE
    ramping_hire_draw: NonNegativeFloat = Field(
        0.0,
        description="Annual guaranteed pay for a hire while un-ramped, in currency. The original "
        "charged full commission to zero-revenue hires; v2 charges commission on realised "
        "revenue plus this explicit draw.",
    )
    manager_span: PositiveFloat | None = Field(
        None, description="Sellers per first-line manager. None → no step-fixed management cost."
    )
    manager_loaded_cost: NonNegativeFloat = Field(
        0.0, description="Annual loaded cost of one additional first-line manager."
    )


@dataclass(frozen=True, slots=True)
class Discrepancy:
    """An assumption that disagrees with a value derivable from actuals."""

    path: str
    assumed: float
    derived: float
    note: str

    @property
    def gap_pct(self) -> float:
        """Assumed ÷ derived − 1."""
        return self.assumed / self.derived - 1.0 if self.derived else math.inf


class Baseline(BaseModel):
    """Inputs + provenance + policy. Immutable; use ``with_*`` to derive a new one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inputs: ModelInputs = Field(default_factory=ModelInputs)
    policy: OperatingPolicy = Field(default_factory=OperatingPolicy)
    provenance: Mapping[str, Provenance] = Field(default_factory=dict)
    name: str = "baseline"

    # ------------------------------------------------------------------ construction

    @classmethod
    def from_defaults(cls, name: str = "illustrative company") -> Baseline:
        """Build the shipped fictitious company with every input tagged DEFAULT."""
        return cls(name=name, provenance={p: Provenance(source=Source.DEFAULT) for p in _paths()})

    def with_value(self, path: str, value: Any, source: Source, note: str = "") -> Baseline:
        """Return a new baseline with ``path`` set to ``value`` and tagged ``source``.

        Precedence is advisory: a lower-precedence write over a higher one is allowed
        (the user may deliberately test a hypothetical) but the provenance records it.
        """
        new_inputs = _set_path(self.inputs, path, value)
        prov = dict(self.provenance)
        prov[path] = Provenance(source=source, note=note)
        return self.model_copy(update={"inputs": new_inputs, "provenance": prov})

    def with_policy(self, **changes: Any) -> Baseline:
        """Return a new baseline with policy fields replaced."""
        return self.model_copy(update={"policy": self.policy.model_copy(update=changes)})

    # ------------------------------------------------------------------ queries

    def source_of(self, path: str) -> Source:
        """Provenance of ``path`` (DEFAULT when never tagged)."""
        p = self.provenance.get(path)
        return p.source if p else Source.DEFAULT

    def inputs_by_source(self) -> dict[Source, list[str]]:
        """Group every known path by its source."""
        out: dict[Source, list[str]] = {s: [] for s in Source}
        for path in _paths():
            out[self.source_of(path)].append(path)
        return out

    def discrepancies(self, tolerance: float = 0.05) -> list[Discrepancy]:
        """Assumptions that differ from derivable actuals by more than ``tolerance``."""
        found: list[Discrepancy] = []
        implied = self.inputs.implied_avg_revenue_per_transaction
        assumed = self.inputs.avg_revenue_per_transaction
        if implied and abs(assumed / implied - 1.0) > tolerance:
            found.append(
                Discrepancy(
                    path="avg_revenue_per_transaction",
                    assumed=assumed,
                    derived=implied,
                    note="revenue_from_contracts ÷ contracts_last_year",
                )
            )
        return found

    def overrides_actuals(self) -> list[str]:
        """Paths where an ASSUMPTION/DEFAULT sits above an available ACTUAL-derived value."""
        return [
            d.path
            for d in self.discrepancies()
            if _PRECEDENCE[self.source_of(d.path)] < _PRECEDENCE[Source.ACTUAL]
        ]


# ---------------------------------------------------------------------- path helpers


def _paths() -> list[str]:
    """Dotted paths of every leaf input on :class:`ModelInputs`."""
    out: list[str] = []
    for name, field in ModelInputs.model_fields.items():
        ann = field.annotation
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            out.extend(f"{name}.{sub}" for sub in ann.model_fields)
        else:
            out.append(name)
    return out


def _set_path(inputs: ModelInputs, path: str, value: Any) -> ModelInputs:
    head, _, tail = path.partition(".")
    if head not in ModelInputs.model_fields:
        msg = f"unknown input path {path!r}"
        raise KeyError(msg)
    # Always re-validate so field constraints (ranges, > 0) still apply.
    if not tail:
        return ModelInputs.model_validate({**inputs.model_dump(), head: value})
    block = getattr(inputs, head)
    if not isinstance(block, BaseModel) or tail not in type(block).model_fields:
        msg = f"unknown input path {path!r}"
        raise KeyError(msg)
    new_block = {**block.model_dump(), tail: value}
    return ModelInputs.model_validate({**inputs.model_dump(), head: new_block})


__all__ = [
    "Baseline",
    "Discrepancy",
    "Horizon",
    "OperatingPolicy",
    "Provenance",
    "RampPolicy",
    "Source",
]
