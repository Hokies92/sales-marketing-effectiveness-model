# Model Teardown — Sales & Marketing Efficiency Modeling Tool (Forrester, 2011)

Source: `reference/original/Sales_and_Marketing_Effectiveness_Model_-_update.xls`
(created 2002-03-02 by Scott Santucci, last saved 2012-05-15). Five sheets, 206 formulas,
no named ranges, no VBA.

This document records (1) what the model *is*, structurally; (2) every input and formula;
(3) the defects found; (4) the design decisions carried into the rebuild.

---

## 1. What the model is

Strip away the layout and the workbook is a **single-stage throughput system** with a
linear cost overlay. One rep is a server holding `P` units of work-in-process (open
opportunities), each unit residing for `C` months. By Little's Law the rep's annual
opportunity throughput is `λ = 12·P / C`. A fraction `w` of those convert, each worth `A`.
Multiply by `T` reps:

```
R  =  T · (12·P / C) · w · A                       … revenue engine identity
```

The four "business scenarios" of the original are exactly the four free variables of that
identity other than `P` (`T`, `w`, `C`, `A`). `P` — concurrent capacity, i.e. *selling
time* — is the fifth lever the orientation text talks about at length but the scenario
sheet never varies. Leads are deliberately absent (the orientation says so): the model
assumes the pipeline is always full, so lead supply is never the binding constraint.

Costs are an affine overlay:

```
RepCost      = T · (S·(1+ℓ) + Travel)  +  c·R            fixed per head + commission on revenue
OpIncome     = R·(1 − c − g_cogs − g_rd − g_ga)  −  T·(S·(1+ℓ)+Travel)  −  OH  −  M
```

So operating income is a straight line in `R` with slope `(1 − c − Σg) ≈ 0.53` and a large
fixed intercept. That is the entire mechanism behind the model's thesis that small
throughput gains produce large margin gains: **operating leverage on a fixed sales
headcount**.

### Geometric consequences worth keeping in the rebuild

| lever | elasticity of R | 10% move → ΔR |
|---|---|---|
| `T`, `w`, `A` | +1 (linear) | +10.0% |
| `C` | −1 (hyperbolic) | +11.1% (`1/0.9 − 1`) |

The original's claim that cycle time is "the single greatest impact you can have" is
true in the model for a purely geometric reason — `1/C` is convex — not an empirical one.
Equal-percentage improvements are not equal-effort improvements; the rebuild should let
users compare levers at *equal cost* or *equal difficulty*, not only equal percentage.

---

## 2. Sheet-by-sheet

### 2.1 `Orientation`
Narrative only. Contains a stale worked example ("10% decrease in sales force + 10%
larger orders → +7% revenue, ~+800% operating margin") that does not correspond to the
current defaults — a remnant of the 2002 edition.

### 2.2 `1) Data entry` — inputs

| cell | input | default | engine field |
|---|---|---|---|
| F9 | territories | 100 | `territories` |
| F11 | avg revenue / transaction | **75,000 (hard-coded)** | `avg_revenue_per_transaction` |
| E12 | contracts last year | 755 | `contracts_last_year` (informational) |
| E13 | revenue from those contracts | 25,000,000 | `revenue_from_contracts` (informational) |
| E16 | salary per rep | 95,000 | `compensation.base_salary` |
| E17 | load rate | 23% | `compensation.load_rate` |
| F15 | fully loaded salary | `=E16+E16*E17` = 116,850 | `fully_loaded_salary` |
| E20–E26 | travel components | 750/200/100/250/2/250/25 | `travel.*` |
| F19 | travel / rep / yr | `=((E20+E21+E25)+E24*(E22+E23))*E26` = 47,500 | `travel.annual_cost` |
| F28 | commission | 8% | `compensation.commission_rate` |
| F31 | concurrent opportunities | 30 | `mechanics.concurrent_opportunities` |
| F33 | cycle (months) | 6 | `mechanics.cycle_months` |
| F35 | ramp (months) | 12 | `mechanics.ramp_months` |
| F37 | close rate | 25% | `mechanics.close_rate` |
| E42–E46 | sales overhead lines | Σ = 10,800,000 | `overhead.*` |
| E49–E56 | marketing lines | Σ = 3,700,000 | `marketing.*` |
| F39 | total S&M overhead | `=F41+F48` = 14,500,000 | `total_sales_and_marketing_overhead` |

### 2.3 `2) Performance breakdown` — the engine

Columns: C baseline · E hire · F close · G cycle · H deal · J close+deal+cycle · K all.
Row 7 holds the improvement % per lever (all 10%).

| row | quantity | baseline formula | notes |
|---|---|---|---|
| 9 | territories | `=Data!F9`; E: `=C9*(1+E7)` | |
| 10 | avg revenue / txn | `=Data!F11`; H: `=G10*(1+H7)` | |
| 11 | loaded salary | **87,750 literal** in C,F,G,H,J | defect Q1 |
| 12 | travel | `=Data!F19` | fixed per rep |
| 13 | commission | `=row23 * Data!F28` | on rep revenue |
| 14 | cost per rep | `=SUM(11:13)` | |
| 16 | capacity P | `=Data!F31` | never varied |
| 17 | cycle C | `=Data!F33`; G: `=C17*(1−G7)` | |
| 18 | ramp | `=Data!F35` | only used in rows 25 E/K |
| 19 | close w | `=Data!F37`; F: `=C19*(1+F7)` | |
| 21 | opps / yr | `=(12/C17)*C16` | Little's Law |
| 22 | deals / yr | `=C21*C19` | E22 is `=C22` (harmless) |
| 23 | revenue / rep | `=C22*C10` | |
| 25 | revenue | `=C23*C9`; E: `=((12−E18)/12·E23)·(E9−C9)+C25`; K: see Q2 | |
| 26 | rep costs | `=C14*C9` | |

### 2.4 `3) Impact Analysis` — income statement

| row | quantity | formula |
|---|---|---|
| 8 | revenue | `=Perf!row25` |
| 9 | Δ revenue | `=row8 − Perf!$C$25` (also a stray I9) |
| 12 | Δ rep costs | `=Perf!row26 − Perf!$C$26` |
| 13 | total sales costs | `=Perf!row26 + Data!$F$41` |
| 14 | marketing | `=Data!$F$48` (constant across scenarios) |
| 15 / 20 | S&M | `=13+14` |
| 18, 19, 21 | COGS, R&D, G&A | `=row8 × C30/C31/C32` (13.22% / 10.19% / 15.4%) |
| 22 | opex | `=SUM(18:21)` |
| 23 | operating income | `=8 − 22` |
| 26 | "% net gain" | `=(Δrev − Δrep cost) / base revenue` |
| 27 | "S&M ROI" | `=(revenue − S&M) / S&M` — a revenue/spend ratio, not profit ROI |

### 2.5 `4) Scenario Diagnostic`
Fifteen qualitative obstacles (5 × close / cycle / deal size). No formulas. Content is
valuable and should become structured data (`diagnostics.yaml`) in Phase 3 so the AI
layer can cite it.

---

## 3. Defects found

Severity reflects effect on the numbers a user would act on.

| id | sev | where | defect | effect at defaults |
|---|---|---|---|---|
| **Q1** | high | Perf!C11,F11,G11,H11,J11 | Loaded salary is a literal `87,750` (= 75,000 × 1.17, an earlier edition's values) instead of `=Data!F15` (116,850). | Rep costs understated by **$29,100/rep → $2.91M**; baseline operating income overstated 10%; S&M "ROI" 204% vs 182%. |
| **Q2** | high | Perf!K25 | `=(K23*K9) − ((12−E18)/12·E23·(E9−C9))`. Subtracts the *productive* share at *baseline* rev/rep. Correct: `K23·C9 + K23·(E9−C9)·(12−E18)/12`. With ramp = 12 the subtraction is 0, so new hires are credited a full year of *improved* revenue. | "Improve all" revenue overstated by **$15.1M**, operating income by **$12.5M**; net gain 42.9% shown vs 29.2% true. **Reverses the ranking**: corrected, "Improve all" (+61% OI) is *worse* than "close+deal+cycle" (+71%). |
| Q3 | med | Data!F11 vs E12:E13 | Avg deal size is typed (75,000) while contracts/revenue (755 / $25M → $33,113) are collected and ignored. Two inconsistent sources of truth on the same screen. | Users who fill in their real contracts/revenue get no effect. |
| Q4 | low | Impact!I9, Perf!I7 | Formulas left in the spacer column (I9 = −112.5M). | Cosmetic. |
| Q5 | low | Perf!E22 | `=C22` instead of `=E21*E19`. | None at present; breaks if hire scenario ever changes mechanics. |
| Q6 | low | Perf!K14, K21–K23 | `=J14` etc. instead of recomputing from K's own inputs. | None at present; fragile. |
| Q7 | design | Orientation!B5 | Worked example is from a different parameter set. | Misleading copy. |

Modelling assumptions that are *not* defects but must be made explicit in the UI:

- Travel is fixed per rep; it does not scale with opportunities or trips implied by `P`, `C`.
- Overhead and marketing are constant across all scenarios, including +10% headcount.
- COGS, R&D, G&A are fully variable with revenue (industry-average ratios).
- Ramp is a step function: zero output for `ramp` months, full output after.
- Hire scenario is a **year-one view**; a multi-year view would show the hires paying back.
- "% net gain" ignores COGS/R&D/G&A, so it is a contribution-style metric, not margin.

---

## 4. Decisions carried into the rebuild

1. **One engine, many renderers.** `smem.engine` is the only place the math lives. The
   workbook (Phase 2) and the web tool (Phase 3) are generated from / call it.
2. **Legacy is preserved, not deleted.** `smem.legacy` reproduces the shipped workbook to
   the cent, defects included, and is pinned by `tests/test_legacy_reproduction.py`. Any
   future change that silently alters our understanding of the original will fail CI.
3. **Ramp is applied consistently.** Added territories earn `(12 − ramp)/12` of a rep-year
   at the *scenario's* revenue per rep; removed territories simply vanish; costs are
   always full.
4. **Both deal-size sources are kept.** `avg_revenue_per_transaction` drives the model;
   `implied_avg_revenue_per_transaction` is surfaced so the UI can warn when they diverge.
5. **`P` becomes a first-class lever** in Phase 3 (selling-time / capacity scenario).
6. **Metric names are kept but documented** (`sales_and_marketing_roi` is revenue ÷ spend).

## 5. Corrected baseline (defaults)

| | legacy | corrected |
|---|---|---|
| revenue | 112,500,000 | 112,500,000 |
| rep costs | 22,525,000 | 25,435,000 |
| operating income | 31,813,750 | 28,903,750 |
| operating margin | 28.3% | 25.7% |

| scenario (10% each) | ΔR | ΔOI (corrected) | margin |
|---|---|---|---|
| hire | 0.0% | −8.8% | 23.4% |
| close rate | +10.0% | +20.7% | 28.2% |
| cycle time | +11.1% | +23.0% | 28.4% |
| deal size | +10.0% | +20.7% | 28.2% |
| close + deal + cycle | +34.4% | +71.3% | 32.7% |
| all four | +34.4% | +61.4% | 30.9% |
