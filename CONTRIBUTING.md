# Contributing — version control rules

These rules are mandatory for every contributor, human or AI. They exist so that `main` is
always releasable, every number is traceable to a reviewed change, and nothing in the model
changes by accident.

## 1. Branching

- `main` is protected: no direct commits, no force-push, no deletion, linear history.
- All work happens on short-lived branches from `main`, named
  `<type>/<scope>-<short-description>`, e.g. `feat/workbook-scenario-builder`,
  `fix/engine-ramp-rounding`, `docs/gate-1-status`, `chore/ci-coverage-gate`.
- One concern per branch. A branch lives days, not weeks; rebase on `main` before opening a PR.
- Release branches are not used; releases are tags on `main`.

## 2. Commits

- Conventional Commits, imperative mood, ≤ 72-character subject:
  `feat(workbook): add scenario builder sheet verified against engine v2`.
  Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`.
  Scopes: `engine`, `workbook`, `export`, `web`, `cli`, `spec`, `docs`, `ci`, `repo`.
- Body explains *why* and names the Gate 1 criterion or ADR it serves.
- A behaviour change to any number carries `BREAKING CHANGE:` in the footer and an ADR.
- Attribution footers required by the tooling (`Co-Authored-By`, `Claude-Session`) are kept.
- No WIP commits on `main`; squash-merge collapses branch history.

## 3. Pull requests

- Every change to `main` arrives by PR using `.github/PULL_REQUEST_TEMPLATE.md`, fully filled in.
- Required before merge:
  1. CI green on all three Python versions (lint, format, mypy strict, tests ≥ 95 % coverage,
     workbook build and recalculation verification).
  2. At least one approving review from a CODEOWNER; the author may not approve their own PR.
     AI-authored PRs are reviewed by the owner.
  3. Branch up to date with `main`.
  4. All review threads resolved.
- Merge method: **squash and merge** only. The squash message is a Conventional Commit.
- Delete the branch on merge.
- PRs over ~400 changed lines are split unless they are a generated artefact plus its test.

## 4. What a PR must contain

| If the PR… | it must also include… |
|---|---|
| changes any calculation | a test proving the new behaviour, the golden-number table updated if moved, and an ADR |
| touches the workbook builder | the recalculation-verification test passing, and the PDF render reviewed |
| adds an artefact (xlsx, export, page) | the code that generates it and a test that verifies it against the engine; never the artefact alone |
| fixes a defect of the original | the defect id (Q*), legacy reproduction untouched, a test showing the corrected path differs |
| moves a Gate 1 criterion | the status table in `docs/gate-1.md` and a `CHANGELOG.md` entry |
| adds a dependency | a one-line justification and a pinned lower bound in `pyproject.toml` |

## 5. Versioning and releases

- Semantic versioning on the engine: `MAJOR` = any computed number changes for the same inputs;
  `MINOR` = new capability, same numbers; `PATCH` = fixes that move no number.
- `__version__` in `src/smem/__init__.py` and `pyproject.toml` move together, in a `chore(release)` PR.
- A release is an annotated, signed tag `vX.Y.Z` on `main` with the CHANGELOG section as its
  message; CI attaches the built workbook(s) to the GitHub Release.
- `CHANGELOG.md` follows Keep a Changelog: Unreleased → Added / Changed / Fixed / Removed.

## 6. Repository hygiene

- Never commit: secrets, tokens, `.env`, customer or real-company data, generated outputs
  (`out/`, `dist/`), editor files. Fixtures are synthetic and small.
- `reference/original/` is immutable. A PR that modifies it is rejected.
- Large binaries (> 1 MB) need a reason; prefer generating them in CI.
- Signed commits are required once every contributor has a key configured; until then, verified
  authorship via the GitHub account is the minimum.

## 7. Enforcement

Branch protection on `main` (configured on GitHub; documented here so it can be re-applied):
require PR, require 1 approval, dismiss stale approvals, require CODEOWNER review, require status
checks `test (3.11)`, `test (3.12)`, `test (3.13)`, require branch up to date, require linear
history, require conversation resolution, block force-push and deletion, apply to administrators.

Local pre-commit hooks (`pre-commit install`) run ruff and mypy before every commit so CI rarely
fails on style.

## 8. Reviewing

A reviewer checks, in this order: does it move a Gate 1 criterion or an approved later phase;
is the number still the engine's; is the test real; is the artefact generated; would the Read-me
tab still be enough for a cold user. Approve only when all five are yes.
