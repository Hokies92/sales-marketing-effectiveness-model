# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer as defined in
`CONTRIBUTING.md` §5 (MAJOR = a computed number changes for the same inputs).

## [Unreleased]

### Added
- Project governance: `CLAUDE.md`, `CONTRIBUTING.md`, `docs/gate-1.md`, `docs/canonical.md`,
  PR template, CODEOWNERS, pre-commit, seed ADRs 0001–0004.
- Repo hygiene: proprietary LICENSE, SECURITY.md, issue templates, Dependabot, tag-driven
  release workflow, .editorconfig; Gate 1 milestone with one issue per open criterion.

## [0.1.0] — 2026-10-24

### Added
- Engine v1 reproducing the 2011 workbook's logic with defects Q1–Q3 corrected; `legacy.py`
  reproducing the original cell-for-cell.
- Corrected workbook V1 generated from the engine and verified after recalculation (197 cells).
- Engine v2 per `docs/spec/business_logic_v1.md`: provenance, N ≠ T, demand ceiling, cost
  types, interventions, zero-residual bridges, comparison modes.
- CI on Python 3.11–3.13 with LibreOffice recalculation.
