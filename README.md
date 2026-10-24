# SMEM — Sales & Marketing Effectiveness Model

A production rebuild of the 2011 Forrester *Sales and Marketing Efficiency Modeling Tool*
(Scott Santucci), reconstructed from first principles as a **throughput model of the
B2B revenue engine**, and delivered in three forms:

1. a validated Python reference engine (this package),
2. a corrected Excel workbook generated *from* the engine, and
3. a web calculator with AI-assisted analytics and an opt-in benchmark store.

## The model in one line

```
R = T · (12·P / C) · w · A
```

| symbol | meaning | lever |
|---|---|---|
| `T` | sales territories | hire / cut |
| `P` | opportunities a rep can work concurrently | (implicit — capacity) |
| `C` | sales-cycle length, months | shorten |
| `w` | close rate | raise |
| `A` | average revenue per transaction | raise |

Per rep, `12·P/C` is Little's Law: throughput = work-in-process ÷ residence time.
Operating income is then affine in `R`:

```
OI = R·(1 − commission − COGS% − R&D% − G&A%) − T·(loaded salary + travel) − overhead − marketing
```

which is why small changes in the throughput levers produce outsized changes in margin.

## Quick start

```bash
pip install -e ".[dev]"
pytest
python -m smem.workbook out/SMEM.xlsx   # build the corrected workbook
```

```python
from smem import ModelInputs, Levers, impact

base = ModelInputs()  # the workbook's fictitious company
i = impact(base, Levers(cycle_time_reduction=0.10))
print(f"{i.revenue_growth_pct:.1%}")  # 11.1%  (1/0.9 − 1, not 10%)
print(f"{i.operating_income_growth_pct:.1%}")
```

## Repository layout

```
src/smem/
  inputs.py      validated input schema (pydantic) — mirrors sheet "1) Data entry"
  engine.py      pure functions: rep economics, levers, income statement, impact
  scenarios.py   the six scenario columns of sheet "2) Performance breakdown"
  legacy.py      cell-exact reproduction of the ORIGINAL workbook, defects included
  diagnostics.py the 15 qualitative obstacles (data/diagnostics.json)
  workbook.py    generates the corrected .xlsx (live formulas over named ranges) + verifier
tests/           engine behaviour + cell-for-cell regression against the shipped .xls
docs/            model_teardown.md — full analysis of the original and its defects
reference/       the original .xls, a converted .xlsx, and a full cell dump
```

## Phases

| phase | deliverable | status |
|---|---|---|
| 1 | Teardown + reference engine + regression against original | ✅ |
| 2 | Corrected `.xlsx` generated from the engine, verified cell-for-cell after recalculation | ✅ |
| 3 | Web calculator (API + embeddable widget) with AI analytics | ⏳ |
| 4 | Benchmark store: submissions, segments, percentiles | ⏳ |

## Engineering standards

- Python ≥ 3.11, `src/` layout, pydantic v2 for all boundaries, frozen models.
- `ruff` (lint + format), `mypy --strict`, `pytest` — all must be green before merge.
- The engine has **no I/O and no framework imports**; everything else consumes it.
- Every defect found in the original is (a) documented, (b) reproduced in `legacy.py`,
  and (c) covered by a test that proves the corrected engine behaves differently.
