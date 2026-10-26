# GitHub setup — one-time, owner only

Repository settings cannot be changed from automated sessions, so the owner applies these once.
`CONTRIBUTING.md` §7 is the policy; this is the click path and the API payload.

## 1. Branch protection on `main`

Settings → Branches → Add branch protection rule → pattern `main`:

- [x] Require a pull request before merging → required approvals **1**
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners
- [x] Require status checks to pass before merging → **Require branches to be up to date**
  - checks: `test (3.11)`, `test (3.12)`, `test (3.13)`
- [x] Require conversation resolution before merging
- [x] Require linear history
- [x] Do not allow bypassing the above settings (applies to administrators)
- [ ] Allow force pushes — **off**
- [ ] Allow deletions — **off**

Equivalent API call (from a machine with owner credentials):

```bash
gh api -X PUT repos/Hokies92/sales-marketing-effectiveness-model/branches/main/protection \
  --input - <<'JSON'
{"required_status_checks":{"strict":true,"contexts":["test (3.11)","test (3.12)","test (3.13)"]},
 "enforce_admins":true,
 "required_pull_request_reviews":{"dismiss_stale_reviews":true,"require_code_owner_reviews":true,"required_approving_review_count":1},
 "restrictions":null,"required_linear_history":true,"allow_force_pushes":false,
 "allow_deletions":false,"required_conversation_resolution":true}
JSON
```

## 2. Merge settings

Settings → General → Pull Requests: **Allow squash merging only** (default message = PR title
and body), **Automatically delete head branches**.

```bash
gh api -X PATCH repos/Hokies92/sales-marketing-effectiveness-model \
  -f allow_merge_commit=false -f allow_rebase_merge=false -f allow_squash_merge=true \
  -f delete_branch_on_merge=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY
```

## 3. Visibility

The repository is currently **public**. It contains the 2011 workbook (Forrester copyright
notice) and the full model logic. Decide deliberately: Settings → General → Danger Zone →
Change visibility → Private, unless public is intended. Record the decision in an ADR.

## 4. Releases

Tags `vX.Y.Z` are created by the owner on `main` after a `chore(release)` PR; CI attaches the
built workbook. Enable Settings → Actions → Workflow permissions → Read and write (needed for
release asset upload) when the release workflow is added.
