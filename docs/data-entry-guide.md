# SMEM Data Entry Guide

Mirror of the live guide (claude.ai doc "SMEM Data Entry Guide", 2026-10-24). The live doc is
where edits happen; this copy is what the Inputs sheet and the web entry page are built from.

## Purpose

Thirty-four fields feed the model; nine decide 90 % of the result (territories, employed
sellers, deal size, loaded salary, travel, commission, capacity, cycle, close rate). Every entry
carries one of four source tags:

| Tag | Meaning |
|---|---|
| Actual | observed in a system of record |
| Derived | calculated from other entries |
| Assumption | a deliberate estimate or hypothetical |
| Default | the shipped illustrative value, untouched |

A default that looks like an actual is the most expensive mistake the form allows.

## How the data flows

Yellow **Entry** cells → **Metric** column → engine. Only the Metric column is read downstream:
seven cells into the throughput engine, two into the income statement. Four metrics are roll-ups
(loaded salary, travel, sales overhead, marketing). In the original, contracts and revenue were
entered and never read, loaded salary never arrived (Q1), and improvement % and the
COGS/R&D/G&A ratios lived on other tabs.

## Territories, filled seats and productive sellers

| Field | Definition | Drives | Source |
|---|---|---|---|
| Territories (T) | coverage units you intend to staff, filled or not | coverage ratio, vacancy count | territory plan |
| Employed sellers | quota-carrying seats filled at the as-of date | **cost** | HRIS |
| Sellers in ramp | employed with tenure under the ramp period | reduces productive equivalents | HRIS hire dates |

Productive equivalents N = ramped + ramping × ramp fraction; revenue follows N, cost follows
employed. Vacancies earn and cost nothing in engine V1; record any vacancy yield as a tagged
assumption. Checks: employed ≤ territories; if employed = territories exactly, confirm it.

## Field-by-field (abridged; GL = statement line to reconcile to)

**Sales force** — territories (plan; Actual) · employed sellers (HRIS; Actual) · sellers in ramp
(Derived) · avg revenue per transaction = recognised revenue ÷ closed contracts, new business
(Derived/Assumption) · contracts last year (CRM) · revenue from those contracts (GL revenue).

**Rep compensation** — base salary, quota carriers only (S&M salaries) · load rate = payroll
taxes + benefits + bonus accrual ÷ base, **no facilities or overhead allocation** · commission
rate = commission paid ÷ quota-carrier revenue (S&M commissions; see ASC 340-40) · draw for
ramping hires.

**Travel** — transport, ground, meals/day, lodging/night, days/trip, entertainment/trip,
trips/year (S&M travel; entertainment kept separate for tax). If total quota-carrier T&E is
known, enter it ÷ employed sellers and tag trip fields Derived.

**Sales mechanics** — P: open qualified opportunities per seller, median (CRM) · C:
created→closed-won months, median, qualified only · ramp: months to first full-quota quarter ·
w: won ÷ (won + lost), same population as C · qualified demand per year (optional).
P, C and w must describe the same opportunity population.

**Sales overhead** — non-quota manager salaries · SEs/support (billable SE time is Cost of
revenue) · sales ops & admin · training (incl. training travel) · non-quota incentives.

**Marketing** — personnel · website (P&L expense, not capitalised spend, ASC 350-50) · events ·
advertising (ASC 720-35) · direct mail · telemarketing/lead gen · branding & PR (ASC 350-30) ·
collateral.

**Ratios** — cost of revenue %, R&D %, G&A % from the same fiscal year's functional income
statement; G&A must not already contain overhead loaded into salary.

## Chart-of-accounts and GAAP/IFRS assessment

The sheet is a by-function income statement (Reg S-X Rule 5-03; IAS 1 function-of-expense) —
the right skeleton — and follows none of the recognition rules. Entry rules per area:

| Area | Standard | Entry rule |
|---|---|---|
| Loaded salary | overhead already in G&A | load = taxes + benefits + bonus accrual only |
| Commission | ASC 340-40 / IFRS 15 capitalise contract costs > 1 yr | enter commission *paid*; label paid-basis |
| Revenue from contracts | ASC 606 / IFRS 15 bookings ≠ revenue | enter recognised revenue; TCV separately |
| Website, branding | ASC 350-50 / 350-30 / IAS 38 | enter P&L expense |
| Sales engineers | billable SE time = Cost of revenue | split before entering |
| Entertainment | tax treatment differs | separate line |

Always record as-of period (fiscal year and calendar months), entity/segment, currency.

## Reconciliation checklist

- [ ] revenue ÷ contracts within 5 % of deal size entered, or explained
- [ ] employed ≤ territories; in-ramp ≤ employed
- [ ] load rate has no facilities/overhead
- [ ] commission rate × revenue ≈ GL commission for quota carriers
- [ ] travel × employed ≈ GL quota-carrier T&E
- [ ] overhead + marketing + rep costs ≈ income-statement S&M (±10 %, exclusions named)
- [ ] ratios from the same fiscal year as revenue
- [ ] P, C, w on the same population and period
- [ ] every field tagged; no Default believed to be an Actual
- [ ] period, entity, currency written at the top

## Common mistakes

Counting open territories as sellers · using the default $75,000 with real contract data ·
win rate and cycle from different stages · overhead in the load rate · bookings as revenue ·
managers/SEs/inside reps in the seller count · percentages as whole numbers · mixed fiscal years.
