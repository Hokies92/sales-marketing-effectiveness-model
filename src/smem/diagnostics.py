"""Qualitative obstacles per scenario (original sheet ``4) Scenario Diagnostic``).

The text is data, not code: it lives in ``data/diagnostics.json`` so the
workbook builder, the web UI and the AI narrative layer all cite one source.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources

from pydantic import BaseModel, ConfigDict, TypeAdapter

from smem.scenarios import Scenario


class Issue(BaseModel):
    """One obstacle and the reasoning behind it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue: str
    reason: str


class ScenarioDiagnostic(BaseModel):
    """The obstacles that stand between a company and one scenario's gains."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: Scenario
    label: str
    issues: tuple[Issue, ...]


_ADAPTER = TypeAdapter(tuple[ScenarioDiagnostic, ...])


@cache
def load_diagnostics() -> tuple[ScenarioDiagnostic, ...]:
    """Load and validate the bundled diagnostics once per process."""
    raw = resources.files("smem").joinpath("data/diagnostics.json").read_text(encoding="utf-8")
    return _ADAPTER.validate_python(json.loads(raw))


def diagnostics_for(scenario: Scenario) -> ScenarioDiagnostic | None:
    """Return the diagnostic block for ``scenario`` if the original defined one."""
    return next((d for d in load_diagnostics() if d.scenario is scenario), None)
