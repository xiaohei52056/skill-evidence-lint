# P2.6c.9 — E4 Applicability and Data Model Review

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `8974fda`
**Mode:** read-only design review. No code, contract, or label changes.

---

## 1. Actual data flow (with citations)

```
SKILL.md text
  │
  ├─ parser.parse_text(text)            → list[MarkdownContext]
  │
  ├─ claim_extractor.extract_candidate_claims(ctxs)
  │     → list[CandidateClaim]           (E1/C1; only PARAGRAPH contexts)
  │     patterns: Q-VERB-BY, Q-ACHIEVES-NUM, Q-NUM-COMP, Q-ZERO
  │
  ├─ evidence_extractor.extract_evidence_references(ctxs)
  │     → list[EvidenceReference]        (LOCAL_PATH, URL, COMMAND)
  │     v1.1: backtick strict paths also emitted as LOCAL_PATH
  │
  ├─ evidence_association.associate_evidence(claims, refs)
  │     → associated_pairs: [(claim, ref)]  (same context_id)
  │     + E1 findings for claims with no associated ref
  │
  ├─ path_checker.check_local_paths(refs, skill_dir)
  │     → E2 findings (missing / escapes / symlink)
  │
  ├─ stale_check.check_stale(claims, refs, associated_pairs,
  │                          skill_dir, skill_frontmatter)
  │     skill_date = _skill_date(fm)      # top-level keys only
  │     for each (claim, ref) in associated_pairs:
  │         resolve, check exists, containment, size, encoding
  │         evidence_date from G1a→G1b→G2→G3
  │         if evidence_date < skill_date → E4 finding
  │
  └─ runner merges + sorts all findings
```

Key functions: `runner.run_check` (src/runner.py:93),
`stale_check._skill_date` (src/stale_check.py:328),
`stale_check._SKILL_FIELDS` (line 52, v1.1 list),
`evidence_extractor.extract_evidence_references` (line 69).

---

## 2. Topic A — Nested `metadata.*` dates

### Current behavior

`parse_frontmatter` uses `yaml.safe_load` (stale_check.py:258), which
returns nested dicts. For E01:

```yaml
metadata:
  last_updated: "2026-09-23"
```

The parsed dict has a top-level key `metadata` whose value is another
dict. `_skill_date(fm)` iterates `_SKILL_FIELDS` (`date`, `updated`,
`last_updated`, `last_modified`, `version_date`) against `fm` directly.
It never descends into `fm["metadata"]`. So E01's skill date is `None`.

### Contract position

v1.0 §3 lists top-level fields. The contract does not mention nested
`metadata`. v1.1 proposal (already implemented) added `last_updated`
at top level but explicitly did **not** flatten nested objects.

### Product tradeoff

| Option | Pros | Cons |
|---|---|---|
| Keep top-level only (current) | Deterministic, no ambiguity, simple | Skills that nest dates under `metadata:` get no skill date |
| Read only `metadata.last_updated` as a special case | Fixes E01 exactly | Ad-hoc; invites `metadata.updated`, `meta.date`, etc. |
| Recursively scan all nested objects for date fields | Most forgiving | Highly ambiguous: which nested date wins? Could pick up unrelated dates (e.g. a deprecation date, a changelog date). |

### Recommendation

**Defer.** Do not implement nested-date support in this phase. The
ecosystem evidence is thin (E01 is the only observed nested case). If 3+
more real skills show the same pattern, propose a narrow v1.1 that
reads exactly `metadata.last_updated` (not arbitrary recursion).

### Test matrix if ever implemented

- top-level `last_updated` wins over nested `metadata.last_updated`
- nested only → skill date recognized
- both valid but different dates → top-level wins
- nested invalid → falls through
- unrelated nested `date:` under `author:` → ignored
- placeholder/invalid tz/year-boundary still rejected

---

## 3. Topic B — E4/E1 coupling

### Current behavior (Model 1: claim-scoped)

E4 iterates only `associated_pairs` (claim + ref in same context). A
local reference that is not adjacent to an E1 claim never produces E4.

This is contract §1.3 and §8: "E4 依附于 claim；无 claim 则无 E4."

### Model 2 (evidence-wide freshness scan)

A separate rule (not a change to E4) that scans all LOCAL_PATH
references inside the skill and emits a freshness finding whenever the
evidence file's date predates the skill baseline date — regardless of
whether a claim is present.

### Tradeoff

| Dimension | Model 1 (current E4) | Model 2 (new rule) |
|---|---|---|
| Scope | Only claims E1 recognizes | All local evidence files |
| Noise | Low (only claims) | Potentially high (every reference gets checked) |
| Use case | "This claim's evidence is stale" | "This skill cites an outdated file" |
| E2 interaction | E2/E4 mutually exclusive per pair | Needs its own E2 relationship |
| Schema | E4 fields already exist | Would need a new rule ID (e.g. E8) |
| Real-sample evidence | 26 skills → 0 positive | Unknown; would need separate calibration |

### Recommendation

**Do not silently convert E4 to Model 2.** If Model 2 is desired, it
should be a **separate rule** (e.g. E8 `evidence-freshness`) with its
own contract, tests, and calibration. The current E4 contract is
coherent and should remain claim-scoped.

### Calibration implication

The fact that 26 real skills produce 0 E4 findings is **not** evidence
that E4 is broken; it is evidence that real skills don't make E1-style
claims. Model 2 would answer a different question and needs its own
thresholds (when is an evidence file "too old"?).

---

## 4. Topic C — E1 claim coverage

### Coverage matrix

| Claim type | Example (synthetic) | Detected? | Pattern | In product scope? |
|---|---|---|---|---|
| Improvement by N% | "reduces latency by 30%" | ✅ | Q-VERB-BY | Yes |
| Achieves N% | "achieves 92% accuracy" | ✅ | Q-ACHIEVES-NUM | Yes (but no E4 fixture exercises it) |
| Comparative | "2x faster", "30% less memory" | ✅ | Q-NUM-COMP | Yes (no E4 fixture) |
| Zero | "zero downtime" | ✅ | Q-ZERO | Yes (E01 "0 errors" fired) |
| Threshold | "crash-free > 99.5%" | ❌ | no "by"/comparative | **Deliberately out** (claim_extractor.py:18) |
| Absolute metric | "p95 is 120ms" | ❌ | no verb/comparison | **Deliberately out** |
| Qualitative | "improves reliability" | ❌ | no number | **Deliberately out** (line 26) |
| Instruction | "Run xcodebuild test" | ❌ | not a claim | Correctly excluded |
| Version/config | "version 2.0", "timeout 30" | ❌ | no effect verb | Correctly excluded |

### Risks of expanding E1

- Thresholds ("must be >99%") are **requirements**, not achieved results.
  Firing E4 on them would flag every skill that states a target.
- Absolute metrics are often current-state facts, not improvement claims.
- Qualitative claims ("fast", "reliable") are subjective and would
  generate noise.

### Recommendation

**Defer E1 expansion.** The current 4 patterns are deliberately narrow.
If evidence-backed skills start making threshold-style claims, that is a
new rule (e.g. E8 target-freshness), not an E1 broadening.

---

## 5. Real sample status (re-verified)

| ID | SHA pinned | License | Pre-label | E4 result | Provenance |
|---|---|---|---|---|---|
| E01 | e4836c0… | MIT in frontmatter; root LICENSE not fetched | out-of-scope (nested date) | 0 | partial |
| E02 | c6dacc7… | not verified | out-of-scope (no claim, no date) | 0 | pending |
| E03 | f369f9e… | not verified | out-of-scope (no claim) | 0 | pending |
| E04 | unpinned main | unknown | pending-provenance | n/a | incomplete |

Formal TP/FP/FN: **n/a** (no expected-e4 or expected-no-e4 in scope).

---

## 6. Recommendations (independent)

| Topic | Recommendation |
|---|---|
| A. Nested metadata dates | **Defer.** Wait for 3+ real samples; then propose narrow `metadata.last_updated` only. |
| B. E4/E1 coupling | **Keep claim-scoped (current).** If evidence-wide scan is wanted, propose as separate rule E8 in a separate contract. |
| C. E1 pattern expansion | **Defer.** Current 4 patterns are deliberately narrow; broadening would create false positives on thresholds/requirements. |

None of the three is implemented in this phase.

---

## 7. Verification

```
pytest: 215 passed, 3 skipped (re-run)
ruff:   All checks passed!
```

No code, contract, fixture, or label changes. No push/merge/tag/release.
Calibration remains **CALIBRATION INCOMPLETE** (0 real expected-e4).
