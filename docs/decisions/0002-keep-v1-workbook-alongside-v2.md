# ADR 0002 — Keep workbook V1 alongside V2

**Status:** accepted · **Date:** 2026-10-26

## Context

Users of the 2011 tool recognise its layout. V2 adds a scenario builder and bridges that change the shape of the sheets.

## Decision

Ship both: V1 = the faithful-but-corrected original (same columns, Q1–Q3 fixed); V2 = the spec-driven model. Both generated from the same engine.

## Consequences

Two builders to maintain; both verified in CI. V1 is frozen except for defect fixes.
