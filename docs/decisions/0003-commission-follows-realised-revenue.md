# ADR 0003 — Commission follows realised revenue

**Status:** accepted · **Date:** 2026-10-26

## Context

The original charged full commission to new hires who earn no revenue in their ramp year, overstating year-one hiring cost by ~0.9M at defaults.

## Decision

Commission = commission rate × realised revenue. A guaranteed draw for ramping hires is an explicit OperatingPolicy field, default 0.

## Consequences

Year-one hire ΔOI moves from −2,543,500 (v1) to −1,643,500 (v2). v1 keeps the original rule for the V1 workbook; v2 is canonical going forward.
