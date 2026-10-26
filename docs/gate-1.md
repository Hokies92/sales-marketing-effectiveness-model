# Gate 1 — Modern replication of the current model

**Question Gate 1 answers:** can the 2011 workbook's purpose and functionality be replicated,
with twenty years of XLS tech debt removed, in a form that is modern, better to use, exportable,
web-publishable and Python-driven — *without sacrificing its outputs?*

**Acceptance:** the owner signs off each criterion below against the delivered artefacts, not
against test output alone. Partial credit is recorded in the status table; the gate opens only
when every **Required** row is accepted.

## 1. Scope

In scope: everything the original does (five tabs: orientation, data entry, performance
breakdown, impact analysis, scenario diagnostic), rebuilt. Plus the specific modernisations
listed in §2. The corrected behaviours Q1–Q3 are in scope because they are *defects*, not
features; everything else behaves as the original unless a row below says otherwise.

Out of scope until Gate 1 is accepted: benchmarking, AI narrative, CRM/GL ingestion, cohort
simulation, databases, multi-year horizons beyond the two already in the engine.

## 2. Criteria

| # | Criterion | Required | Evidence of done | Status |
|---|---|---|---|---|
| **A. Fidelity** | | | | |
| A1 | Original reproduced cell-for-cell, defects included | ✅ | `legacy.py` + `test_legacy_reproduction.py` | ✅ done |
| A2 | Corrected engine matches original wherever the original was right; Q1–Q3 fixed and proven | ✅ | `test_engine.py`, `docs/model_teardown.md` | ✅ done |
| A3 | Every output of the five original tabs exists in the new workbook with the same meaning | ✅ | mapping table in `docs/canonical.md` §5 | ⏳ V1 covers tabs 1–4; orientation + diagnostics text parity to confirm |
| **B. Modern Excel, same outputs** | | | | |
| B1 | Every input a named range; every output a live formula over names; zero hard-coded results | ✅ | `test_workbook.py::test_every_formula_uses_names_not_literals` | ✅ done (V1) |
| B2 | Recalculated workbook equals the engine on every output cell, at defaults and at alternate inputs | ✅ | `test_recalculated_workbook_matches_engine` | ✅ done (V1, 197 cells) |
| B3 | Excel Tables, data validation (ranges, dropdowns), structured input blocks, conditional-format warnings (e.g. deal-size gap, demand-bound) | ✅ | visual review + builder tests | ⏳ |
| B4 | Input provenance visible in the sheet (source tag per input; defaults flagged) | ✅ | Inputs sheet column + legend | ⏳ |
| B5 | Formula transparency: an "Explain" sheet or cell notes that state each formula in words with its named inputs | ✅ | review | ⏳ (V1 has comments on key cells) |
| B6 | Print/screen layout, fonts, colour conventions (blue inputs, black formulas, green links), no gridlines, frozen panes, fit-to-width | ✅ | PDF render in CI artefact | ✅ done (V1) |
| **C. Scenario work** | | | | |
| C1 | The six original scenario columns with editable improvement % | ✅ | V1 Scenarios sheet | ✅ done |
| C2 | Named, user-built scenarios (≥ 6 slots) combining any levers incl. capacity P, with per-scenario cost, delay and horizon | ✅ | V2 Scenario Builder sheet verified against engine v2 | ⏳ |
| C3 | Side-by-side comparison with OI bridge (waterfall) and break-even budget per scenario | ✅ | V2 Compare sheet + chart | ⏳ |
| C4 | Year-one vs steady-state toggle; demand-bound indicator | ✅ | policy cells + conditional format | ⏳ |
| **D. Macros and workflow aids** | | | | |
| D1 | Macro-free core: everything above works in `.xlsx` with macros disabled | ✅ | CI builds `.xlsx` | ✅ (V1) |
| D2 | Optional `.xlsm` layer: buttons for *Reset to defaults*, *Snapshot scenario*, *Export*, *Trace this cell* (formula walk-through) | ◻ nice-to-have | VBA template under `excel/vba/`, manual test script | ⏳ |
| D3 | Guided entry: a step-through on the Inputs sheet (Office Scripts or VBA) that highlights the next required cell and its description | ◻ | manual test script | ⏳ |
| **E. Export** | | | | |
| E1 | One-command export of baseline + every scenario as tidy CSV/JSON (long format, one row per metric per scenario) for Power BI / Tableau / pandas | ✅ | `smem.export` + tests | ⏳ |
| E2 | Export sheet inside the workbook mirroring E1 (so Excel users can connect a BI tool directly) | ✅ | V2 Export sheet | ⏳ |
| **F. Web publish** | | | | |
| F1 | A hosted data-entry page that captures the Inputs with validation and provenance tags, **without exposing formulas or the full model** | ✅ | FastAPI `POST /evaluate` + static entry page; engine stays server-side | ⏳ |
| F2 | A custom-output page: the six scenarios, bridge and break-even for the entered data, shareable by link, no model internals | ✅ | `GET /result/{id}` rendering | ⏳ |
| F3 | Round-trip: web inputs download as the Excel workbook pre-filled; workbook inputs upload to the web | ✅ | `smem.workbook` from a `Baseline`; reader for the Inputs sheet | ⏳ |
| **G. Python where appropriate** | | | | |
| G1 | Engine, builder, verifier, exporter and API are Python; the workbook contains no Python dependency at runtime | ✅ | repo structure | ✅ done |
| G2 | CLI: `smem build`, `smem verify`, `smem export`, `smem serve` | ✅ | `src/smem/cli.py` + tests | ⏳ |
| **H. Quality** | | | | |
| H1 | CI green on 3.11–3.13; ≥ 95 % coverage; ruff + mypy strict | ✅ | `.github/workflows/ci.yml` | ✅ done |
| H2 | Owner walkthrough recorded: open the workbook cold, enter a company, build a scenario, read the bridge, export, publish — no instructions needed beyond the Read-me tab | ✅ | sign-off note in this file | ⏳ |

## 3. Definition of "doesn't sacrifice its outputs"

For every input set, the new workbook's baseline and six-scenario outputs equal the corrected
engine to the cent, and the corrected engine equals the original workbook everywhere except the
documented defects. Where the new workbook *adds* outputs (bridge, break-even, demand-bound),
those are additions, never substitutions.

## 4. Order of work

1. **3b — Excel V2** (B3–B5, C2–C4, E2): generated by `smem.workbook` from engine v2, verified
   after recalculation like V1. V1 remains in the repo as the faithful-but-corrected original.
2. **Export + CLI** (E1, G2).
3. **Web entry + output** (F1–F3): FastAPI over the engine, two static pages, no JavaScript
   re-implementation of any formula.
4. **Macro layer** (D2–D3) last, because it cannot be verified in CI.
5. **Owner walkthrough** (H2) and gate review.

## 5. Sign-off

| Criterion group | Accepted by | Date | Note |
|---|---|---|---|
| A | | | |
| B | | | |
| C | | | |
| D | | | |
| E | | | |
| F | | | |
| G | | | |
| H | | | |
