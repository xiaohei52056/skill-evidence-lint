# P2.6c.13 — Remote CI Verification and Release Gate

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD:** `4514adf`
**Working tree:** clean
**Mode:** read-only preflight + plan. No push/PR/merge/tag/release performed.

---

## 1. Preflight findings

| Item | Value |
|---|---|
| Branch | `phase-2/quality-and-e3` |
| HEAD | `4514adf009dbfa882ef440c9306dd061e32f8989` |
| Upstream tracking | **none** (branch never pushed) |
| Remote | `origin https://github.com/xiaohei52056/skill-evidence-lint.git` |
| Unpushed commits | all phase-2 commits (10+) local-only |
| CI workflow | `.github/workflows/tests.yml` (matrix ubuntu/macos/windows × py3.11/3.12; pytest + ruff + JSON smoke) |
| Workflow triggers | `push` to `main`, `pull_request` |

The workflow will **not** run on a feature-branch push alone. It triggers
on PR or on push to `main`. So opening a PR from this branch to `main`
is the correct way to trigger the matrix.

---

## 2. Proposed remote operation plan (NOT EXECUTED)

Awaiting explicit user authorization. The steps, in order:

1. **Push branch:**
   `git push -u origin phase-2/quality-and-e3`
2. **Open PR** from `phase-2/quality-and-e3` → `main` (via `gh` CLI or
   GitHub web UI). This triggers the `pull_request` workflow.
3. **Watch CI:** poll `gh run list --branch phase-2/quality-and-e3`
   until all matrix jobs complete.
4. **If green:** report each job's conclusion; do not merge yet.
5. **If red:** read logs, fix locally, commit, push, re-watch.

These steps are **not** performed in this task. No authorization has
been given.

---

## 3. Release gate status

| Gate | Status | Notes |
|---|---|---|
| Local pytest | PASS (this run: 215 passed, 3 skipped) | 3 skips are Windows symlink (WinError 1314) |
| Local ruff | PASS | All checks passed |
| sdist/wheel build | PASS | v0.1.0 artifacts built |
| CLI text/JSON smoke | PASS (P2.6c.11) | exit 0 / exit 2 correct; schema v1; by_rule E1–E7 |
| pyproject version | PASS | `0.1.0` |
| CHANGELOG accuracy | PASS (P2.6c.12) | E4 scope, v1.1 proposal, calibration disclosure all present |
| Frozen v1.0 contract untouched | PASS | `docs/e4-contract.md` unchanged |
| **Remote CI matrix** | **BLOCKED** | Workflow never run; awaiting push + PR |
| PR review + merge authorization | **BLOCKED** | No PR exists |
| v0.1.0 tag | **BLOCKED** | Not created |
| PyPI publish | **BLOCKED** | Not performed |
| Real E4 positive calibration | **INCOMPLETE** | 0 real expected-e4; synthetic fixtures pass |

---

## 4. What would count as "REMOTE CI VERIFIED"

Only after a real PR is opened and all required jobs have green
conclusions:

- ubuntu-latest / py3.12: pytest + ruff + JSON smoke
- macos-latest / py3.12: pytest + ruff + JSON smoke
- windows-latest / py3.12: pytest + ruff + JSON smoke
- (py3.11 jobs on ubuntu only per workflow matrix)

Any skip, cancel, or failure must be disclosed; a green checkmark on
the workflow badge is not enough — per-job conclusions must be recorded.

The 3 Windows symlink tests that skip locally are expected to pass or
skip on CI depending on runner permissions; that must be observed, not
assumed.

---

## 5. Calibration status (unchanged)

- Synthetic: 24 fixtures, 8 TP / 0 FP / 0 FN.
- Real public corpus: 29 files, all out-of-scope, 0 expected-e4, 0 FP.
- Real expected-e4: **0**.
- Formal real TP/FP/FN: n/a.
- Status: **CALIBRATION INCOMPLETE** (ecosystem gap, not code defect).

---

## 6. Next action

Awaiting user decision on whether to authorize:

1. `git push -u origin phase-2/quality-and-e3`
2. Opening a PR to `main`
3. (After CI green) merging, tagging, and publishing

No action taken. Waiting.
