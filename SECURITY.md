# Security policy

- Report vulnerabilities or data-exposure concerns privately to scott@successification.com.
  Do not open a public issue.
- Never commit secrets, tokens, customer data or real company inputs. Fixtures are synthetic.
- Dependencies are pinned with lower bounds in `pyproject.toml`; Dependabot opens update PRs
  weekly and they go through the normal PR gate.
- The web layer (Gate 1 F1–F3) must never return formulas, engine source or another user's
  inputs; only the requesting user's inputs and derived outputs.
