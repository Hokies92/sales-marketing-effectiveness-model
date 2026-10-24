"""Sales & Marketing Effectiveness Model (SMEM).

Public surface::

    from smem import ModelInputs, Levers, evaluate, impact, run_all
"""

from smem.engine import (
    Impact,
    Levers,
    RepEconomics,
    ScenarioResult,
    apply_levers,
    evaluate,
    impact,
    ramp_productivity,
    rep_economics,
)
from smem.inputs import (
    IncomeStatementRatios,
    MarketingSpend,
    ModelInputs,
    RepCompensation,
    SalesMechanics,
    SalesOverhead,
    TravelProfile,
)
from smem.scenarios import SCENARIO_LABELS, ImprovementRates, Scenario, run_all

__all__ = [
    "SCENARIO_LABELS",
    "Impact",
    "ImprovementRates",
    "IncomeStatementRatios",
    "Levers",
    "MarketingSpend",
    "ModelInputs",
    "RepCompensation",
    "RepEconomics",
    "SalesMechanics",
    "SalesOverhead",
    "Scenario",
    "ScenarioResult",
    "TravelProfile",
    "apply_levers",
    "evaluate",
    "impact",
    "ramp_productivity",
    "rep_economics",
    "run_all",
]

__version__ = "0.1.0"
