# SMEM — Operating Instructions

Read this file first in every session, human or AI. It is the contract for how work on this
repository is done. If anything here conflicts with a request, raise the conflict before acting.

## 1. What we are building, in order

**Long-term goal.** A commercial-effectiveness simulation and decision model that supports
everything in `docs/spec/business_logic_v1.md` and is a durable differentiator against sales
velocity calculators, capacity planners and vendor ROI tools (see `docs/model_teardown.md` §5).

**Gate 1 — the thing we must prove first.** Replicate the purpose and functionality of the 2011
workbook with twenty years of spreadsheet tech debt removed, in a form that is modern,
better to use, exportable, publishable to the web, and driven by Python where that helps.
Gate 1 is defined precisely in `docs/gate-1.md`. **Nothing beyond Gate 1 is built until Gate 1
is accepted**, except engine capabilities that Gate 1 itself requires.

## 2. Canonical foundation — the only sources of truth

Defined in `docs/canonical.md`. In short:

1. **The engine is the model.** `src/smem/` (engine v1 for the original's logic, engine v2 for the
   spec) is the single implementation of every calculation. Excel, web, exports and documents
   *render* it. No calculation may exist only in a formula, a macro, a JavaScript file or a doc.
2. **The original is preserved, not edited.** `reference/original/` is read-only. `legacy.py`
   reproduces it cell-for-cell, defects included, and `tests/test_legacy_reproduction.py` pins it.
3. **The golden numbers** in `docs/canonical.md` §4 are regression anchors. A change that moves
   one needs a documented reason in the same PR.
4. **Every defect of the original** is listed with an id (Q1…Q7). Fixing one means: documented,
   reproduced in legacy, covered by a test that proves the new behaviour differs.

## 3. Rules for every change

- Work on a branch, open a PR, let CI pass, get a review, squash-merge. Never commit to `main`.
  Full rules: `CONTRIBUTING.md`. They are strict on purpose.
- `ruff check`, `ruff format --check`, `mypy --strict`, `pytest` (≥ 95 % coverage) must be green
  locally before a PR is opened. CI re-runs them on 3.11–3.13 and rebuilds the workbook.
- Any generated artefact (an `.xlsx`, an export, a web bundle) is **built by code in this repo
  from the engine** and verified against the engine by a test. Hand-edited artefacts are not
  accepted.
- Excel: the computed core uses only formulas LibreOffice can evaluate (see `docs/canonical.md`
  §6) so it can be verified in CI; modern Excel features are used for *usability* on top of
  that core, never as the only place a number is computed.
- Python is the engine, the builder, the verifier and the API. It is not used where a formula
  the user can read does the same job in the workbook.
- No secrets, customer data or real company inputs in the repo. Fixtures are synthetic.
- Documents that explain the model live in `docs/`; a decision that changes the model goes in
  `docs/decisions/` as an ADR before or with the code.

## 4. How a session should run

1. `git pull`, read `docs/gate-1.md` status table and the open PRs.
2. State what you are about to do and which Gate 1 criterion it serves.
3. Branch, build, test, PR. One concern per PR.
4. Update the Gate 1 status table and `CHANGELOG.md` in the same PR when a criterion moves.
5. Report what changed and what the next criterion is. Do not expand scope.
6. **Close every report with a "So what, now what" block** in blunt plain speech:
   *Observation* (what was found) → *What it means for the whole model* → *Decision the owner
   needs to make*. The normal answer comes first; this block always follows it.

## 5. What not to do

- Do not add benchmarking, AI recommendations, CRM integration, Monte Carlo or a database
  before Gate 1 is accepted. They are Phase 5–6 (see `README.md`).
- Do not "improve" the original's numbers silently. Behaviour changes are explicit and tested.
- Do not re-derive the model from the workbook. The spec and the engine are upstream of it now.
- Do not describe Gate 1 as done because the engine passes; Gate 1 is accepted by the owner
  against `docs/gate-1.md`, with the artefacts in hand.
