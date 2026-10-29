# P2.6c.8 — E4 Compatibility Improvements Report

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `947aea5`
**Mode:** code changes approved by task; no push/merge/tag/release.

---

## 1. Root-cause analysis

P2.6c.7 found that 3 pinned real candidates (E01–E03) all landed as
out-of-scope. Two distinct causes:

1. **Skill date field mismatch.** Real skills use `last_updated` in
   frontmatter; v1.0 recognized only `date`, `updated`, `last_modified`,
   `version_date`. E01 also nested it under `metadata:`, which is a
   separate issue.
2. **Backtick paths not seen as LOCAL_PATH.** E01 line 138 wrote
   `` `examples/pr-1-retrospective.md` ``. The extractor masked all backtick
   spans and emitted them only as `RefType.COMMAND`, so E1 had no
   local-path reference to associate with the nearby Q-ZERO claim.

Both were v1.0 design decisions, not bugs. The changes below are v1.1
compatibility improvements (proposed, not yet ratified).

---

## 2. Changes made

### 2.1 `last_updated` skill-side field

- File: `src/skill_evidence_lint/stale_check.py` line 52.
- `_SKILL_FIELDS` changed from
  `("date", "updated", "last_modified", "version_date")` to
  `("date", "updated", "last_updated", "last_modified", "version_date")`.
- Strict parsing unchanged (placeholder, calendar, year ≥2000, tz ±14:00).
- Top-level only; nested `metadata.last_updated` still not flattened.

### 2.2 Backtick-wrapped strict paths

- File: `src/skill_evidence_lint/evidence_extractor.py` after line 112.
- After emitting each COMMAND, the extractor re-checks the backtick
  content against the strict `_LOCAL_PATH` regex. If it matches, an
  additional LOCAL_PATH reference is emitted (additive; COMMAND kept).
- Strings with spaces, shell flags, metacharacters, or unsupported
  extensions remain COMMAND only.

### 2.3 Contract proposal

- New file: `docs/e4-contract-v1.1-proposal.md`.
- v1.0 file `docs/e4-contract.md` is **unchanged**.

---

## 3. Test matrix

| Test | File | Result |
|---|---|---|
| A35 last_updated only | test_stale_check.py | pass |
| A36 updated wins over last_updated | test_stale_check.py | pass |
| A37 invalid last_updated falls to version_date | test_stale_check.py | pass |
| A38 last_updated placeholder rejected | test_stale_check.py | pass |
| backtick strict path = both COMMAND + LOCAL_PATH | test_evidence_extractor.py | pass |
| backtick command not a path | test_evidence_extractor.py | pass |
| backtick bare filename with ext | test_evidence_extractor.py | pass |
| backtick unsupported ext (.exe) stays COMMAND | test_evidence_extractor.py | pass |
| backtick path with space not a path | test_evidence_extractor.py | pass |

**Full suite:** 215 passed, 3 skipped (Windows symlink), up from 206
before this change. Ruff clean.

---

## 4. E01–E04 re-evaluation after changes

| ID | Before | After | Reason |
|---|---|---|---|
| E01 (AlterLab) | 0 E4, 3 E1, 39 refs | 0 E4, **1 E1**, **59 refs** | Backtick paths now associate (E1 dropped from 3 to 1 because two claims now have paired refs). But skill date is still None: `metadata.last_updated` is nested, not top-level. E4 silent. |
| E02 (voidmatcha) | 0 E4 | 0 E4 | No claims, no skill date. |
| E03 (Pvragon) | 0 E4 | 0 E4 | No claims. `last_updated: 2026-10-16` is now recognized as skill date (top-level!), but 0 claims → no E4. |
| E04 (K-Dense) | pending-provenance | pending-provenance | Still unpinned. |

E03 is the interesting case: with the `last_updated` change, the skill
date **is** now recognized. But E03 has 0 E1 claims, so E4 still has
nothing to evaluate. This is correct behavior, not a defect.

E01 still does not fire because of the nested `metadata:` structure — a
separate v1.1 question not addressed here.

---

## 5. Formal calibration counts

| Metric | Count |
|---|---|
| Real samples with provenance verified | 0 (E02/E03 licenses still pending; E01 MIT in frontmatter but root LICENSE not fetched) |
| expected-e4 | 0 |
| expected-no-e4 | 0 |
| out-of-scope | 3 (E01, E02, E03) |
| pending-provenance | 1 (E04) |
| TP / FP / FN | n/a |

**Real E4 positives: 0.** The two improvements make the linter more
compatible with real-world skill formatting, but they do not manufacture
positive cases.

---

## 6. Verification actually run

```
pytest:        215 passed, 3 skipped
ruff:          All checks passed
sdist/wheel:   built successfully (skill_evidence_lint-0.1.0.tar.gz, .whl)
pip install .:  installed; CLI runs
CLI text:      Claims=3 Refs=59 Findings=23 on E01
CLI JSON:      by_rule includes E4=0; schema id unchanged
```

---

## 7. What is fixed vs. what still needs decisions

**Fixed (v1.1 implemented):**
- Top-level `last_updated` skill date now recognized.
- Backtick-wrapped strict relative paths now associate with claims.

**Still needs v1.1 decisions (not done):**
- Nested frontmatter flattening (`metadata.last_updated`).
- Whether `.sh` / other extensions should be in the LOCAL_PATH pass.
- E1 claim expansion for thresholds/absolute metrics (separate product
  question).

**Still missing (calibration gap, not code gap):**
- A real, provenance-complete SKILL.md that has a top-level date, a
  Q-VERB-BY/Q-ACHIEVES-NUM/etc. claim, and a dated local evidence file.
  Until that exists, real calibration stays incomplete.
