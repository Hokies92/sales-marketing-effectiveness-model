from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_XLSX = (
    REPO_ROOT
    / "reference"
    / "original"
    / "Sales_and_Marketing_Effectiveness_Model_-_update.converted.xlsx"
)


@pytest.fixture(scope="session")
def original_cached_values() -> dict[str, float]:
    """Every numeric cached value from the original workbook, keyed ``'<sheet>'!<cell>``.

    The .xlsx is a LibreOffice conversion of the shipped .xls; cached values are
    what Excel last calculated, so this is ground truth for the legacy model.
    """
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(ORIGINAL_XLSX, data_only=True)
    out: dict[str, float] = {}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool):
                    out[f"'{ws.title}'!{cell.coordinate}"] = float(cell.value)
    return out
