# Calibration Intake & Acceptance Process

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD:** `90df9cd`
**Status:** process established; calibration remains INCOMPLETE (no real authorized samples yet)

---

## 1. Purpose

This document defines how a future user-supplied or public real SKILL.md
sample is received, labeled, run, and counted toward the frozen E4 v1.0
contract §11.2 calibration threshold. It does **not** itself complete
calibration; it sets the bar so that when samples arrive, they are
accepted or rejected consistently.

---

## 2. Current state (verified this session)

| Item | Value |
|---|---|
| 24 synthetic fixtures re-run | 8 TP, 0 FP, 0 FN, 0 OOS violations |
| pytest | 206 passed, 3 skipped (Windows symlink) |
| ruff | All checks passed |
| Real public samples fetched | 26 files across 10 repos (see `manifest.csv`) |
| Real samples with pinned commit SHA | 0 (GitHub API rate-limited; all pinned to `main`) |
| Real samples with verified license | 0 (partial only; no per-file LICENSE.txt audit) |
| Real samples that are E1 claim-bearing | 0 |
| Real expected-e4 positives | 0 |

---

## 3. Intake checklist (per sample)

A sample is accepted into the formal calibration set **only when all
rows below are checked**. Otherwise it is labeled `pending-provenance`
or `excluded` and is not counted in calibration statistics.

### 3.1 Provenance

- [ ] Stable sample ID assigned (e.g. `U01`, `R01`).
- [ ] Source type recorded: user-authorized or public-repo.
- [ ] For public-repo samples: owner/repo/path/branch recorded.
- [ ] Immutable commit SHA recorded (not floating `main`).
- [ ] License name and LICENSE file location recorded.
- [ ] Redistribution right confirmed (for samples to be committed to repo).
- [ ] For user samples: explicit user authorization stated; sample stays
      local by default unless user says otherwise.
- [ ] Secrets, tokens, internal paths, PII stripped before any commit.
- [ ] Redaction (if any) does not alter claim text, dates, or reference
      paths.

### 3.2 E4 applicability (per frozen contract v1.0)

- [ ] E1 currently recognizes the claim (one of Q-VERB-BY, Q-ACHIEVES-NUM,
      Q-NUM-COMP, Q-ZERO). Thresholds like ">99.5%" do **not** count.
- [ ] Claim and local-path reference share a context (same paragraph or
      list item).
- [ ] Reference target exists, is inside Skill root, not a symlink escape.
- [ ] File extension in `.md .markdown .txt .json .yaml .yml .csv`.
- [ ] File ≤ 1 MiB, decodes as UTF-8-sig.
- [ ] Skill baseline date parses from `date`/`updated`/`last_modified`/
      `version_date` (first parseable wins).
- [ ] Evidence date is uniquely resolvable via G1a→G1b→G2→G3 with no
      group ambiguity.
- [ ] Evidence date < skill date (for expected-e4) or ≥ skill date (for
      expected-no-e4).
- [ ] Not a multi-match wildcard (E7 owns that); not a missing path
      (E2 owns that).

### 3.3 Labels

| Label | When |
|---|---|
| `expected-e4` | All preconditions met AND evidence date < skill date. |
| `expected-no-e4` | All preconditions met AND evidence date ≥ skill date. |
| `out-of-scope` | Any precondition fails (no claim, no date, missing file, etc.). |
| `ambiguous` | Contract does not uniquely decide; flagged for contract v1.1. |
| `pending-provenance` | Provenance/license/version not yet confirmed. Not counted. |

Labels are written **before** running the linter. No relabeling after
seeing results.

---

## 4. How a user runs their own Skill locally (no commit needed)

```powershell
# 1. Put your skill somewhere on disk, e.g. D:\my-skills\demo\
#    (must contain SKILL.md and referenced evidence files)

# 2. Run the linter (text output):
skill-evidence-lint D:\my-skills\demo

# 3. Run with JSON output for machine-readable results:
skill-evidence-lint --format json D:\my-skills\demo > result.json

# 4. Open result.json and check:
#    - Does E1 fire? (summary.by_rule.E1 > 0)
#    - Does E4 fire? (summary.by_rule.E4 > 0)
#    - Does this match what you expected?
```

You do **not** need to commit your skill. Share only:
- The `summary` block,
- Any E4/E1 findings,
- Your expected label and reasoning.

We do **not** execute commands in your skill, do not fetch URLs, and do
not read git history.

---

## 5. Acceptance math (contract §11.2)

The formal calibration set passes when:

- ≥ 20 real, provenance-complete samples (not synthetic fixtures).
- ≥ 5 expected-e4 samples that actually produce E4 findings.
- 0 false positives (an expected-no-e4 or out-of-scope sample producing
  an E4 finding).
- Labels were written before running; no relabeling after.

**Current count of samples meeting §3.1 + §3.2:** 0.

---

## 6. What we have vs. what we need

| Evidence type | What it proves | What it does not prove |
|---|---|---|
| 24 synthetic fixtures | E4 logic matches contract on all decision branches. | Real-world skill behavior. |
| 26 public SKILL.md files | E4 produces 0 false positives on instruction/tutorial skills. | E4 works correctly on positive cases. |
| A1–A34 unit tests | Each contract clause is implemented. | Real-world coverage. |
| User-supplied evidence-backed skills (when provided) | End-to-end real-world positive calibration. | Nothing yet — none provided. |

---

## 7. Next minimal action

A user with a real project can contribute 1–5 SKILL.md files that make
a "by N%" claim and cite a dated local evidence file. Even one such
sample with correct expected-e4 behavior would be the first real positive
data point. We do not need 20 samples to start; we need one genuine
evidence-backed claim to begin evaluating.

Until then, calibration remains **INCOMPLETE** by contract.
