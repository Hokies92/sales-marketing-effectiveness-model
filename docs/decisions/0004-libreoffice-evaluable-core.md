# ADR 0004 — Computed core restricted to LibreOffice-evaluable formulas

**Status:** accepted · **Date:** 2026-10-26

## Context

CI verifies the workbook by recalculating it in LibreOffice. LAMBDA, LET, dynamic arrays and XLOOKUP are not evaluated there.

## Decision

Cells whose values also exist in the engine use only arithmetic, SUM/MIN/MAX/IF/IFERROR/INDEX/MATCH/SUMPRODUCT/CEILING and named ranges. Modern functions are allowed only in presentation cells whose removal changes no computed value.

## Consequences

Slightly longer formulas in the core; full CI verification retained. Revisit if CI gains Excel-native recalculation.
