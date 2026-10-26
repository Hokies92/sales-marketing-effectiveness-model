# ADR 0001 — Engine is the single source of truth

**Status:** accepted · **Date:** 2026-10-26

## Context

Five tabs of formulas with no tests had drifted (Q1, Q2) and could not be reused by a web tool.

## Decision

All calculations live in `src/smem/`. Workbooks, exports and web pages are generated from the engine and verified against it by tests. No number may exist only in a formula, macro or script.

## Consequences

Every artefact needs a builder and a verifier; hand edits to artefacts are rejected. CI must be able to recalculate the workbook (LibreOffice).
