# ADR 0007 — The model tracks change over time; three clocks; state transitions are the primitive

**Status:** proposed — awaiting owner signature · **Date:** 2026-10-27 · **Ledger:** L17, L18

## Owner's words

> "Most track time like it's a constant. I do that, but I ALSO focus on change states based on
> customer variable actions. I know my calculations IN the model are basic arithmetic, but I am
> paying more attention to change states — so my analysis is very much aligned with calculus …
> I make many representations of 'points in time' and track changes among them. There are
> deadlines (quarter ends, year ends) that are Bergsonian time, there's a ton of calendar or
> Newton time, but I treat sales as about driving change so I spend more weight in the Leibniz
> view of time."
>
> "We need to factor in all forms of tracking time but it's analysis, not data entry. We just
> need to understand the logic and rationale of how the data is collected."
>
> "None of the other models are focused on the calculus and as such are more biased to
> managerial accounting. I focus on both, but with a bias to tracking change over time."

## Decision

1. **Principle.** The model's primitive is the *customer state transition* (a change caused by a
   customer's action). Calendar time is derived from the order and spacing of transitions. The
   2002 workbook is the steady-state, calendar-time projection of this idea; the rebuild keeps
   that projection as one view and does not mistake it for the model.
2. **Three clocks, named in the canonical vocabulary.** *Newton* — calendar, uniform, external
   (cycle months, fiscal year). *Bergson* — time as experienced pressure (quarter-end, year-end
   behaviour). *Leibniz* — time as the order of events; no change, no time (stage transitions,
   customer actions). Every quantity in the model is tagged with its clock. Today everything is
   Newton.
3. **Entry vs analysis.** Data entry captures raw observations and the *logic and rationale of
   how they were collected*; it does not ask the client to think in clocks. The clocks live in
   the analysis layer: points-in-time snapshots and the deltas between them (discrete calculus).
4. **Sequence.** Gate 1 is unchanged. After Gate 1, the engine's next core is event-based; the
   customer-state list is the first artefact needed and is tracked as its own thread.

## Consequences

- Canonical vocabulary gains the three clocks and the tag.
- A snapshot/delta view can be added on the current math as analysis without changing outputs.
- Competitive position: the differentiator is change-over-time (calculus) on top of the
  managerial-accounting view, not instead of it.
