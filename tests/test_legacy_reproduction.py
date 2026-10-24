"""Prove the legacy reproduction matches the shipped workbook cell-for-cell."""

from __future__ import annotations

import math

import pytest

from smem.legacy import legacy_workbook_values


@pytest.fixture(scope="module")
def legacy() -> dict[str, float]:
    return legacy_workbook_values()


def test_every_legacy_cell_matches_original(
    legacy: dict[str, float], original_cached_values: dict[str, float]
) -> None:
    missing = [k for k in legacy if k not in original_cached_values]
    assert not missing, f"cells computed but absent from original: {missing}"

    mismatches = {
        k: (v, original_cached_values[k])
        for k, v in legacy.items()
        if not math.isclose(v, original_cached_values[k], rel_tol=1e-9, abs_tol=1e-6)
    }
    assert not mismatches, f"{len(mismatches)} mismatching cells: {mismatches}"


def test_coverage_of_original_formula_cells(
    legacy: dict[str, float], original_cached_values: dict[str, float]
) -> None:
    """Every numeric cell on sheets 2 & 3 that carries logic must be reproduced.

    Exclusions are documented: row 7 are the input percentages, I7/I9 are a stray
    spacer-column formula, rows 30-32 are input ratios, and sheet-2 rows 9-19 in
    column C are pure echoes of Data-entry inputs.
    """
    s2, s3 = "'2) Performance breakdown'", "'3) Impact Analysis'"
    expected_logic_cells = {
        k
        for k in original_cached_values
        if k.startswith((s2, s3))
        and not k.endswith(("7", "I9", "C30", "C31", "C32"))
        and k[k.index("!") + 1] != "I"
    }
    not_reproduced = sorted(expected_logic_cells - legacy.keys())
    assert not_reproduced == [], not_reproduced


@pytest.mark.parametrize(
    ("cell", "value"),
    [
        ("'2) Performance breakdown'!C25", 112_500_000),
        ("'2) Performance breakdown'!K25", 166_375_000),
        ("'3) Impact Analysis'!C23", 31_813_750),
        ("'3) Impact Analysis'!K26", 0.428_555_555_555_556),
        ("'3) Impact Analysis'!C27", 2.038_487_508_440_24),
    ],
)
def test_headline_numbers(legacy: dict[str, float], cell: str, value: float) -> None:
    assert legacy[cell] == pytest.approx(value, rel=1e-12)
