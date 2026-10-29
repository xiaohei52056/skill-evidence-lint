# P2.6c.12 — CI and Release Documentation Finalization

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `ebf8a72`
**Mode:** local documentation + verification. No push/PR/tag/release.

---

## 1. Repo state

| Item | Value |
|---|---|
| Branch | `phase-2/quality-and-e3` |
| HEAD start | `ebf8a72` |
| Remote | `origin https://github.com/xiaohei52056/skill-evidence-lint.git` |
| Branch pushed to origin | **no** (no upstream tracking; all phase-2 commits local) |
| Working tree at start | clean |
| CI workflow | `.github/workflows/tests.yml` (triggers on push to `main` and PR; matrix ubuntu/macos/windows × py3.11/3.12) |

---

## 2. Documentation changes

### CHANGELOG.md
- Expanded the E4 bullet to state explicitly that E4 is **claim-scoped**
  and that E2/E4 are mutually exclusive per pair.
- Added an "E4 compatibility notes" section documenting the two v1.1
  improvements (`last_updated` skill field, backtick strict-path
  association) and clarifying they are **proposed v1.1 changes**, not
  ratified; v1.0 contract unchanged.
- Added a "Calibration status disclosure" section that separates
  synthetic results (24 fixtures, 8/8/0/0) from real public corpus
  results (29 files, 0 expected-e4, 0 FP), and states real expected-e4
  is 0.

### No changes to
- `docs/e4-contract.md` (frozen v1.0)
- `docs/e4-contract-v1.1-proposal.md` (already present)
- README, pyproject, source code, tests, fixtures

---

## 3. Local verification (this run)

```
pytest:   215 passed, 3 skipped (Windows symlink WinError 1314)
ruff:     All checks passed!
sdist:    skill_evidence-lint-0.1.0.tar.gz built
wheel:    skill_evidence-lint-0.1.0-py3-none-any.whl built
```

CLI/JSON smoke was verified in P2.6c.11 (exit 0 on valid skill, exit 2
on bad path; schema `skill-evidence-lint.report.v1`; by_rule contains
E1–E7). No code changed since then, so those results still hold.

---

## 4. Remote CI status

**NOT VERIFIED.** The workflow exists and is correctly configured (matrix,
pytest, ruff, JSON smoke step), but it has never run because:

- This branch (`phase-2/quality-and-e3`) has never been pushed to origin.
- The workflow triggers on `push` to `main` and on `pull_request`.
- No PR has been opened.

Local Windows symlink skips are **not** equivalent to a passing Windows
CI job; the remote matrix must actually run.

---

## 5. Issues

### Blockers
None for local release readiness.

### Warnings
1. Remote CI has not run. Must push + open PR to trigger.
2. Real E4 positive calibration is incomplete (0 real expected-e4).
3. 3 symlink tests skip on Windows locally; they will run on CI Linux/macOS.
4. v1.1 compatibility changes are implemented but labeled "proposed".

### Follow-ups
1. Push branch and open PR to trigger CI.
2. After CI green, decide on `v0.1.0` tag and PyPI publish.
3. Future: collect user-supplied evidence-backed SKILL.md samples.

---

## 6. Release recommendation

**READY WITH DISCLOSED LIMITATIONS** (unchanged from P2.6c.11), now with
release documentation finalized.

- Local tests, lint, build, CLI, JSON output, exit codes all verified.
- CHANGELOG now accurately describes E4 scope, v1.1 compatibility, and
  calibration status.
- Remote CI is the one remaining gate; it requires user authorization to
  push.

---

## 7. Awaiting user decision

The following actions require explicit user authorization and have **not**
been performed:

1. `git push -u origin phase-2/quality-and-e3`
2. Open a pull request to `main`
3. Merge to `main`
4. Tag `v0.1.0`
5. Publish to PyPI

Waiting for user direction.
