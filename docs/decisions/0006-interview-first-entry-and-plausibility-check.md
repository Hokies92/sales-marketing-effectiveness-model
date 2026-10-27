# ADR 0006 — Entry is interview-first; the identity is a plausibility check on the client's numbers

**Status:** proposed — awaiting owner signature · **Date:** 2026-10-27 · **Ledger:** L15, L16

## Owner's words

> "I don't have faith in CRM data. I prefer calculating these by assumptions. If we use that data
> I want to know its sources. Typically I make it an interview process and allow people to fill
> in what they can."
>
> "When I use their data, often the numbers don't work, which means their data can't be true. By
> this I mean close rates, cycle time, cognitive capacity."

## Decision

1. Data entry is an **interview**: assumptions are the primary input; every field carries a
   source tag; exported data is optional evidence and is always shown with its source. The
   "CRM export first" default proposed by Claude on 2026-10-26 is withdrawn.
2. The revenue identity `R = N · (12·P / C) · w · A` is also a **consistency test**. Given any
   five of the six quantities the model computes the sixth and reports the gap against what the
   client stated — e.g. "revenue and headcount imply a 31% close rate; you entered 25%; at least
   one of these is not true." The check runs at entry time and names which inputs conflict.
3. The web entry page (Gate 1 F1) and the Inputs sheet (B3–B4) are designed as an interview with
   the plausibility check visible, not as an upload form.

## Consequences

- Engine: `plausibility(baseline) -> list[Conflict]` — pure arithmetic, no new data.
- Proposed addition to Gate 1 (owner to decide): criterion **B7 / F4 — plausibility check shown
  at entry**. It changes no output; it improves usability and is a differentiator.
