# P2.6c.8 — E1/E4 Boundary Review and v1.1 Change Proposal

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `5ceab63`
**Mode:** read-only design review. No code, contract, fixture, or label changes.

---

## 1. Executive summary

Two independent boundary questions surfaced during P2.6c.7 real-sample intake:

1. **Q-A — `last_updated` as a skill-side baseline date field.** Real skills (E01, E03) commonly use `last_updated` in frontmatter; the E4 v1.0 contract only recognizes `date`, `updated`, `last_modified`, `version_date`.
2. **Q-B — backtick-wrapped local paths.** E01 line 138 wrote `` `examples/pr-1-retrospective.md` ``; the extractor masks backtick spans and classifies them as `RefType.COMMAND`, so no `LOCAL_PATH` reference is ever emitted.

This document evaluates both independently. Neither is approved. Both are candidate items for a future **contract v1.1** proposal, which would be a separate task.

---

## 2. Current behavior (with code citations)

### 2.1 Skill-side date fields

`src/skill_evidence_lint/stale_check.py` line 52:

```python
_SKILL_FIELDS = ("date", "updated", "last_modified", "version_date")
```

Line 328–330: `_skill_date(fm)` iterates these in order and returns the first parseable date. The contract §3 specifies the same priority. `last_updated` is **not** in this list. It does appear in the evidence-side G1b list (line 46), where it is accepted as an *evidence* date field — not a skill date.

### 2.2 Evidence reference extraction

`src/skill_evidence_lint/evidence_extractor.py`:

- Line 33: `_BACKTICK = re.compile(r"`([^`\n]+)`")` — matches inline code.
- Lines 86–109: backtick spans are emitted as `RefType.COMMAND` **and masked out** of the text before path scanning.
- Lines 133–145: `_LOCAL_PATH` regex runs only on the masked text, so backtick-wrapped strings are never seen as paths.

This is deliberate (module docstring lines 17–18): prevents `python run.py` from being double-counted as a path.

### 2.3 E01 outcome

- Q-ZERO claims fired on "0 errors" (lines 16, 71, 138).
- On line 138, `` `examples/pr-1-retrospective.md` `` is classified COMMAND.
- E1 (association) reports "no local-path or URL evidence reference in same context."
- E4 sees no associated pair AND no skill date (`metadata.last_updated` nested + field name not in `_SKILL_FIELDS`).
- Result: 0 E4 findings. Correct per v1.0 contract.

---

## 3. Q-A: Add `last_updated` to skill-side fields?

### 3.1 Current contract position

Contract §3 (skill baseline date): `date → updated → last_modified → version_date`. The contract does not mention `last_updated`.

### 3.2 Arguments in favor

- Real skills (E01, E03) use `last_updated`; two of three recent pinned candidates used it.
- `last_updated` is already accepted as an *evidence* date (G1b), so accepting it as a *skill* date is semantically symmetric.
- Low implementation cost: one tuple entry.

### 3.3 Arguments against / risks

- **Semantic overlap with `updated`.** If a skill has both `updated: 2026-01-01` and `last_updated: 2026-06-01`, which wins? The v1.0 priority is "first parseable wins" — insertion order must be defined.
- **Nesting.** E01 put `last_updated` under `metadata:` (indented). Current `parse_frontmatter` returns a flat dict; nested metadata is not flattened. Even if `last_updated` were added to the tuple, E01 would still fail because the field is nested. A field-name change alone does not fix E01.
- **Placeholder/validation rules already apply** (YYYY-MM-DD rejected, year ≥2000, tz range ±14:00). Adding a field does not bypass these.
- **Public evidence is thin.** Only 2 of ~30 inspected skills used `last_updated`. Not an ecosystem-wide signal.

### 3.4 Proposed v1.1 shape (if accepted)

- Add `last_updated` to `_SKILL_FIELDS` at a defined position (likely after `updated`, before `last_modified`, to preserve backward compatibility: existing skills with `updated` continue to win).
- Document in contract §3 that `last_updated` is top-level only; nested `metadata.last_updated` remains out of scope (or define a separate flattening rule — a larger change).
- Keep all date validation, placeholder rejection, and fallback behavior identical.

### 3.5 Test matrix (if implemented)

| Case | Expected |
|---|---|
| `last_updated: 2026-06-01` only | skill date = 2026-06-01 |
| `updated: 2026-01-01` + `last_updated: 2026-06-01` | first in priority list wins (order documented) |
| `last_updated: YYYY-MM-DD` | rejected (placeholder) |
| `last_updated: 2025-02-30` | rejected (calendar-impossible) |
| `metadata.last_updated: 2026-06-01` (nested) | out of scope per v1.1 (not flattened) |
| Existing 24 fixtures | unchanged results |

### 3.6 Recommendation

**Propose for v1.1, low priority.** It is a small, backward-compatible field addition, but it does not by itself fix E01 (which also has nested metadata and backtick-path issues). Defer until we have 3+ real samples affected.

---

## 4. Q-B: Treat backtick-wrapped local paths as LOCAL_PATH?

### 4.1 Current behavior

Backtick spans → COMMAND + masked. Path scanning never sees them.

### 4.2 Arguments in favor

- E01 line 138's `` `examples/pr-1-retrospective.md` `` is unambiguously a file reference; treating it as a command is a false negative for association.
- Markdown convention often uses backticks for file paths.

### 4.3 Arguments against / risks

- **False positives.** `` `python run.py` ``, `` `curl https://...` ``, `` `rm -rf /` `` are all backtick-wrapped but are commands. The current masking exists precisely to prevent these from becoming "evidence."
- **Inline code is frequently illustrative.** `` `npm install` `` is an instruction, not a path.
- **Determinism.** Path regex would need to distinguish `examples/foo.md` from `python run.py` based on shape (slashes, extension, no spaces/flags). False-positive risk is high.
- **This is an evidence_extractor-level decision** affecting E1, E2, E3, E4, E5, E6, E7 — not just E4. Loosening it changes behavior across all rules.

### 4.4 Proposed v1.1 shape (if accepted)

Do **not** disable backtick masking globally. Instead, add a narrow second pass:

- After extracting COMMAND entries, re-examine each command text.
- If it matches a strict path shape (relative path with `/`, no spaces, no shell flags like `--`, no shell metacharacters `$|;&>`, and ends with an E4-supported extension `.md/.markdown/.txt/.json/.yaml/.yml/.csv`), emit it as a **second** `LOCAL_PATH` reference in addition to COMMAND (not instead of).
- E2 still verifies existence; missing backtick-paths become E2 findings (same as un-backtick paths today).
- This is additive: no existing COMMAND is removed.

### 4.5 Test matrix

| Case | Expected |
|---|---|
| `` `examples/foo.md` `` | also emitted as LOCAL_PATH |
| `` `python run.py` `` | COMMAND only (no path shape) |
| `` `curl https://example.com` `` | COMMAND only (URL already handled separately) |
| `` `npm install` `` | COMMAND only |
| `` `README.md` `` (bare filename, no slash) | LOCAL_PATH (matches existing bare-filename rule) |
| `` `scripts/foo.sh` `` | COMMAND only (`.sh` not in supported extensions) |
| Backtick path outside skill root | E2 finding (path containment) |
| Existing 24 fixtures | unchanged results (fixtures don't use backtick paths) |

### 4.6 Recommendation

**Defer.** This is a broader extractor change. The current masking is a deliberate safety choice. A narrow additive pass is plausible but needs more real examples before we tune the path-shape regex. Wait for 2–3 more samples like E01 before implementing.

---

## 5. Compatibility and risk summary

| Item | v1.0 behavior | v1.1 candidate | Risk |
|---|---|---|---|
| Skill date fields | 4 fields | add `last_updated` (top-level only) | Low; priority order must be documented |
| Backtick spans | COMMAND + masked | COMMAND + optionally LOCAL_PATH if strict path shape | Medium; affects all rules that consume refs |
| Date validation | unchanged | unchanged | None |
| E2/E4 mutual exclusion | unchanged | unchanged | None |
| JSON schema v1 | unchanged | additive only (no new fields) | None |
| Existing 24 fixtures | pass | must still pass | Regression guard |

---

## 6. Validation plan for future v1.1 implementation

When/if v1.1 is implemented (separate task), run:

1. **Synthetic regression:** existing A1–A34 + 24 fixtures must pass unchanged.
2. **New unit tests:** for each row in §3.5 and §4.5 above.
3. **Real-sample re-run:** E01–E03 re-run after the change; document whether E01 now produces an E4 finding (it still won't, because `metadata.last_updated` is nested — Q-A field addition alone doesn't fix nesting).
4. **JSON by_rule smoke:** `skill-evidence-lint --format json` on a sample skill; verify schema id remains `skill-evidence-lint.report.v1`.
5. **Out-of-scope and pending-provenance samples are NOT counted as TP/FP/FN.**

---

## 7. Open questions

1. Should nested `metadata.last_updated` be flattened? (Larger change; deferred.)
2. What priority order if both `updated` and `last_updated` exist?
3. Is the path-shape regex for backtick-pass too strict or too loose? Needs more examples.
4. Are there other field names the ecosystem uses (e.g. `released`, `published`)? Need more samples.

---

## 8. Recommendation

- **Q-A (`last_updated`):** propose for v1.1, low priority. Documented as a candidate, not approved.
- **Q-B (backtick paths):** defer. Needs more real examples before loosening.
- Neither change is implemented in this task.
- Calibration status remains **CALIBRATION INCOMPLETE** (0 real expected-e4 samples). This review does not change that.
