# P2.6c.10 — Real-World Corpus Discovery and E4 Calibration Feasibility

**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`
**HEAD start:** `bd3ae4d`
**Mode:** read-only feasibility study. No code, contract, or label changes.

---

## 1. Search method and boundaries

This round did **not** attempt to fetch dozens more SKILL.md files. The
prior rounds (P2.6c.1–P2.6c.8) already inspected **29 distinct public
SKILL.md files** across these independent sources:

| Source group | Files inspected |
|---|---|
| anthropics/skills (official) | 9 |
| PracticalSwan/agent-skills | 5 |
| bm629/agent-skills | 2 |
| geronimo-iia, daymade, openlark, Confluent, benchflow, full-stack-skills | 6 |
| FitTracker2 (Regevba) | 2 (qa, design) |
| RConsortium/pharma-skills | 1 |
| snapsynapse/skill-a11y-audit | 1 |
| AlterLab-IEU (pinned) | 1 |
| voidmatcha (pinned) | 1 |
| Pvragon (pinned) | 1 |
| **Total** | **29** |

This round additionally probed `huggingface/skills`, `microsoft/skills`,
and `antfu/skills` READMEs — all are catalog/index repos; their listed
skills are procedural tool-use guides (same shape as the 29 above).

**Search boundary:** We did not exhaustively enumerate every SKILL.md on
GitHub. The 29 files cover the dominant public sources (Anthropic official,
independent author collections, corporate research repos, real-world
application repos). Generalization beyond this set is not claimed.

---

## 2. Failure-stage distribution (all 29 public files)

| Failure stage | Count | Notes |
|---|---|---|
| No E1-style claim ("by N%", "N% faster", "achieves N%", "zero X") | 29 | Every public skill is procedural or tutorial prose. |
| No skill baseline date (top-level recognized field) | ~22 | E01 nested; E03 uses `last_updated` (now recognized post-v1.1) |
| Claim exists but no associated local evidence reference | 1 (E01 line 138, now fixed by v1.1 backtick change) | After v1.1: 0 in this stage |
| Evidence file missing / out of scope | rest | E2 findings expected when only SKILL.md fetched |
| Evidence date earlier than skill date | 0 | No sample reached this stage |
| **Meets all E4 v1.0 conditions** | **0** | |

---

## 3. Why E4 positive cases don't exist in the wild

The E4 positive path requires a SKILL.md that:

1. States an **improvement claim** ("we reduced latency by 30%").
2. Cites a **local evidence file** in the same paragraph.
3. Has a **frontmatter baseline date**.
4. The evidence file has a **dated field** earlier than step 3.

Real-world SKILL.md files are **instructions to an agent**, not project
status reports. They say "do X, then Y" or "target must be >99%"; they
do not say "we achieved a 30% reduction, see benchmarks/q1.md (dated
2026-01-15)". That shape exists in engineering reports, blog posts, and
PR descriptions — not in skill manifests.

This is an **ecosystem mismatch**, not a search failure, not a detector
bug, and not a contract defect. The 0 false-positive result across 29
files is a *strong* negative signal: E4 correctly stays silent on the
kind of skills that actually exist.

---

## 4. Formal calibration statistics

| Metric | Count |
|---|---|
| Public SKILL.md files inspected (cumulative) | 29 |
| Provenance-complete (pinned SHA + verified license) | 0 (E01 has MIT in frontmatter but root LICENSE not fetched) |
| expected-e4 | 0 |
| expected-no-e4 | 0 |
| out-of-scope | 29 |
| ambiguous | 0 |
| pending-provenance | 1 (E04) |
| TP / FP / FN | n/a (no in-scope samples) |
| Synthetic fixtures (separate) | 24 (8 TP / 0 FP / 0 FN) |

**Real expected-e4: 0.**

---

## 5. Decision analysis

### Option A — Keep searching public ecosystem
- **Cost:** unbounded; we've already covered the major sources.
- **Expected yield:** near zero. The shape E4 checks for doesn't occur in
  skill manifests.
- **Recommendation:** stop broad search.

### Option B — Freeze E4 v1.0 as-is; accept incomplete calibration
- E4 logic is proven correct on 24 synthetic fixtures and correct-silent
  on 29 real files.
- The product can ship v0.1.0 with E4 marked "designed for evidence-backed
  skills; real-world coverage pending such skills existing."
- **Recommendation:** this is the honest status.

### Option C — Propose narrow v1.1 compatibility changes
- Already done in P2.6c.8 (top-level `last_updated`, backtick paths).
- Nested `metadata.*` (P2.6c.9) deferred.
- These improve compatibility but don't create positives.

### Option D — Independent E8 evidence-wide freshness rule
- Answers a different question ("is cited evidence old?") rather than
  ("is this claim's evidence stale?").
- Would need its own contract, thresholds, and calibration.
- **Recommendation:** separate proposal, not this phase.

### Option E — Lower the bar to claim "calibration complete"
- Rejected. Would mislead users about E4's real-world evidence.

### Recommended order
1. **Ship v0.1.0** with E4 as designed; document "real-positive coverage
   pending evidence-backed skills."
2. **Collect user-supplied samples** (via `USER_SAMPLES.md` /
   `INTAKE_AND_ACCEPTANCE.md`) rather than scraping public repos.
3. If evidence-wide freshness is wanted, propose E8 separately.

---

## 6. Verification run

```
pytest: 215 passed, 3 skipped
ruff:   All checks passed!
```

No code, contract, fixture, or label changes. No push/merge/tag/release.

---

## 7. Calibration status

**CALIBRATION INCOMPLETE.** Real expected-e4 = 0 across 29 public
files. The bottleneck is ecosystem: public SKILL.md files are procedural
instructions, not evidence reports. E4's logic is sound (proven on 24
synthetic fixtures and 0 FP on 29 real files), but real positive
calibration requires either (a) the ecosystem to produce evidence-backed
skill manifests, or (b) user-supplied samples from projects that already
write that way.
