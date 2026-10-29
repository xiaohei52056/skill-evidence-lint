# P2.6c.7 — Real Skill Candidate Intake (read-only validation)

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `d9d6fe2`
**HEAD end:** (this commit)
**Mode:** read-only; no production code, contract, or fixture changes.

---

## 1. Candidates fetched at pinned SHAs

| ID | Repo | SHA | Skill path | Support file | License |
|---|---|---|---|---|---|
| A | AlterLab-IEU/AlterLab-Academic-Skills | `e4836c08a20da195a11f30f203a8cf23ec30aa95` | `skills/core/alterlab-link-health/SKILL.md` | `examples/pr-1-retrospective.md` | MIT (frontmatter) |
| B | voidmatcha/ui-clone-skills | `c6dacc7a14ca1bc655dbda99c25cbfd5f0baf3e6` | `skills/benchmark/SKILL.md` | `scripts/benchmark-harvest.sh` | not verified |
| C | Pvragon/ai-workspace-reference | `f369f9e416992a109bc7566cc430392c2b4dfe14` | `team-lib/skills/skill-autoresearch/SKILL.md` | `programs/skill-clarity.md` | not verified |
| D | K-Dense-AI/scientific-agent-skills | **unpinned** (main) | `skills/exploratory-data-analysis/SKILL.md` | — | not verified |

D was not downloaded (no pinned SHA; per task rules, floating `main` is not a fixed version).

---

## 2. Pre-run labels (written before running linter)

| ID | Pre-label | Reasoning |
|---|---|---|
| A | `out-of-scope` | Frontmatter date field is `metadata.last_updated: "2026-09-23"` — nested under `metadata:` AND field name `last_updated` is not in `_SKILL_FIELDS = ("date","updated","last_modified","version_date")`. No skill date → E4 silent. Also backtick-wrapped paths likely classified as commands, not LOCAL_PATH. |
| B | `out-of-scope` | No date/updated/last_modified/version_date field. No E1 claim patterns observed (procedural benchmark skill). |
| C | `out-of-scope` | `last_updated: 2026-10-16` top-level, but `last_updated` is not in `_SKILL_FIELDS`. `created: 2026-03-16` also not recognized. No E1 claim patterns observed. |

---

## 3. Actual linter output

### Candidate A (AlterLab link-health)

```
claims=3 refs=39
E1 L16:  No local-path or URL evidence reference found ...
E1 L71:  No local-path or URL evidence reference found ...
E1 L138: No local-path or URL evidence reference found ...
E3 L16, L71, L138: reproducibility cue missing
E4: 0 findings
```

- **Claims detected:** 3, all Q-ZERO matching `"0 errors"` (lines 16, 71, 138). These are weak matches on retrospective language ("1208 → 0 errors").
- **Association:** failed. On line 138, the reference `` `examples/pr-1-retrospective.md` `` is backtick-wrapped and classified as `RefType.COMMAND`, not `LOCAL_PATH`. E1 therefore reports "no local-path reference in same context."
- **Skill date:** none recognized. `metadata.last_updated` is nested and uses field name not in `_SKILL_FIELDS`.
- **E4:** 0 findings. Correct per contract (no skill date + no associated pair).

### Candidate B (ui-clone-skills benchmark)

```
claims=0 refs=255
E2: 13 findings (missing files: AGENTS.md, regions.json, dom-extraction.md, ...)
E4: 0 findings
```

- No E1 claims. No skill date. All E2 findings are expected (we only fetched SKILL.md and the harvest script; the other referenced files don't exist locally).

### Candidate C (skill-autoresearch)

```
claims=0 refs=64
E4: 0 findings
```

- No E1 claims. No recognized skill date (`last_updated` not in `_SKILL_FIELDS`).

---

## 4. Expected vs. actual

| ID | Pre-label | Actual E4 | Match? | Notes |
|---|---|---|---|---|
| A | out-of-scope | 0 E4 | ✅ | Q-ZERO claims exist but not associated (backtick=command), and no skill date. |
| B | out-of-scope | 0 E4 | ✅ | No claims, no date. |
| C | out-of-scope | 0 E4 | ✅ | No claims, no recognized skill date. |

**No expected-e4 samples this round.**

---

## 5. New findings (not bugs, but observations)

1. **Field-name mismatch:** Real-world skills commonly use `last_updated` in frontmatter (A, C both do). The E4 contract's recognized skill-side fields are `date`, `updated`, `last_modified`, `version_date` — `last_updated` is not among them. This is a **contract-level decision**, not a bug. If the ecosystem prefers `last_updated`, that is a future v1.1 proposal, not a fix for this phase.
2. **Backtick-wrapped paths are treated as commands:** On line 138 of A, `` `examples/pr-1-retrospective.md` `` is classified as `RefType.COMMAND`. Whether this is correct depends on the evidence_extractor's rules; E4 never sees it as a path reference. This is consistent with E1 behavior (E1 also reports no association), so it is not an E4 defect.
3. **Q-ZERO matches "0 errors":** This is a known pattern (zero errors/downtime). It fired on retrospective prose, but that's by design — E1 reports "claim without evidence" (E1 warning), not an E4 finding.

---

## 6. Counts (this round)

| Metric | Count |
|---|---|
| Candidates downloaded at pinned SHA | 3 (A, B, C) |
| Candidates unpinned / not downloaded | 1 (D) |
| License verified | 1 (A: MIT in frontmatter; root LICENSE not fetched) |
| Pending-provenance | 2 (B, C — root LICENSE not verified) |
| expected-e4 | 0 |
| expected-no-e4 | 0 |
| out-of-scope | 3 |
| ambiguous | 0 |
| Real E4 positives | **0** |
| TP / FP / FN | n/a (no positives or negatives in scope) |

**This round did not find a qualified E4 positive sample.**

---

## 7. What would actually produce an E4 finding

Based on this round, a real sample that fires E4 needs ALL of:

1. Top-level frontmatter field named `date`, `updated`, `last_modified`, or `version_date` with a valid ISO date (not `last_updated`, not nested under `metadata:`).
2. A paragraph containing a Q-VERB-BY / Q-ACHIEVES-NUM / Q-NUM-COMP claim (e.g., "reduces latency by 30%").
3. A **non-backtick-wrapped** local path reference in the same paragraph (e.g., `benchmarks/2026-q1.md`), not `` `benchmarks/2026-q1.md` ``.
4. That path resolves to an existing file inside the skill directory.
5. The file has a unique parseable date (G1a/G1b/G2/G3) earlier than the skill date.

The public skills investigated so far fail at step 1 (wrong field name) or step 2 (no improvement claim) or step 3 (paths in backticks).

---

## 8. Verification run

```
pytest: 206 passed, 3 skipped
ruff:   All checks passed!
```

No code, contract, or fixture changes. No skill scripts were executed. No push/merge/tag/release.
