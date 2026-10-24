"""The generated workbook must agree with the engine after a real spreadsheet recalculation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from smem import ImprovementRates, ModelInputs, SalesMechanics
from smem.diagnostics import diagnostics_for, load_diagnostics
from smem.scenarios import Scenario
from smem.workbook import build_workbook, expected_cells, verify_against_engine, write_workbook

openpyxl = pytest.importorskip("openpyxl")
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


def _recalculate(path: Path) -> Path:
    """Round-trip through LibreOffice so formula cells acquire cached values."""
    out_dir = path.parent / "recalc"
    out_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(SOFFICE),
            "--headless",
            "--convert-to",
            "xlsx",
            "--outdir",
            str(out_dir),
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return out_dir / path.name


ALT_INPUTS = ModelInputs(
    territories=42,
    avg_revenue_per_transaction=120_000,
    mechanics=SalesMechanics(
        concurrent_opportunities=18, cycle_months=9, ramp_months=6, close_rate=0.31
    ),
)
ALT_RATES = ImprovementRates(hire=-0.15, close=0.2, cycle=0.25, deal=0.05)


def test_workbook_builds_with_expected_sheets() -> None:
    wb = build_workbook()
    assert wb.sheetnames == ["Read me", "Inputs", "Scenarios", "Impact", "Diagnostics"]
    assert {"Territories", "LoadedSalary", "CogsPct", "MarketingTotal"} <= set(wb.defined_names)


def test_every_formula_uses_names_not_literals() -> None:
    """No hard-coded numbers inside Scenarios/Impact formulas except the 12-month constant."""
    wb = build_workbook()
    import re

    for sheet in ("Scenarios", "Impact"):
        for row in wb[sheet].iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    literals = set(re.findall(r"(?<![A-Za-z$\d])\d+(?:\.\d+)?(?![\d])", c.value))
                    literals -= {"0", "1", "12"}  # guards, ramp fraction
                    # row numbers inside references are letters+digits, excluded by lookbehind
                    assert not literals, f"{sheet}!{c.coordinate}: {c.value}"


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice not available for recalculation")
@pytest.mark.parametrize(
    ("inputs", "rates"),
    [(ModelInputs(), ImprovementRates()), (ALT_INPUTS, ALT_RATES)],
    ids=["defaults", "alt-inputs-with-headcount-cut-and-6mo-ramp"],
)
def test_recalculated_workbook_matches_engine(
    tmp_path: Path, inputs: ModelInputs, rates: ImprovementRates
) -> None:
    path = write_workbook(tmp_path / "smem.xlsx", inputs, rates)
    recalculated = _recalculate(path)
    mismatches = verify_against_engine(recalculated, inputs, rates)
    assert mismatches == [], mismatches[:10]
    assert len(expected_cells(inputs, rates)) >= 190


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice not available for recalculation")
def test_recalculated_workbook_has_no_formula_errors(tmp_path: Path) -> None:
    recalculated = _recalculate(write_workbook(tmp_path / "smem.xlsx"))
    wb = openpyxl.load_workbook(recalculated, data_only=True)
    errors = [
        f"{ws.title}!{c.coordinate}={c.value}"
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for c in row
        if isinstance(c.value, str) and c.value.startswith("#")
    ]
    assert errors == []


def test_diagnostics_data_is_complete() -> None:
    blocks = load_diagnostics()
    assert len(blocks) == 3
    assert all(len(b.issues) == 5 for b in blocks)
    assert diagnostics_for(Scenario.CLOSE) is not None
    assert diagnostics_for(Scenario.HIRE) is None  # the original offered none for hiring
