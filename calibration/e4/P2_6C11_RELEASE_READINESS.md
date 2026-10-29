# P2.6c.11 — Release Readiness Review (no release performed)

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `3f0f04a`
**Mode:** read-only review. No release, no push, no tag.

---

## 1. Repo state

| Item | Value |
|---|---|
| Branch | `phase-2/quality-and-e3` |
| HEAD | `3f0f04a` |
| Working tree | clean at start; only this report added |
| Package | `skill-evidence-lint` |
| Version | `0.1.0` (pyproject.toml) |
| Python requirement | `>=3.11` |
| License | MIT |
| Entry point | `skill-evidence-lint = skill_evidence_lint.cli:app` |

---

## 2. Metadata consistency

| Item | Status |
|---|---|
| pyproject version `0.1.0` | matches CHANGELOG "Unreleased" note (first post-0.1.0 release pending) |
| Runtime deps | `typer>=0.12`, `markdown-it-py>=3.0`, `pyyaml>=6.0` |
| Dev deps | `pytest>=8.0`, `ruff>=0.5` |
| CLI entry point | works (verified below) |
| JSON schema id | `skill-evidence-lint.report.v1` (verified on output) |
| README badge | CI badge points to `tests.yml` (workflow exists) |

**Note:** CHANGELOG contains a few mojibake em-dashes (`鈥?`) from an
earlier Windows encoding write. Cosmetic; not a release blocker.

**Note:** CHANGELOG "Added" section lists E1–E7 but does not yet mention
the v1.1 compatibility additions (top-level `last_updated`, backtick
strict-path association) from P2.6c.8. This is a **documentation gap**,
not a blocker for v0.1.0 (which hasn't been tagged yet — these changes
are on the pre-release branch and will be in the first release notes).

---

## 3. E4 behavior vs. documentation

| Claim in docs | Verified in code |
|---|---|
| E4 is claim-scoped (only E1-associated pairs) | `runner.py:118` passes `associated_pairs` |
| E2/E4 mutually exclusive | A34 test passes; E4 checks `is_file()` itself |
| Skill date fields: `date → updated → last_updated → last_modified → version_date` | `stale_check.py:52` (v1.1 list) |
| Evidence date groups G1a/G1b/G2/G3 | `stale_check.py:42-50, 70-83` |
| 1 MiB read cap, UTF-8-sig, root-contained | `stale_check.py` bounded read |
| Wildcard single-match resolved, multi-match → E7 | A08, A14/A15 tests |
| Frozen v1.0 contract at `docs/e4-contract.md` | unmodified (verified) |
| v1.1 proposal at `docs/e4-contract-v1.1-proposal.md` | present, marked "proposed, not ratified" |

All consistent. No drift between code and contract.

---

## 4. Verification actually run

```
pytest:  215 passed, 3 skipped (Windows symlink WinError 1314)
ruff:    All checks passed!
sdist:   skill_evidence_lint-0.1.0.tar.gz built
wheel:   skill_evidence_lint-0.1.0-py3-none-any.whl built
pip install .:  installed; console script runs
CLI text (valid skill):  exit 0, claims=1 refs=1 findings=2
CLI text (bad path):     exit 2 (InputError)
CLI JSON:  top-level keys [schema, tool, input, summary, claims, references, findings]
           schema = "skill-evidence-lint.report.v1"
           by_rule = {E1:0, E2:0, E3:1, E4:1, E5:0, E6:0, E7:0}
CI workflow:  .github/workflows/tests.yml exists (ubuntu/macos/windows × py3.11/3.12)
              CI status: NOT VERIFIED (branch never pushed; workflow triggers on push to main / PR)
```

---

## 5. Calibration status (separated)

**Synthetic (24 fixtures, run via `calibration/e4/run_calibration.py`):**
- 8 expected-e4 positives, 0 false negatives
- 5 expected-no-e4 negatives, 0 false positives
- 11 out-of-scope, 0 out-of-scope violations
- This validates E4 logic on its designed decision branches.

**Real public corpus (29 SKILL.md files across 13+ sources):**
- 0 expected-e4, 0 expected-no-e4 in scope
- 29 out-of-scope (no E1 claim, no skill date, or both)
- 0 false positives (E4 correctly silent)
- Formal TP/FP/FN: n/a (no in-scope real samples)
- Real expected-e4: 0
- Status: **CALIBRATION INCOMPLETE**

This is an **ecosystem gap**, not a code defect. The synthetic suite
proves the logic; the real corpus proves E4 doesn't fire spuriously.

---

## 6. Issues

### Blockers
None. The package builds, installs, runs, emits correct exit codes, and
produces valid v1 JSON. All tests pass.

### Warnings (must be disclosed in release notes)
1. **Real-world positive calibration is incomplete.** E4 has not been
   exercised on a real evidence-backed SKILL.md. Users should expect E4
   to produce few/no findings on typical procedural skills.
2. **CI matrix is unverified.** The workflow exists but has not run on
   this branch (it triggers on `main` push / PR, and this branch has
   never been pushed). Local verification is on Windows/Python 3.12 only.
3. **3 tests skipped on Windows** due to symlink creation requiring
   elevated privileges (WinError 1314). These pass on Linux/macOS CI.
4. **v1.1 compatibility additions** (`last_updated`, backtick paths)
   are implemented but documented as a proposal, not ratified. Behavior
   is backward-compatible.

### Follow-ups (not blockers)
1. CHANGELOG mojibake em-dashes (cosmetic).
2. CHANGELOG should mention E4 v1.1 compatibility additions when the
   first release notes are written.
3. Nested `metadata.*` date support deferred.
4. User-supplied real sample intake flow exists but no samples yet.

---

## 7. Release recommendation

**READY WITH DISCLOSED LIMITATIONS** for v0.1.0.

- The linter is functionally complete for rules E1–E7.
- Synthetic fixtures prove logic correctness.
- Build, install, CLI, JSON output, and exit codes all verified locally.
- E4's real-world positive calibration is incomplete; this should be
  disclosed in the release notes (not hidden).
- CI has not yet run on this code (will run on first PR/push to main).

**Do not claim** in release notes that E4 has been validated on real
evidence-backed skills. The honest statement is: E4 is designed for that
use case, logic-proven on synthetic fixtures, and currently produces no
findings on typical procedural skills.

---

## 8. Items awaiting user decision

1. Push this branch to origin and open a PR to `main` (triggers CI).
2. After CI passes, decide whether to tag `v0.1.0` and publish to PyPI.
3. Whether to disclose E4 calibration status in the README badge area.

No release action has been taken. Waiting for user direction.
