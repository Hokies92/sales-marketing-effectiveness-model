# Canonical Foundation

What is fixed, what is the source of truth for each thing, and the numbers that anchor
regression. Change anything here only by ADR (`docs/decisions/`) in the same PR.

## 1. Sources of truth, by concern

| Concern | Source of truth | Everything else is |
|---|---|---|
| What the original did | `reference/original/*.xls` (read-only) and `src/smem/legacy.py` | commentary |
| What the model *should* do | `docs/spec/business_logic_v1.md` | implementation of it |
| The calculation | `src/smem/` — engine v1 (`inputs`, `engine`, `scenarios`) and engine v2 (`assumptions`, `operating`, `scenario`, `finance`, `compare`) | a renderer: workbook, web, export |
| Input definitions and how to collect them | the Data Entry Guide (`docs/data-entry-guide.md`, mirrored from the live doc) | |
| Defects of the original | `docs/model_teardown.md` §3 (ids Q1–Q7) | |
| The qualitative diagnostics | `src/smem/data/diagnostics.json` | |
| Project rules | `CLAUDE.md`, `CONTRIBUTING.md`, this file | |

## 2. The model, canonically

Revenue identity (per baseline, per scenario, per horizon):

```
capacity_opportunities = N · (12 · P / C)
realised_opportunities = min(capacity_opportunities, D)        D = None → never binding
deals                  = realised_opportunities · w
R                      = deals · A
```

| symbol | name | definition |
|---|---|---|
| `T` | territories | coverage units, staffed or not |
| employed | employed sellers | filled quota-carrying seats; **drive cost** |
| `N` | productive seller-equivalents | fully ramped sellers + ramping sellers × ramp fraction; **drive revenue** |
| `P` | concurrent opportunities | qualified opportunities one seller holds at once (attention-bounded capacity) |
| `C` | cycle months | qualified-opportunity creation → closed-won, same population as `w` |
| `w` | close rate | closed-won ÷ (closed-won + closed-lost), capped at 1.0 |
| `A` | average deal size | revenue per executed agreement |
| `D` | qualified demand per year | optional ceiling |

Operating income:

```
OI = R − R·(cogs% + rd% + ga% + commission%) − employed·(loaded_salary + travel)
       − draw·unproductive_seller_years − step_managers − sales_overhead − marketing − programmes
```

Ramp fraction (year one): step `(12 − r)/12`; linear `1 − r/24`; steady state `1`.
Removed seats remove full capacity at once. Commission follows realised revenue only.

Integrity rules enforced in code: `revenue − Σcosts − OI = 0`; `ΔOI − Σ bridge steps = 0`.

## 3. Vocabulary (use these words, in code and in sheets)

| say | not |
|---|---|
| scenario | what-if column, case |
| lever | driver, dial |
| intervention | initiative, program (in code) |
| baseline | base case, current state |
| provenance / source tag | data quality flag |
| break-even investment | ROI threshold |
| operating income | EBIT, profit |
| sales & marketing (S&M) | SG&A (that includes G&A) |
| year one / steady state | short / long term |

Metric names are preserved from the original where kept (`net_gain_pct`, `sales_and_marketing_roi`)
and documented as what they compute; new metrics are never given a misleading legacy name.

## 4. Golden numbers (defaults = the shipped fictitious company)

| quantity | value | pinned by |
|---|---|---|
| Baseline revenue | 112,500,000 | legacy, v1, v2 |
| Baseline operating income (original, with Q1) | 31,813,750 | legacy |
| Baseline operating income (corrected) | 28,903,750 | v1, v2 |
| Loaded salary | 116,850 (legacy sheet used 87,750) | inputs, legacy |
| Travel per rep | 47,500 | inputs |
| Rep opportunities / deals / revenue per year | 60 / 15 / 1,125,000 | v1, v2 |
| "Improve all" revenue — original / corrected | 166,375,000 / 151,250,000 | legacy, v1 |
| Three-lever interaction effect on revenue | +3,750,000 | v2 |
| Break-even improvement budget, steady state (close +10% vs hire +10%) | 1,643,500 = 10 × (116,850 + 47,500) | v2 |
| Same, year one, step ramp 12 months | 7,627,375 | v2 |
| Hire +10%, year one ΔOI — v1 (commission on hires) / v2 (none) | −2,543,500 / −1,643,500 | v1, v2 |

## 5. Original-tab → new-artefact mapping (Gate 1 A3)

| Original tab | Content | New home |
|---|---|---|
| Orientation | purpose, sections, caveats, stale worked example | Read-me sheet (rewritten; example recomputed) |
| 1) Data entry | 34 inputs with descriptions | Inputs sheet (named ranges, provenance column) + Data Entry Guide |
| 2) Performance breakdown | per-rep economics, six scenario columns | Scenarios sheet (V1) · Scenario Builder (V2) |
| 3) Impact Analysis | income statement, net gain, S&M ratio, assumption ratios | Impact sheet (+ margin, ΔOI, growth; V2 adds bridge, break-even) |
| 4) Scenario Diagnostic | 15 obstacles | Diagnostics sheet, from `diagnostics.json` |

## 6. Excel formula policy

- The **computed core** (every number that also exists in the engine) uses only functions
  LibreOffice evaluates: arithmetic, `SUM`, `MIN`, `MAX`, `IF`, `IFERROR`, `INDEX`, `MATCH`,
  `SUMPRODUCT`, `CEILING`, named ranges. This is what lets CI recalculate and verify.
- **Usability features** may use anything Excel offers (Tables, data validation, conditional
  formatting, slicers, form controls, Office Scripts, VBA) provided removing them changes no
  computed value. `LAMBDA`, `LET`, dynamic arrays and `XLOOKUP` are therefore allowed only in
  presentation cells, never in the core.
- Macros live in `.xlsm` variants built from a template under `excel/vba/`, are optional, and are
  covered by a written manual test script because CI cannot run them.

## 7. Decision log (ADRs)

ADRs go in `docs/decisions/NNNN-title.md` (context, decision, consequences). Seeded:

- 0001 — Engine is the single source of truth; artefacts are generated and verified.
- 0002 — Keep V1 workbook alongside V2 (V1 = faithful-but-corrected original).
- 0003 — Commission follows realised revenue; draw is an explicit policy.
- 0004 — Computed core restricted to LibreOffice-evaluable formulas.
