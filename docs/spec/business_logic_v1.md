# Business Logic & Scenario Architecture Specification — V1

**Status:** implemented in `smem` engine v2 (`assumptions`, `operating`, `scenario`, `finance`, `compare`); enforced by `tests/test_engine_v2.py`.
**Purpose:** the shared contract between the Excel model, the web engine and any later analytics or benchmarking. Excel and web both *render* this logic; neither defines it.

This spec adopts the October 2026 reassessment's framing: the product is an **assumption-driven commercial and financial scenario simulator**. Its core question is *"what if we changed how the business operates, alone or in combination — and what are the complete economic consequences?"* Every capability below exists to improve one of four things: scenario realism, financial integrity, fairness of comparison, or decision quality.

---

## 1. Vocabulary

| term | definition | code |
|---|---|---|
| **Baseline** | A complete set of inputs + per-input provenance + an operating policy. Immutable. | `assumptions.Baseline` |
| **Provenance** | The source of one input: `default` < `derived` < `assumption` < `actual`. | `assumptions.Source` |
| **Policy** | Behavioural rules the original left implicit: ramp curve, horizon, demand limit, draw for ramping hires, manager span. | `assumptions.OperatingPolicy` |
| **Lever** | One of six dimensions a scenario can move: territories, capacity, close rate, cycle time, deal size, demand. | `scenario.Lever` |
| **Intervention** | A deliberate change: a lever set + annual cost + one-time cost + months to benefit + success probability. | `scenario.Intervention` |
| **Scenario** | A named bundle of interventions. Inherits everything from the baseline except what it changes. | `scenario.Scenario` |
| **Horizon** | `year_one` (ramp, time-to-benefit and one-time costs apply) or `steady_state`. | `assumptions.Horizon` |
| **Outcome** | Income statement for one scenario at one horizon, built from typed cost lines. | `finance.Outcome` |
| **Bridge** | Waterfall from baseline OI to scenario OI with zero residual. | `finance.Bridge` |

## 2. Assumption engine

**Principle: assumptions do not need to equal actuals, but the model must always know which it is using.**

- Every leaf input has a dotted path (`mechanics.close_rate`) and a `Provenance`.
- `Baseline.from_defaults()` tags everything `default` (the shipped fictitious company).
- `with_value(path, value, source, note)` returns a *new* baseline; it re-validates the whole input tree so range constraints still apply.
- Precedence is **advisory**: a user may knowingly set an `assumption` over an available `actual` (to test a hypothetical). `overrides_actuals()` lists where that has happened; `discrepancies()` quantifies the gap.
- V1 derivation: `avg_revenue_per_transaction` vs `revenue_from_contracts ÷ contracts_last_year`. (The original collected the latter and ignored it — defect Q3.)

## 3. Commercial operating engine

Throughput identity, with three quantities the original conflated now separated:

```
capacity_opportunities = N · (12 · P / C)
realised_opportunities = min(capacity_opportunities, qualified_demand)      # demand may be None
deals                  = realised_opportunities · w
revenue                = deals · A
```

| symbol | meaning | how it moves |
|---|---|---|
| `T` territories | coverage units | `territory_change` |
| employed sellers | filled seats; **incur cost** | scale with `T` (vacancies preserved proportionally) |
| `N` productive equivalents | **generate throughput** | existing + new hires × ramp fraction |
| `P` concurrent opportunities per seller | attention-bounded capacity | `capacity_change` — first-class lever |
| `C` cycle months | turnover speed | `cycle_time_reduction` (positive = shorter) |
| `w` close rate | conversion | `close_rate_change`, capped at 1.0 |
| `A` deal size | monetisation | `deal_size_change` |
| `D` qualified demand / yr | optional ceiling | `demand_change`; `None` → never binding |

**Ramp** (`ramp_fraction`): share of year one a hire is productive.
`step`: `(12 − r)/12` (the original's convention). `linear`: `1 − r/24`. Steady state: 1.
Removed seats remove full capacity immediately. **The same ramp rule applies in every scenario** (fixes defect Q2).

**Outputs** also expose `utilisation` and `demand_bound`, so the UI can say *why* a lever did nothing.

## 4. Financial engine and true-up

Income statement lines are typed by cost behaviour:

| line | kind | driver |
|---|---|---|
| cost of revenue, R&D, G&A | variable | revenue × ratio |
| commission | variable | **realised revenue** × rate |
| draw for ramping hires | fixed per seller | unproductive seller-years × policy draw |
| seller salary + travel | fixed per seller | employed sellers × (loaded salary + travel) |
| incremental managers | step-fixed | `ceil(sellers/span) − ceil(base/span)` × manager cost |
| sales overhead, marketing | fixed | constant |
| improvement programmes | discretionary | Σ intervention costs at the horizon |

Integrity rules, enforced in code (`Outcome.check`, `Bridge.check`):

1. **Accounting:** `revenue − Σ costs − operating_income = 0`.
2. **Bridge:** `OI_scenario − OI_baseline − Σ steps = 0`. Steps are the revenue delta plus one bar per cost line that changed.
3. **Causal:** commission follows realised revenue, so a hire who sells nothing earns no commission. (The original charged full commission to zero-revenue hires; year-one hiring was therefore ~$0.9M worse than it should have been.) A guaranteed draw is an explicit policy, not an accident.

Bookings = revenue in V1. The architecture leaves room to separate bookings, recognised revenue and cash later; it does not permanently equate them.

## 5. Scenario engine

- Lever changes **compose multiplicatively**: `(1+a)(1+b) − 1`; cycle: `1 − (1−a)(1−b)`.
- Year one credits `(12 − months_to_benefit)/12` of an intervention's change; steady state credits all of it.
- One-time costs hit year one only; annual costs hit every horizon.
- `combine(name, scenarios)` merges interventions; `with_intervention` adds one. Scenarios are frozen, so comparisons are reproducible.

## 6. Comparison and decision support

| mode | question | function | note |
|---|---|---|---|
| Equal percentage | what if each lever improves 10%? | `equal_percentage` | entry point; shows that cycle is hyperbolic (`1/0.9 − 1 = 11.1%`), a property of the formula, not evidence |
| Interaction | how much do combined levers earn beyond the sum of parts? | `interaction_effect` | +$3.75M revenue at defaults for close+cycle+deal; negative values reveal binding constraints |
| **Break-even investment** | how much can we spend on strategy A before strategy B is better? | `break_even_investment` | **steady state identity:** improve-vs-hire headroom = `ΔT × (loaded salary + travel)` = $1,643,500 at defaults; year one adds the ramp penalty ($7.6M) |
| Equal investment | what does $X buy on each lever? | `equal_investment` + `CostToImprove` | difficulty is *not* a score; it is `cost per point`, `max_change`, `months_to_benefit`, `success_probability` |
| Goal seek | how far must a lever move to add $Y of OI? | `goal_seek` | bisection; returns `None` when unattainable (e.g. hiring in year one under a 12-month ramp) |
| Risk-adjusted | expected value when the programme may fail | `risk_adjusted_delta` | `p·ΔOI(success) + (1−p)·ΔOI(failure)`; failure still pays the programme |
| Sensitivity | OI across a grid of one lever | `sensitivity` | |

## 7. What the original proves, restated precisely

> Gains in existing-resource productivity produce superior operating leverage **when they are achievable at lower incremental cost, and faster, than expanding capacity.**

The engine makes that conditional testable: the break-even budget is the price at which the proposition stops being true for a given company.

## 8. Test matrix (all implemented)

| test | expectation | status |
|---|---|---|
| Baseline identity | empty scenario reproduces baseline; v2 baseline = v1 baseline = original (after Q1 fix) | ✅ |
| Scenario isolation | scenarios and baselines are frozen; `with_*` never mutates | ✅ |
| Financial reconciliation | zero residual for every scenario × horizon | ✅ |
| Ramp consistency | same ramp in hire-only and combined; step and linear policies | ✅ |
| Cost integrity | each line follows its kind; no commission without revenue; draw only on unproductive years; step managers | ✅ |
| Input validation | ranges, unknown paths, impossible levers rejected | ✅ |
| Dependency integrity | derived values follow sources; discrepancies detected and cleared | ✅ |
| Constraint enforcement | demand cap, close-rate cap, hiring worthless when demand-bound | ✅ |
| Interaction | multiplicative identity; lever composition | ✅ |
| Legacy parity | `legacy.py` reproduces the shipped .xls cell-for-cell, defects included | ✅ |
| Cross-platform parity | Excel V1 ↔ engine v1 (197 cells, after recalculation) | ✅ — Excel V2 ↔ engine v2 pending |

## 9. Open decisions carried forward (with current defaults)

| decision | V1 default |
|---|---|
| Baseline = history or hypothetical capacity? | Both: provenance tags say which |
| Is capacity demand-constrained? | Optional (`qualified_demand_per_year = None`) |
| Are lever changes independent? | Yes, composed multiplicatively, until interaction rules are specified |
| Financial period | Annual; two horizons; period-aware engine deferred |
| ROI definition | *Not* revenue ÷ spend. V2 reports ΔOI, break-even budget and risk-adjusted ΔOI; a formal return-on-incremental-investment metric follows once investment is on every scenario |
| Benchmarks required to run? | No |
| Legacy behaviour | Reproduced in `legacy.py`; corrected logic is the default everywhere else |
| IP provenance | Workbook carries a 2011 Forrester notice over a 2002 original; establish before external publication |

## 10. What this spec deliberately excludes from V1

Monthly cohort simulation · CRM integration · detailed compensation plans · Monte Carlo · AI recommendations · external benchmark databases · three-statement reconciliation. Each is admitted later only if it passes the four-way test in the preamble.
