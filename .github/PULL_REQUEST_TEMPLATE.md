## What

<!-- One sentence. Conventional-commit style title above. -->

## Why — Gate 1 criterion or ADR served

<!-- e.g. Gate 1 C2 (scenario builder) · ADR 0003 -->

## Does any computed number change?

- [ ] No — same inputs, same outputs (tests prove it)
- [ ] Yes — golden-number table updated, ADR included, `BREAKING CHANGE:` footer present

## Checklist

- [ ] Branch named `<type>/<scope>-<desc>`; one concern only
- [ ] `ruff check . && ruff format --check . && mypy && pytest --cov=smem --cov-fail-under=95` green locally
- [ ] Generated artefacts are produced by code in this PR and verified against the engine by a test
- [ ] `reference/original/` untouched
- [ ] `docs/gate-1.md` status table and `CHANGELOG.md` updated if a criterion moved
- [ ] No secrets, customer data, or generated outputs committed

## Evidence

<!-- Test names, screenshot/PDF of the sheet, export sample, or link to CI artefact -->
