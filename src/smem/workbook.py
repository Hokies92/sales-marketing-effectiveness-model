"""Generate the corrected Excel workbook from the reference engine.

The workbook is a *renderer* of :mod:`smem.engine`, not a second implementation:
every cell is a live formula over named input cells, the layout follows the
original's four-sheet flow, and :func:`verify_against_engine` proves (after a
LibreOffice recalculation) that every output cell equals the engine to the cent.

Usage::

    python -m smem.workbook out/SMEM.xlsx
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.worksheet import Worksheet

from smem.diagnostics import load_diagnostics
from smem.engine import Impact, ScenarioResult
from smem.inputs import ModelInputs
from smem.scenarios import SCENARIO_LABELS, ImprovementRates, Scenario, run_all

# ----------------------------------------------------------------------------- styles

FONT = "Arial"
_BASE = Font(name=FONT, size=10)
_BOLD = Font(name=FONT, size=10, bold=True)
_TITLE = Font(name=FONT, size=14, bold=True)
_H2 = Font(name=FONT, size=11, bold=True, color="FFFFFF")
_INPUT = Font(name=FONT, size=10, color="0000FF")
_LINK = Font(name=FONT, size=10, color="008000")
_NOTE = Font(name=FONT, size=9, italic=True, color="595959")
_FILL_H2 = PatternFill("solid", fgColor="1F3864")
_FILL_INPUT = PatternFill("solid", fgColor="FFFF00")
_FILL_TOTAL = PatternFill("solid", fgColor="F2F2F2")
_THIN = Side(style="thin", color="BFBFBF")
_TOP = Border(top=Side(style="thin", color="000000"))
_WRAP = Alignment(wrap_text=True, vertical="top")

FMT_MONEY = "$#,##0;($#,##0);-"
FMT_PCT = "0.0%;(0.0%);-"
FMT_PCT2 = "0.00%;(0.00%);-"
FMT_NUM1 = "#,##0.0"
FMT_INT = "#,##0"

INPUTS = "Inputs"
SCEN = "Scenarios"
IMPACT = "Impact"
DIAG = "Diagnostics"
README = "Read me"

# Scenario column letters — identical to the original so users feel at home.
COLS: Mapping[Scenario, str] = {
    Scenario.HIRE: "E",
    Scenario.CLOSE: "F",
    Scenario.CYCLE: "G",
    Scenario.DEAL: "H",
    Scenario.PRODUCTIVITY: "J",
    Scenario.ALL: "K",
}
BASE_COL = "C"
ALL_COLS = (BASE_COL, *COLS.values())


# ----------------------------------------------------------------------------- inputs sheet


@dataclass(frozen=True, slots=True)
class _InputSpec:
    name: str  # defined name
    label: str
    value: float
    fmt: str
    note: str = ""


def _input_specs(i: ModelInputs) -> list[tuple[str, list[_InputSpec]]]:
    """Section → inputs, in the order of the original Data-entry sheet."""
    c, t, m, o, k, r = i.compensation, i.travel, i.mechanics, i.overhead, i.marketing, i.ratios
    return [
        (
            "Sales force",
            [
                _InputSpec(
                    "Territories",
                    "Number of sales territories",
                    i.territories,
                    FMT_INT,
                    "Open territories last year, whether or not currently staffed.",
                ),
                _InputSpec(
                    "AvgDealSize",
                    "Average revenue per sales transaction",
                    i.avg_revenue_per_transaction,
                    FMT_MONEY,
                    "Drives the model. Compare with the implied figure below.",
                ),
                _InputSpec(
                    "ContractsLastYear",
                    "Number of contracts last year (informational)",
                    i.contracts_last_year or 0,
                    FMT_INT,
                ),
                _InputSpec(
                    "RevenueFromContracts",
                    "Revenue from those contracts (informational)",
                    i.revenue_from_contracts or 0,
                    FMT_MONEY,
                ),
            ],
        ),
        (
            "Rep compensation",
            [
                _InputSpec("BaseSalary", "Average salary per sales rep", c.base_salary, FMT_MONEY),
                _InputSpec(
                    "LoadRate", "Corporate load rate (benefits, overhead)", c.load_rate, FMT_PCT
                ),
                _InputSpec(
                    "CommissionRate",
                    "Average commission (% of revenue)",
                    c.commission_rate,
                    FMT_PCT,
                ),
            ],
        ),
        (
            "Travel per trip",
            [
                _InputSpec(
                    "TripTransport",
                    "Air fare / train / mileage (round trip)",
                    t.transport_round_trip,
                    FMT_MONEY,
                ),
                _InputSpec("TripGround", "Cabs, tolls, car rental", t.ground, FMT_MONEY),
                _InputSpec("TripMealsPerDay", "Meals per day", t.meals_per_day, FMT_MONEY),
                _InputSpec(
                    "TripLodgingPerNight", "Lodging per night", t.lodging_per_night, FMT_MONEY
                ),
                _InputSpec("TripDays", "Days away per trip", t.days_per_trip, FMT_NUM1),
                _InputSpec(
                    "TripEntertainment",
                    "Entertainment per trip",
                    t.entertainment_per_trip,
                    FMT_MONEY,
                ),
                _InputSpec("TripsPerYear", "Trips per year per rep", t.trips_per_year, FMT_INT),
            ],
        ),
        (
            "Sales mechanics",
            [
                _InputSpec(
                    "Capacity",
                    "Pipeline opportunities manageable at one time",
                    m.concurrent_opportunities,
                    FMT_INT,
                    "Work-in-process per rep. Rises with selling time.",
                ),
                _InputSpec(
                    "CycleMonths", "Length of sales cycle (months)", m.cycle_months, FMT_NUM1
                ),
                _InputSpec(
                    "RampMonths",
                    "Sales ramp-up time (months)",
                    m.ramp_months,
                    FMT_NUM1,
                    "New hires produce nothing for this long, then full output.",
                ),
                _InputSpec("CloseRate", "Close rate", m.close_rate, FMT_PCT),
            ],
        ),
        (
            "Sales overhead (annual)",
            [
                _InputSpec(
                    "OhManagers",
                    "Non-quota sales manager salaries",
                    o.non_quota_manager_salaries,
                    FMT_MONEY,
                ),
                _InputSpec(
                    "OhEngineers",
                    "Sales engineers / non-quota support",
                    o.sales_engineers_and_support,
                    FMT_MONEY,
                ),
                _InputSpec(
                    "OhAdmin", "Sales operations and admin", o.sales_admin_and_operations, FMT_MONEY
                ),
                _InputSpec("OhTraining", "Training", o.training, FMT_MONEY),
                _InputSpec(
                    "OhIncentives",
                    "Non-quota incentives (President's Club etc.)",
                    o.incentives_non_quota,
                    FMT_MONEY,
                ),
            ],
        ),
        (
            "Marketing (annual)",
            [
                _InputSpec("MkPersonnel", "Marketing personnel", k.personnel, FMT_MONEY),
                _InputSpec("MkWebsite", "Web site", k.website, FMT_MONEY),
                _InputSpec("MkEvents", "Events", k.events, FMT_MONEY),
                _InputSpec("MkAdvertising", "Advertising", k.advertising, FMT_MONEY),
                _InputSpec("MkDirectMail", "Direct mail", k.direct_mail, FMT_MONEY),
                _InputSpec(
                    "MkTelemarketing",
                    "Telemarketing / lead generation",
                    k.telemarketing_lead_gen,
                    FMT_MONEY,
                ),
                _InputSpec("MkBranding", "Branding and PR", k.branding_and_pr, FMT_MONEY),
                _InputSpec("MkCollateral", "Collateral", k.collateral, FMT_MONEY),
            ],
        ),
        (
            "Income-statement ratios (% of revenue)",
            [
                _InputSpec(
                    "CogsPct",
                    "Cost of revenue",
                    r.cost_of_revenue,
                    FMT_PCT2,
                    "Industry average in the original; replace with actuals.",
                ),
                _InputSpec(
                    "RdPct", "Research and development", r.research_and_development, FMT_PCT2
                ),
                _InputSpec(
                    "GaPct", "General and administrative", r.general_and_administrative, FMT_PCT2
                ),
            ],
        ),
    ]


def _define(wb: Workbook, name: str, sheet: str, cell: str) -> None:
    wb.defined_names[name] = DefinedName(name, attr_text=f"'{sheet}'!${cell[0]}${cell[1:]}")


def _header(ws: Worksheet, row: int, text: str, width_cols: int) -> None:
    ws.cell(row=row, column=2, value=text).font = _H2
    for col in range(2, 2 + width_cols):
        ws.cell(row=row, column=col).fill = _FILL_H2


def _build_inputs(wb: Workbook, inputs: ModelInputs) -> None:
    ws = wb.create_sheet(INPUTS)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 46
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 60

    ws["B1"] = "Sales & Marketing Effectiveness Model — Inputs"
    ws["B1"].font = _TITLE
    ws["B2"] = "Yellow cells with blue text are inputs. Everything else is calculated."
    ws["B2"].font = _NOTE

    row = 4
    for section, specs in _input_specs(inputs):
        _header(ws, row, section, 3)
        row += 1
        for s in specs:
            ws.cell(row=row, column=2, value=s.label).font = _BASE
            c = ws.cell(row=row, column=3, value=s.value)
            c.font, c.fill, c.number_format = _INPUT, _FILL_INPUT, s.fmt
            if s.note:
                ws.cell(row=row, column=4, value=s.note).font = _NOTE
            _define(wb, s.name, INPUTS, f"C{row}")
            row += 1
        row += 1

    # Derived quantities — formulas, named so the other sheets can use them.
    _header(ws, row, "Derived (do not edit)", 3)
    row += 1
    derived = [
        (
            "LoadedSalary",
            "Fully loaded salary per rep",
            "=BaseSalary*(1+LoadRate)",
            FMT_MONEY,
            "Original workbook hard-coded 87,750 here on the scenario sheet (defect Q1).",
        ),
        (
            "TripCost",
            "Cost per trip",
            "=TripTransport+TripGround+TripEntertainment+TripDays*(TripMealsPerDay+TripLodgingPerNight)",
            FMT_MONEY,
            "",
        ),
        ("TravelPerRep", "Travel cost per rep per year", "=TripCost*TripsPerYear", FMT_MONEY, ""),
        (
            "SalesOverhead",
            "Total sales overhead",
            "=OhManagers+OhEngineers+OhAdmin+OhTraining+OhIncentives",
            FMT_MONEY,
            "",
        ),
        (
            "MarketingTotal",
            "Total marketing",
            "=MkPersonnel+MkWebsite+MkEvents+MkAdvertising+MkDirectMail+MkTelemarketing"
            "+MkBranding+MkCollateral",
            FMT_MONEY,
            "",
        ),
        (
            "ImpliedDealSize",
            "Implied deal size (revenue ÷ contracts)",
            "=IF(ContractsLastYear>0,RevenueFromContracts/ContractsLastYear,0)",
            FMT_MONEY,
            "Informational. If this differs materially from the input above, reconcile them.",
        ),
        (
            "DealSizeGap",
            "Gap: input vs implied deal size",
            "=IF(ImpliedDealSize>0,AvgDealSize/ImpliedDealSize-1,0)",
            FMT_PCT,
            "Original collected contracts & revenue but never used them (defect Q3).",
        ),
    ]
    for name, label, formula, fmt, note in derived:
        ws.cell(row=row, column=2, value=label).font = _BASE
        c = ws.cell(row=row, column=3, value=formula)
        c.font, c.number_format = _BASE, fmt
        if note:
            ws.cell(row=row, column=4, value=note).font = _NOTE
        _define(wb, name, INPUTS, f"C{row}")
        row += 1
    ws.freeze_panes = "B4"


# ----------------------------------------------------------------------------- scenarios sheet

RATE_ROW = 7
R_TERR, R_DEAL, R_SAL, R_TRAV, R_COMM, R_COST = 9, 10, 11, 12, 13, 14
R_CAP, R_CYC, R_RAMP, R_CLOSE = 16, 17, 18, 19
R_OPPS, R_DEALS, R_REVREP = 21, 22, 23
R_REV, R_REPCOST = 25, 26

_LEVER_RATE_CELL: Mapping[Scenario, str] = {
    Scenario.HIRE: f"$E${RATE_ROW}",
    Scenario.CLOSE: f"$F${RATE_ROW}",
    Scenario.CYCLE: f"$G${RATE_ROW}",
    Scenario.DEAL: f"$H${RATE_ROW}",
}


def _scenario_levers(s: Scenario) -> set[Scenario]:
    """Which single levers a scenario column pulls."""
    match s:
        case Scenario.PRODUCTIVITY:
            return {Scenario.CLOSE, Scenario.CYCLE, Scenario.DEAL}
        case Scenario.ALL:
            return set(_LEVER_RATE_CELL)
        case _:
            return {s}


def _build_scenarios(wb: Workbook, rates: ImprovementRates) -> None:
    ws = wb.create_sheet(SCEN)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 46
    for col in ALL_COLS:
        ws.column_dimensions[col].width = 16
    ws.column_dimensions["D"].width = 2
    ws.column_dimensions["I"].width = 2

    ws["B2"] = '"What if" performance breakdown'
    ws["B2"].font = _TITLE
    ws["B3"] = (
        "Each column re-runs the revenue engine R = T × (12·P/C) × w × A with one or more "
        "levers moved by the % in row 7 (yellow). Every cell is a live formula."
    )
    ws["B3"].font = _NOTE

    ws["E5"], ws["J5"] = "Individual scenarios", "Combined"
    ws["E5"].font = ws["J5"].font = _BOLD
    ws[f"{BASE_COL}6"] = "Baseline"
    ws[f"{BASE_COL}6"].font = _BOLD
    for s, col in COLS.items():
        c = ws[f"{col}6"]
        c.value, c.font, c.alignment = SCENARIO_LABELS[s], _BOLD, _WRAP
    ws.row_dimensions[6].height = 42
    ws[f"B{RATE_ROW}"] = "Improvement assumed"
    for s, val in (
        (Scenario.HIRE, rates.hire),
        (Scenario.CLOSE, rates.close),
        (Scenario.CYCLE, rates.cycle),
        (Scenario.DEAL, rates.deal),
    ):
        c = ws[f"{COLS[s]}{RATE_ROW}"]
        c.value, c.font, c.fill, c.number_format = val, _INPUT, _FILL_INPUT, FMT_PCT

    labels = {
        8: "Sales representative economics",
        R_TERR: "Number of sales territories (T)",
        R_DEAL: "Average revenue per transaction (A)",
        R_SAL: "Fully loaded salary",
        R_TRAV: "Travel cost per rep",
        R_COMM: "Commission",
        R_COST: "Total cost per rep",
        15: "Sales mechanics",
        R_CAP: "Opportunities manageable at one time (P)",
        R_CYC: "Length of sales cycle, months (C)",
        R_RAMP: "Ramp-up time, months",
        R_CLOSE: "Close rate (w)",
        20: "Individual impact",
        R_OPPS: "Opportunities pursued per year  = 12·P/C",
        R_DEALS: "Transactions per year per rep  = opps × w",
        R_REVREP: "Revenue per rep  = transactions × A",
        24: "Outcomes",
        R_REV: "Total revenue",
        R_REPCOST: "Total sales rep costs",
    }
    for r, text in labels.items():
        cell = ws.cell(row=r, column=2, value=text)
        cell.font = _BASE
    for r in (8, 15, 20, 24):
        _header(ws, r, labels[r], 10)

    def lever(s: Scenario | None, which: Scenario) -> str | None:
        """Rate cell if column ``s`` pulls lever ``which``, else None."""
        return _LEVER_RATE_CELL[which] if s and which in _scenario_levers(s) else None

    col_to_scenario = {v: k for k, v in COLS.items()}
    for col in ALL_COLS:
        scen: Scenario | None = col_to_scenario.get(col)
        f: dict[int, str] = {}
        t = lever(scen, Scenario.HIRE)
        f[R_TERR] = f"=Territories*(1+{t})" if t else "=Territories"
        d = lever(scen, Scenario.DEAL)
        f[R_DEAL] = f"=AvgDealSize*(1+{d})" if d else "=AvgDealSize"
        f[R_SAL] = "=LoadedSalary"
        f[R_TRAV] = "=TravelPerRep"
        f[R_COMM] = f"={col}{R_REVREP}*CommissionRate"
        f[R_COST] = f"=SUM({col}{R_SAL}:{col}{R_COMM})"
        f[R_CAP] = "=Capacity"
        cy = lever(scen, Scenario.CYCLE)
        f[R_CYC] = f"=CycleMonths*(1-{cy})" if cy else "=CycleMonths"
        f[R_RAMP] = "=RampMonths"
        w = lever(scen, Scenario.CLOSE)
        f[R_CLOSE] = f"=MIN(1,CloseRate*(1+{w}))" if w else "=CloseRate"
        f[R_OPPS] = f"=(12/{col}{R_CYC})*{col}{R_CAP}"
        f[R_DEALS] = f"={col}{R_OPPS}*{col}{R_CLOSE}"
        f[R_REVREP] = f"={col}{R_DEALS}*{col}{R_DEAL}"
        # Consistent ramp: added reps earn (12-ramp)/12 of a rep-year; removed reps vanish.
        f[R_REV] = (
            f"={col}{R_REVREP}*(MIN({col}{R_TERR},${BASE_COL}${R_TERR})"
            f"+MAX(0,{col}{R_TERR}-${BASE_COL}${R_TERR})*MAX(0,(12-{col}{R_RAMP})/12))"
        )
        f[R_REPCOST] = f"={col}{R_COST}*{col}{R_TERR}"
        fmts = {
            R_TERR: FMT_INT,
            R_DEAL: FMT_MONEY,
            R_SAL: FMT_MONEY,
            R_TRAV: FMT_MONEY,
            R_COMM: FMT_MONEY,
            R_COST: FMT_MONEY,
            R_CAP: FMT_INT,
            R_CYC: FMT_NUM1,
            R_RAMP: FMT_NUM1,
            R_CLOSE: FMT_PCT,
            R_OPPS: FMT_NUM1,
            R_DEALS: FMT_NUM1,
            R_REVREP: FMT_MONEY,
            R_REV: FMT_MONEY,
            R_REPCOST: FMT_MONEY,
        }
        for r, formula in f.items():
            c = ws[f"{col}{r}"]
            c.value, c.number_format = formula, fmts[r]
            c.font = _LINK if formula.lstrip("=").replace("(", "").isalpha() else _BASE
        for r in (R_COST, R_REV, R_REPCOST):
            ws[f"{col}{r}"].fill = _FILL_TOTAL
            ws[f"{col}{r}"].border = _TOP
    ws[f"{BASE_COL}{R_REV}"].comment = Comment(
        "Revenue = rev/rep × (min(T, T_base) + max(0, T − T_base) × (12 − ramp)/12). "
        "Same formula in every column, so the combined scenario can no longer credit "
        "un-ramped hires with a full year (original defect Q2).",
        "SMEM",
    )
    ws.freeze_panes = "C8"


# ----------------------------------------------------------------------------- impact sheet

I_REV, I_DREV, I_DREPCOST, I_SALES, I_MKT, I_SM = 8, 9, 12, 13, 14, 15
I_COGS, I_RD, I_SMX, I_GA, I_OPEX, I_OI = 18, 19, 20, 21, 22, 23
I_NET, I_ROI, I_MARGIN, I_DOI, I_OIGROWTH, I_REVGROWTH = 26, 27, 28, 29, 30, 31


def _build_impact(wb: Workbook) -> None:
    ws = wb.create_sheet(IMPACT)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 40
    for col in ALL_COLS:
        ws.column_dimensions[col].width = 16
    ws.column_dimensions["D"].width = 2
    ws.column_dimensions["I"].width = 2
    ws["B2"] = "Financial impact"
    ws["B2"].font = _TITLE
    ws["B3"] = (
        "Operating income is affine in revenue: OI = R·(1 − commission − COGS% − R&D% − G&A%) "
        "− T·(loaded salary + travel) − overhead − marketing."
    )
    ws["B3"].font = _NOTE
    ws[f"{BASE_COL}6"] = "Baseline"
    ws[f"{BASE_COL}6"].font = _BOLD
    for s, col in COLS.items():
        c = ws[f"{col}6"]
        c.value, c.font, c.alignment = SCENARIO_LABELS[s], _BOLD, _WRAP
    ws.row_dimensions[6].height = 42

    labels = {
        7: "Revenue",
        I_REV: "Total revenue",
        I_DREV: "Increase in revenue from base",
        11: "Costs",
        I_DREPCOST: "Increase in sales rep costs",
        I_SALES: "Total sales costs",
        I_MKT: "Total marketing costs",
        I_SM: "Total sales and marketing costs",
        17: "Operating expenses",
        I_COGS: "Cost of revenue",
        I_RD: "Research and development",
        I_SMX: "Sales and marketing",
        I_GA: "General and administrative",
        I_OPEX: "Total operating expenses",
        I_OI: "Operating income",
        25: "Metrics",
        I_NET: "Percentage net gain  (ΔR − Δrep cost) / base R",
        I_ROI: "Sales & marketing ROI  (R − S&M) / S&M",
        I_MARGIN: "Operating margin",
        I_DOI: "Change in operating income",
        I_OIGROWTH: "Operating income growth",
        I_REVGROWTH: "Revenue growth",
    }
    for r, text in labels.items():
        ws.cell(row=r, column=2, value=text).font = _BASE
    for r in (7, 11, 17, 25):
        _header(ws, r, labels[r], 10)

    base = f"${BASE_COL}"
    for col in ALL_COLS:
        is_base = col == BASE_COL
        f = {
            I_REV: f"='{SCEN}'!{col}{R_REV}",
            I_SALES: f"='{SCEN}'!{col}{R_REPCOST}+SalesOverhead",
            I_MKT: "=MarketingTotal",
            I_SM: f"={col}{I_SALES}+{col}{I_MKT}",
            I_COGS: f"={col}{I_REV}*CogsPct",
            I_RD: f"={col}{I_REV}*RdPct",
            I_SMX: f"={col}{I_SM}",
            I_GA: f"={col}{I_REV}*GaPct",
            I_OPEX: f"=SUM({col}{I_COGS}:{col}{I_GA})",
            I_OI: f"={col}{I_REV}-{col}{I_OPEX}",
            I_ROI: f"=IF({col}{I_SM}=0,0,({col}{I_REV}-{col}{I_SM})/{col}{I_SM})",
            I_MARGIN: f"=IF({col}{I_REV}=0,0,{col}{I_OI}/{col}{I_REV})",
        }
        if not is_base:
            f |= {
                I_DREV: f"={col}{I_REV}-{base}${I_REV}",
                I_DREPCOST: f"='{SCEN}'!{col}{R_REPCOST}-'{SCEN}'!{base}${R_REPCOST}",
                I_NET: f"=IF({base}${I_REV}=0,0,({col}{I_DREV}-{col}{I_DREPCOST})/{base}${I_REV})",
                I_DOI: f"={col}{I_OI}-{base}${I_OI}",
                I_OIGROWTH: f"=IF({base}${I_OI}=0,0,{col}{I_DOI}/{base}${I_OI})",
                I_REVGROWTH: f"=IF({base}${I_REV}=0,0,{col}{I_DREV}/{base}${I_REV})",
            }
        pct_rows = {I_NET, I_ROI, I_MARGIN, I_OIGROWTH, I_REVGROWTH}
        for r, formula in f.items():
            c = ws[f"{col}{r}"]
            c.value = formula
            c.number_format = FMT_PCT if r in pct_rows else FMT_MONEY
            c.font = _LINK if formula.startswith(f"='{SCEN}'") else _BASE
        for r in (I_SM, I_OPEX, I_OI):
            ws[f"{col}{r}"].fill = _FILL_TOTAL
            ws[f"{col}{r}"].border = _TOP
    ws.freeze_panes = "C7"


# ----------------------------------------------------------------------------- text sheets


def _build_diagnostics(wb: Workbook) -> None:
    ws = wb.create_sheet(DIAG)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 110
    ws["B2"] = "Issues preventing achievement of each scenario"
    ws["B2"].font = _TITLE
    ws["B3"] = (
        "Five common obstacles per scenario, from the original tool. Not exhaustive; "
        "use as a checklist when deciding which lever is realistic for your organisation."
    )
    ws["B3"].font = _NOTE
    row = 5
    for block in load_diagnostics():
        _header(ws, row, block.label, 2)
        row += 1
        for n, issue in enumerate(block.issues, 1):
            a = ws.cell(row=row, column=2, value=f"{n}) {issue.issue}")
            b = ws.cell(row=row, column=3, value=issue.reason)
            a.font, b.font = _BOLD, _BASE
            a.alignment = b.alignment = _WRAP
            ws.row_dimensions[row].height = max(30, 15 * (len(issue.reason) // 110 + 1))
            row += 1
        row += 1


def _build_readme(wb: Workbook) -> None:
    ws = wb.create_sheet(README, 0)
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 120
    lines: Iterable[tuple[str, Font]] = [
        ("Sales & Marketing Effectiveness Model", _TITLE),
        ("", _BASE),
        (
            "Rebuilt from the 2011 Forrester Sales and Marketing Efficiency Modeling Tool "
            "(Scott Santucci). Generated by the smem Python package; do not edit formulas by "
            "hand — edit the engine and regenerate.",
            _BASE,
        ),
        ("", _BASE),
        ("How it works", _BOLD),
        ("Revenue is a throughput identity:  R = T × (12·P / C) × w × A", _BASE),
        (
            "   T territories · P opportunities per rep in process · C cycle months · "
            "w close rate · A average deal size",
            _BASE,
        ),
        (
            "Per rep, 12·P/C is Little's Law (throughput = work-in-process ÷ residence time). "
            "The four scenarios move T, w, C and A by the percentages on the Scenarios sheet.",
            _BASE,
        ),
        ("", _BASE),
        ("Sheets", _BOLD),
        ("1. Inputs — yellow cells are yours. Everything is a named range.", _BASE),
        ("2. Scenarios — per-rep economics and revenue under each scenario.", _BASE),
        ("3. Impact — income statement, net gain, ROI, margin and growth per scenario.", _BASE),
        ("4. Diagnostics — common obstacles to realising each scenario.", _BASE),
        ("", _BASE),
        ("Corrections versus the original workbook", _BOLD),
        (
            "Q1  Loaded salary was hard-coded at 87,750 on the scenario sheet; now linked "
            "(116,850 at defaults). Rep costs were understated by $2.9M.",
            _BASE,
        ),
        (
            "Q2  The 'Improve all' column credited un-ramped new hires with a full year of "
            "improved revenue; ramp is now applied identically in every column. At defaults this "
            "removes $15.1M of phantom revenue and reverses the ranking of the two combined "
            "scenarios.",
            _BASE,
        ),
        (
            "Q3  Contracts and revenue were collected but ignored; the implied deal size and its "
            "gap to the input are now shown on Inputs.",
            _BASE,
        ),
        ("", _BASE),
        ("Modelling assumptions (unchanged from the original)", _BOLD),
        (
            "Travel is fixed per rep. Overhead and marketing do not change with scenario. "
            "COGS, R&D and G&A scale with revenue. New hires produce nothing until ramped, "
            "then full output (year-one view).",
            _BASE,
        ),
    ]
    for r, (text, font) in enumerate(lines, 1):
        c = ws.cell(row=r, column=2, value=text)
        c.font, c.alignment = font, _WRAP


# ----------------------------------------------------------------------------- public API


def build_workbook(
    inputs: ModelInputs | None = None,
    rates: ImprovementRates | None = None,
) -> Workbook:
    """Build the workbook in memory. Formulas are not evaluated until Excel/LibreOffice opens it."""
    inputs = inputs or ModelInputs()
    rates = rates or ImprovementRates()
    wb = Workbook()
    for default_sheet in list(wb.worksheets):  # we create every sheet explicitly
        wb.remove(default_sheet)
    _build_inputs(wb, inputs)
    _build_scenarios(wb, rates)
    _build_impact(wb)
    _build_diagnostics(wb)
    _build_readme(wb)
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return wb


def write_workbook(
    path: Path,
    inputs: ModelInputs | None = None,
    rates: ImprovementRates | None = None,
) -> Path:
    """Build and save the workbook to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    build_workbook(inputs, rates).save(path)
    return path


@dataclass(frozen=True, slots=True)
class Mismatch:
    """One cell whose recalculated value disagrees with the engine."""

    cell: str
    workbook: float | None
    engine: float


def expected_cells(
    inputs: ModelInputs | None = None,
    rates: ImprovementRates | None = None,
) -> dict[str, float]:
    """Return the engine's value for every output cell on the Scenarios and Impact sheets."""
    inputs = inputs or ModelInputs()
    results = run_all(inputs, rates)
    out: dict[str, float] = {}

    def put(r: ScenarioResult, scen_col: str, res: Impact | None) -> None:
        s, i = f"'{SCEN}'!{scen_col}", f"'{IMPACT}'!{scen_col}"
        out.update(
            {
                f"{s}{R_TERR}": r.inputs.territories,
                f"{s}{R_DEAL}": r.inputs.avg_revenue_per_transaction,
                f"{s}{R_SAL}": r.rep.loaded_salary,
                f"{s}{R_TRAV}": r.rep.travel,
                f"{s}{R_COMM}": r.rep.commission,
                f"{s}{R_COST}": r.rep.total_cost,
                f"{s}{R_CYC}": r.inputs.mechanics.cycle_months,
                f"{s}{R_CLOSE}": r.inputs.mechanics.close_rate,
                f"{s}{R_OPPS}": r.rep.opportunities_per_year,
                f"{s}{R_DEALS}": r.rep.deals_per_year,
                f"{s}{R_REVREP}": r.rep.revenue,
                f"{s}{R_REV}": r.revenue,
                f"{s}{R_REPCOST}": r.rep_costs,
                f"{i}{I_REV}": r.revenue,
                f"{i}{I_SALES}": r.total_sales_costs,
                f"{i}{I_SM}": r.sales_and_marketing,
                f"{i}{I_COGS}": r.cost_of_revenue,
                f"{i}{I_RD}": r.research_and_development,
                f"{i}{I_GA}": r.general_and_administrative,
                f"{i}{I_OPEX}": r.total_operating_expenses,
                f"{i}{I_OI}": r.operating_income,
                f"{i}{I_ROI}": r.sales_and_marketing_roi,
                f"{i}{I_MARGIN}": r.operating_margin,
            }
        )
        if res is not None:
            out.update(
                {
                    f"{i}{I_DREV}": res.revenue_delta,
                    f"{i}{I_DREPCOST}": res.rep_cost_delta,
                    f"{i}{I_NET}": res.net_gain_pct,
                    f"{i}{I_DOI}": res.operating_income_delta,
                    f"{i}{I_OIGROWTH}": res.operating_income_growth_pct,
                    f"{i}{I_REVGROWTH}": res.revenue_growth_pct,
                }
            )

    put(results[Scenario.HIRE].baseline, BASE_COL, None)
    for scen, col in COLS.items():
        put(results[scen].scenario, col, results[scen])
    return out


def verify_against_engine(
    recalculated_path: Path,
    inputs: ModelInputs | None = None,
    rates: ImprovementRates | None = None,
    *,
    rel_tol: float = 1e-9,
) -> list[Mismatch]:
    """Compare a *recalculated* workbook's cached values to the engine. Empty list = pass."""
    wb = load_workbook(recalculated_path, data_only=True)
    mismatches: list[Mismatch] = []
    for ref, want in expected_cells(inputs, rates).items():
        sheet, cell = ref.split("!")
        got = wb[sheet.strip("'")][cell].value
        ok = isinstance(got, int | float) and abs(got - want) <= max(rel_tol * abs(want), 1e-6)
        if not ok:
            mismatches.append(Mismatch(ref, got if isinstance(got, int | float) else None, want))
    return mismatches


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m smem.workbook OUTPUT.xlsx", file=sys.stderr)
        return 2
    out = write_workbook(Path(argv[1]))
    print(f"wrote {out} ({len(expected_cells())} verifiable output cells)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main(sys.argv))


__all__ = [
    "Mismatch",
    "build_workbook",
    "expected_cells",
    "verify_against_engine",
    "write_workbook",
]
