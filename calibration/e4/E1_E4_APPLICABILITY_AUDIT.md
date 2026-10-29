# E1/E4 Applicability and Claim-Coverage Audit

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD at audit start:** `f0970bc`
**HEAD at audit end:** `f0970bc` (read-only; no code changes)
**Contract:** `docs/e4-contract.md` v1.0 (frozen, unmodified)

---

## 1. Audit scope and baseline

| Item | Value |
|---|---|
| Repo path | `D:\skill-evidence-lint` |
| Branch | `phase-2/quality-and-e3` |
| Working tree | clean |
| Contract file | `docs/e4-contract.md` (456 lines, v1.0) |
| E1 claim extractor | `src/skill_evidence_lint/claim_extractor.py` |
| E4 implementation | `src/skill_evidence_lint/stale_check.py` |
| Pipeline | `src/skill_evidence_lint/runner.py` |
| E4 tests | `tests/test_stale_check.py` (A1–A34) |
| Fixture calibration | `calibration/e4/run_calibration.py` (24 samples) |
| Public corpus results | `calibration/e4/README.md`, `manifest.csv` |

No production code, contract, schema, CLI, or rule files were modified during this audit.

---

## 2. Contract requirements (E4 v1.0) — extracted with citations

| # | Requirement | Contract section |
|---|---|---|
| C1 | E4 only evaluates `(claim, evidence_ref)` pairs where **all** preconditions hold. | §1 (line 21–25) |
| C2 | E4 uses the **same `context_id` association model as E1–E3**: a claim's evidence references come from its local context (same paragraph or list item). E4 does not re-associate or guess across paragraphs. | §1.3 (line 53–55) |
| C3 | "E4 依附于 claim；无 claim 则无 E4。共享 `context_id`." | §8 compatibility table (line 335) |
| C4 | E2 and E4 are mutually exclusive on the same `(claim, ref)` pair; E4 runs only when `exists == True`. | §8 (line 336) |
| C5 | Skill baseline date fields (priority order): `date` → `updated` → `last_modified` → `version_date`. First parseable wins. | §3 (skill-side) |
| C6 | Evidence source groups: G1a (`as_of`, `data_date`) → G1b (`date`, `updated`, `last_updated`, `last_modified`, `generated`, `run_date`) → G2 (filename date) → G3 (labeled content date). Group-die-on-ambiguity, no fallback. | §2.1 |
| C7 | Read cap 1 MiB+1, UTF-8-sig, root-confined, symlink-safe. | §4 |
| C8 | Wildcard: single match uses resolved file; multi-match handed to E7; `?`/`**` treated literally. | §4.5 |
| C9 | Example claim in contract: `"reduces review time by 40%"` (line 279) — an improvement-style quantified claim. | §7 example |

**Key observation:** The contract's own illustrative claim (C9) is a Q-VERB-BY pattern. The contract does not separately define what counts as a "claim" beyond saying E4 reuses E1's association model (C2, C3). Therefore E4's scope is bounded by whatever E1/E1-extractor recognizes as a claim.

---

## 3. E1 claim detection coverage matrix

Source: `src/skill_evidence_lint/claim_extractor.py` lines 50–86.

### 3.1 The four patterns

| Pattern ID | Regex shape (simplified) | Example | Matches? |
|---|---|---|---|
| Q-VERB-BY | `(reduc\|improv\|increas\|cut\|low\|decreas\|boost\|shorten\|speed up) ... by N(%\|x\|times\|pp)` | "reduces latency by 30%" | ✅ |
| Q-ACHIEVES-NUM | `(achiev\|deliver\|ensur\|guarantee\|provide) N(%\|x\|times)` | "achieves 92% accuracy" | ✅ |
| Q-NUM-COMP | `N(%\|x\|times) (faster\|slower\|less\|more\|fewer\|...)` | "2x faster", "30% less memory" | ✅ |
| Q-ZERO | `(zero\|near-zero) (latency\|downtime\|errors\|...)` | "zero downtime" | ✅ |

### 3.2 Claim-type coverage

| Claim type | Example | Detected? | Pattern / reason | Test coverage |
|---|---|---|---|---|
| **Improvement quantified** ("by N%") | "We cut latency by 30%" | ✅ | Q-VERB-BY | A1, P01, etc. |
| **Achievement quantified** | "achieves 92% accuracy" | ✅ | Q-ACHIEVES-NUM | Not directly in fixtures |
| **Comparative** | "2x faster", "30% less memory" | ✅ | Q-NUM-COMP | Not directly in fixtures |
| **Zero/near-zero** | "zero downtime" | ✅ | Q-ZERO | None |
| **Performance threshold / guardrail** | "Crash-free rate > 99.5%", "Cold start < 2s" | ❌ | No "by", no comparative adjective, no verb from the list. Numbers alone are explicitly excluded (line 18–19). | None — but this is **by design** per line 18–19. |
| **Absolute metric** | "p95 latency is 120 ms" | ❌ | No verb/comparison/by. | None — by design. |
| **Comparative without number** | "faster than the previous version" | ❌ | No N%/x/times. | None. |
| **Qualitative effect** | "improves reliability" | ❌ | No quantifier. Explicitly out of scope (line 26). | None. |
| **Instruction / procedural** | "Run xcodebuild test" | ❌ | Not a claim. | N/A (correct). |
| **Number without effect** | "version 2.0", "timeout 30s" | ❌ | Explicitly excluded (line 18–19). | N/A (correct). |

### 3.3 Negation/hypothetical filter

Lines 91–99: sentences containing `not/never/no/if/could/would/might/expected to/aims to/targeting` within 40 chars before a match are dropped. This means:
- "We aim to reduce latency by 30%" → dropped (hypothetical).
- "Crash-free rate must stay > 99.5%" → never matched in the first place.

---

## 4. E1→E4 call chain (verified from source)

`runner.py` lines 103–124:

```
claims = extract_candidate_claims(parsed.contexts)   # E1/C1
references = extract_evidence_references(parsed.contexts)
association = associate_evidence(claims, references)  # pairs claims↔refs
e4_findings = check_stale(
    claims=claims,
    references=references,
    associated_pairs=association.associated,   # <-- only paired claims
    ...
)
```

`stale_check.py` `check_stale()` (line 401): iterates `associated_pairs`. If `association.associated` is empty (no claims), E4 returns `()` immediately after the skill-date check.

**Therefore:**
- E4 **only** processes claims that E1 extracted AND that `associate_evidence` paired with a local-path reference.
- If E1 finds 0 claims, E4 finds 0 findings regardless of how many dated evidence files exist.
- This matches contract C2/C3. No implementation deviation found.

---

## 5. The 24 fixture audit

Source: `calibration/e4/run_calibration.py`.

| ID | Claim text (abbrev) | E1 pattern? | E4 expected? | What it actually tests |
|---|---|---|---|---|
| P01 | "cut p95 latency by 30%" | Q-VERB-BY ✅ | positive | Basic G1b stale |
| P02 | "reduced error rate by 40%" | Q-VERB-BY ✅ | positive | G1a priority |
| P03 | "cut bundle size by 18%" | Q-VERB-BY ✅ | positive | G2 filename date |
| P04 | "cut test coverage misses by 22%" | Q-VERB-BY ✅ | positive | G3 content date |
| P05 | "cut cold start by 40%" | Q-VERB-BY ✅ | positive | Skill date fallback |
| P06 | "cut cost by 25%" (two ev) | Q-VERB-BY ✅ | positive (2 findings) | Multi-evidence, dedup, ordering |
| P07 | "cut memory by 12%" | Q-VERB-BY ✅ | positive | Z tz normalization |
| P08 | "cut flake rate by 50%" | Q-VERB-BY ✅ | positive | Single-match wildcard |
| N01–N05 | "cut latency by 10%" variants | Q-VERB-BY ✅ | negative | Equal/newer/ambiguity/placeholder/no-date |
| O01–O11 | "cut latency by 10%" variants | Q-VERB-BY ✅ | out-of-scope | Missing path, URL, multi-match wildcard, bad ext, no skill date, pre-2000, fractional sec, bad tz, impossible date, >1MiB, non-UTF-8 |

**Observation:** All 24 fixtures use the same claim shape ("cut X by N%", Q-VERB-BY). None exercise Q-ACHIEVES-NUM, Q-NUM-COMP, or Q-ZERO. None test threshold-type or absolute-metric claims. This is acceptable because the contract (C9) itself illustrates Q-VERB-BY, and E4's contract doesn't require E4 to evaluate non-Q-VERB-BY claims — but it means E4's positive path is only proven for one E1 pattern family.

---

## 6. Public corpus — what can be concluded

From `calibration/e4/README.md` (P2.6c.3 + P2.6c.4):

| Metric | Count |
|---|---|
| Real public SKILL.md files fetched | 26 |
| With a skill baseline date in frontmatter | ~8 (PracticalSwan A01–A05, Confluent A12, FitTracker D01/D02) |
| With E1-style claims ("by N%") | **0** |
| Expected E4 positives | 0 |
| E4 findings produced | 0 |
| False positives (among 26 real files) | 0 |

**What we can say with confidence:**
- E4 does not fire spuriously on real instruction/tutorial skills.
- 0 FP across 26 files is a negative-corpus signal, but it is **not** a meaningful recall/precision measurement because the denominator for "should have fired" is 0.

**What we cannot say:**
- We cannot claim E4 has 0 false negatives, because no real sample was ever expected to produce an E4 finding.
- We cannot claim the rule is production-calibrated; the positive path is only exercised by synthetic fixtures.

---

## 7. Findings — categorized

### 7.1 Confirmed (code + contract + tests agree)

1. **E4 is correctly wired to E1 claims.** No claim → no E4 finding. Matches contract §1.3 and §8.
2. **E2/E4 mutual exclusion works.** Missing paths are E2; E4 requires `is_file()`. Verified by A34.
3. **Skill date fallback, source-group priority, UTC normalization, 1 MiB cap, wildcard handoff** all match the frozen contract and are covered by A1–A34.
4. **The 26 real public skills produce 0 E4 findings.** This is correct behavior — they have no E1 claims.

### 7.2 Suspected gap (evidence points here but not a contract violation)

1. **E1's pattern set does not recognize threshold/guardrail statements** like "crash-free rate > 99.5%". This is **by design** (claim_extractor.py lines 18–19: "Numbers alone (versions, dates, config values, timeouts) do not match"). The E4 contract does not require E4 to evaluate threshold statements. This is a **scope decision**, not a bug.
2. **No fixture exercises Q-ACHIEVES-NUM, Q-NUM-COMP, or Q-ZERO.** If E1 were to recognize such claims, E4 would need to handle them; but since the contract example is Q-VERB-BY, this is a test-coverage gap, not a contract gap.
3. **Real public skills do not contain improvement-style claims.** The skill ecosystem consists of procedural instructions, not evidence reports. This means E4's positive path is not exercised in the wild.

### 7.3 Unknown / needs external input

1. Whether the skill ecosystem will ever produce "claim + dated local evidence" SKILL.md files.
2. Whether threshold-type statements should be in scope for a future rule (E8?) — that is a product decision, not a defect in E4 v1.0.
3. Whether users will actually write SKILL.md files in the shape E4 expects.

---

## 8. Conclusions A/B/C/D

| Option | Verdict | Evidence |
|---|---|---|
| **A. Contract scope is reasonable; samples insufficient** | **Yes** | Contract §1.3 and §8 explicitly tie E4 to E1 claims. The contract example (line 279) is Q-VERB-BY. Real skills lack such claims — this is a sample/ecosystem gap, not a contract bug. |
| **B. E1 claim detector may be too narrow** | **Partially** | E1 deliberately excludes thresholds/absolute metrics (line 18–19). Whether that's "too narrow" is a product decision. For E4 v1.0's purposes it is sufficient because the contract only addresses improvement-style claims. |
| **C. E4 call chain deviates from contract** | **No** | `runner.py` lines 103–124 and `stale_check.py` `check_stale()` correctly iterate `associated_pairs`, respect E2 mutual exclusion, and implement all preconditions. No deviation found. |
| **D. Contract has material ambiguity** | **No** | The contract is explicit about association, preconditions, source groups, and mutual exclusion. The only open question is scope (what counts as a claim), which is resolved by §1.3 saying "use E1–E3's context model." |

**Primary conclusion: A** — the contract is coherent; the public skill ecosystem simply doesn't contain the shape E4 was designed to check.

---

## 9. Recommended next tasks

| Task | Scope | Boundary |
|---|---|---|
| **P2.6d — User-supplied real skill calibration** | Collect 5+ real SKILL.md files from the user's own projects that contain "by N%" claims with dated local evidence. | No code changes; only calibration data. |
| **Future E-proposal (separate)** | Consider whether threshold/guardrail statements (">99.5%", "<2s") deserve their own rule with a different evidence model. | This would be a new rule (E8?), not an E4 change. Requires a new contract proposal. |
| **E1 test coverage** | Add fixtures for Q-ACHIEVES-NUM, Q-NUM-COMP, Q-ZERO to prove E4 works with those claim shapes. | Test-only; no semantic change. |

---

## 10. Verification run during audit

```
pytest: 206 passed, 3 skipped (3 symlink skips on Windows, expected)
ruff:   All checks passed!
```

No network access during this audit. No new samples downloaded. No production code modified.

---

## 11. Calibration status

**CALIBRATION INCOMPLETE** (unchanged). The synthetic fixture suite proves E4's logic; the public corpus proves no false positives on real instruction skills; but 0 real expected-positive cases have been found. This requires user-supplied evidence-backed SKILL.md files.
