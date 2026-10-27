# ADR 0005 — Revenue has two kinds: base (relationship) and growth (seller-driven)

**Status:** proposed — awaiting owner signature · **Date:** 2026-10-27 · **Ledger:** L11

## Owner's words

> "If the territory has customers in it that have ongoing relationships it can generate revenue,
> yes. But is it contributing to the growth plan? Unlikely. When I made this it was just easier
> to show as zero. It's a good note and something for a client to watch out for."
>
> On how fast base revenue decays in an uncovered territory: "We allow the data FROM the clients
> and let the answer reveal itself. We only need to create the structure to capture and then the
> rules to analyze so we know what we're looking for."

## Decision

1. Revenue per territory splits into **base** (relationship revenue — renewals, repeat orders —
   that continues for a time without a seller) and **growth** (new logos and expansion that
   require a seller). The original's data-entry note "separate new client revenue from upselling
   your installed base" becomes a modelled distinction, not advice.
2. A vacant territory earns **base revenue only**, growth = 0, cost = 0. Zero-for-everything was
   a 2002 simplification, recorded as such.
3. The rate at which base revenue decays while uncovered is **not assumed by the model**. The
   structure captures it (base share, uncovered months, observed base revenue by period) and the
   analysis rules report it; the client's data reveals the number.
4. New diagnostic entry: *"Renewal revenue hiding a coverage gap"* — a territory can look healthy
   on total revenue while its growth contribution has stopped.

## Consequences

- Inputs gain: base share of revenue (or base/growth split), with provenance.
- Engine: `revenue = growth(N, P, C, w, A) + base(territories, coverage, decay rule)`; golden
  numbers unchanged at defaults when base share = 0.
- Gate 1: no change to scope; the split is an engine capability rendered when ready.
