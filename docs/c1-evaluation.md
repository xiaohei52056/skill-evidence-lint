# C1 Candidate-Claim Extraction — Phase 7B Evaluation

**Date:** 2026-10-27
**Evaluated build:** `src/skill_evidence_lint/claim_extractor.py` (unchanged this phase)
**Runner:** `scripts/run_c1_eval.py` (dev-only helper; not imported by pytest)
**Rule set under test:** the four shipped patterns `Q-VERB-BY`, `Q-ACHIEVES-NUM`, `Q-NUM-COMP`, `Q-ZERO`, with the existing negation / 40-char hypothetical guard.

## 1. Scope and method

C1 proposes **candidate English effect claims** — it does not judge truth. This run reuses the production `parse_text()` + `extract_candidate_claims()` against two fixture sets:

- **Real documents:** 17 redistributable public `SKILL.md` files (13 Apache-2.0 from `anthropics/skills`, 4 MIT from `obra/superpowers`) downloaded at pinned commits (see `tests/fixtures/c1_eval/manifest.json`). An earlier, larger collection of 22 files was trimmed after a per-directory license audit; see §2 and `manifest.json` → `excluded`.
- **Synthetic fixture:** 1 hand-written Markdown file (`tests/fixtures/c1_eval/synthetic/synthetic_claims.md`) covering the required phenomena.

Downloaded docs were treated as untrusted data: no commands executed, no URLs followed, no packages installed.

### Annotation categories

- **A. in_scope_positive** — should be caught by v0.1 C1.
- **B. in_scope_negative** — must NOT be caught (versions, dates, config values, dimensions, ratios, instructions, descriptive statistics).
- **C. known_out_of_scope** — expresses an effect but v0.1 does not promise to catch it (qualitative, passive-without-verb-root, Chinese).
- **D. ambiguous** — left for manual judgment; not counted in precision/recall.

## 2. Sample composition

| Set | Docs | Repos | Commit-pinned | License |
|---|---|---|---|---|
| Real (redistributable) | 17 | 2 | yes | Apache-2.0 (13), MIT (4) |
| Synthetic | 1 | n/a | n/a | project-owned |

Real docs by repo (redistributable set after per-directory license audit):

- `anthropics/skills` @ `dbd4588f9e1033efb41dad4bef2f7947c8993d44` (Apache-2.0, 13 files): academy-guide, algorithmic-art, brand-guidelines, canvas-design, discernment-nudge, frontend-design, internal-comms, mcp-builder, skill-creator, slack-gif-creator, theme-factory, webapp-testing, web-artifacts-builder.
- `obra/superpowers` @ `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b` (MIT, 4 files): brainstorming, systematic-debugging, test-driven-development, writing-plans.

**License-driven sample reduction (Phase 9.2).** An earlier version of this fixture held 18 Anthropic files. A per-directory license audit at the pinned commit found that `docx`, `pdf`, `pptx`, and `xlsx` carry a proprietary "© 2025 Anthropic, PBC. All rights reserved." LICENSE.txt that explicitly forbids extraction, reproduction, derivative works, and redistribution to third parties; `doc-coauthoring` had no LICENSE.txt at all (default all-rights-reserved). These 5 files were removed from redistributable fixtures. They are listed in `manifest.json` under `excluded`; their numeric examples referenced below were from those removed files and are no longer part of the shipped sample.

**Repo-diversity limitation.** The target was ≥5 distinct public repos. Unauthenticated GitHub API rate-limited further repository enumeration during collection, so only 2 repos were reachable. This is a sample-selection limitation, not a code result; it is called out honestly here rather than padded with synthetic docs.

## 3. Results

### 3.1 Real documents

C1 produced **0 candidate claims across all 17 redistributable real files**.

A second-pass audit (Phase 7B.1) went beyond numeric grep and specifically swept for:
- the Q-VERB-BY roots (`reduce/improve/increase/cut/lower/decrease/boost/shorten/speed up/sped up`) anywhere, then confirmed none of them is followed within the clause by `by <number><unit>`;
- Q-ACHIEVES-NUM triggers (`achieve/deliver/ensure/guarantee/provide`) near numbers;
- Q-NUM-COMP pattern `<number><unit> faster|slower|less|more|higher|lower|…`;
- literal `zero`, `near-zero`, and `0` adjacent to any noun (not just the Q-ZERO noun list).

**Outcome of the audit: 0 in-scope-positive spans were found in the 17 redistributable docs.** The numeric occurrences that do exist in the shipped files are all legitimate negatives:

| Example | File:line | Category | Why not a claim |
|---|---|---|---|
| "90% algorithmic generation, 10% essential parameters" | algorithmic-art L26 | B | descriptive ratio of a style recipe, not a measured effect |
| "128x128", "480x480" | slack-gif-creator L14-15 | B | pixel dimensions |
| "60% train and 40% held-out", "3 times", "5 times" | skill-creator L394 | B | ML split / iteration counts |
| "3 times" inside `test('…', async () => {…})` | test-driven-development L77 | B (code block) | fenced code, parser excludes it |
| "95% of 'no root cause' cases are incomplete investigation" | systematic-debugging L275 | B | descriptive statistic about debugging, not a tool effect |
| "Python 3.11", "2026-03-15", "timeout=30" style config | various | B | version / date / config |
| "zero-pads", "zero border-radius", "denominators that can be zero" | docx/frontend/xlsx (removed) / frontend | B | technical usage unrelated to effect claims |
| "reduce alpha", "cut any decoration", "reduced motion respected" | slack-gif/frontend | B | procedural instructions, no quantified `by <unit>` result |
| "systematic is faster than thrashing" | systematic-debugging L42 | C | qualitative comparative, no number |
| "TDD … slower, not faster" | test-driven-development L234 | C | qualitative, inside a negation table cell |

(Examples from the removed `docx`/`pdf`/`pptx`/`xlsx`/`doc-coauthoring` files — e.g. "80%+ of sections done", "60-70% visual weight", "0.0x valuation format", "zero QA risk", "Zero formula errors" — are no longer part of the shipped fixture; they remain documented here only as historical audit notes and were not counted toward the final metrics.)

**Real-set accounting (Phase 9.2 refined):**

| Metric | Value |
|---|---|
| Documents audited (redistributable) | 17 |
| C1-flagged candidates | 0 |
| Hand-annotated in-scope-positive spans (A) | 0 |
| Genuine missed claims (A not flagged) | 0 |
| Flagged but hand-reviewed as non-claim (false positives) | 0 |
| Known-out-of-scope spans (C) in shipped docs | 2 (the two qualitative comparatives above) |
| Ambiguous spans (D) requiring further judgment | 0 |

Because the in-scope-positive denominator is zero, **neither precision nor recall is computable on the real set.** Observing zero flagged candidates and zero hand-annotated positives is not evidence that C1 has been validated against real-world marketing-style docs; it reflects that this particular corpus is overwhelmingly procedural. This is stated as a sample limitation, not a pass grade.

### 3.2 Synthetic fixture

C1 flagged 13 spans (lines 8–58 of `synthetic_claims.md`):

| Line | Pattern | Text | Annotation |
|---|---|---|---|
| 8 | Q-VERB-BY | `reduces processing time by 40%` | A ✓ |
| 9 | Q-VERB-BY | `cuts cost by 2x` | A ✓ |
| 10 | Q-ACHIEVES-NUM | `achieves 92%` | A ✓ (match stops before "accuracy"; line correct) |
| 11 | Q-NUM-COMP | `2x faster` | A ✓ |
| 12 | Q-NUM-COMP | `30% less` | A ✓ (stops before "memory"; line correct) |
| 13 | Q-ZERO | `zero downtime` | A ✓ |
| 14 | Q-ZERO | `near-zero latency` | A ✓ |
| 15 | Q-VERB-BY | `boosts throughput by 3x` | A ✓ |
| 17 | Q-VERB-BY | `cuts CI time by 60%` | A ✓ (multi-claim paragraph) |
| 17–18 | Q-VERB-BY | `reduces\nmemory by 25%` | A ✓ (soft-wrapped across physical lines; line 17 = start of match) |
| 18 | Q-ACHIEVES-NUM | `achieves 99.9%` | A ✓ |
| 42 | Q-VERB-BY | `improved by 25%` | A (reclassified; see §4) |
| 58 | Q-VERB-BY | `cuts cold starts by 50%` | A ✓ (paragraph inside a list item; correctly scanned because list-item paragraphs are PARAGRAPH contexts) |

Negatives that were **correctly not flagged**: Python 3.11, timeout=30, v2.4.10, 2026-03-15, 3 retries, `--workers 8`, `docs/evidence/report.md`, "under two minutes", "does not reduce cost by 40%" (negation window), "Assuming a 50% cache hit rate … improve by 2x" (hypothetical window), "aims to reduce p95 by 30%" (hypothetical), "60-70% visual weight", "128x128", "60% train / 40% held-out", "95% of incomplete investigations".

Code blocks were **correctly excluded**: the fenced block containing "reduces runtime by 80% and achieves 99% accuracy" and the indented block containing "reduces cost by 2x and has zero downtime" produced no candidates.

The Chinese paragraph ("本工具将处理时间缩短了 40%，准确率达到 92%") produced no candidate, as specified by the English-only product decision.

**Synthetic-set metrics (counting unit = claim span):**

- True positives: 13
- False positives: 0
- False negatives among A spans: 0 (the A list had 13 spans, all caught)
- Precision: 13/13 = 1.00
- Recall on A: 13/13 = 1.00

These numbers describe the synthetic fixture only and must not be read as real-world accuracy.

## 4. Boundary observations

1. **Passive constructions with a verb root.** "The system was improved by 25%" (synthetic L42) is flagged because `improved` is one of the Q-VERB-BY roots. The module docstring already calls out *passive without our verb roots* ("Build time is down 40%") as out-of-scope. Passive-with-verb-root matches are kept; this is consistent with the documented design and is not treated as a defect.
2. **Match span truncation.** `achieves 92%` and `30% less` stop at the number/unit rather than capturing the trailing noun ("accuracy", "memory"). This is intentional: C1 stores the matched span, not the full clause. Downstream E1 association uses `context_id`, not the match text, so truncation does not affect evidence linking.
3. **Soft-wrapped claims.** The "reduces\nmemory by 25%" span starts on line 17 and the unit is on line 18; `claim.line` reports 17 (where the match begins). This is the documented 1-based physical-line behavior and is adequate for locating the paragraph.
4. **List-item inner paragraphs.** "cuts cold starts by 50%" lives inside a Markdown list item. The parser exposes it as a PARAGRAPH context with `enclosing_list_item_id` set; C1 scans it once and does not also scan the list-item joined text, so no double-count.
5. **Rhetorical numbers.** Real docs contain phrases like "a million times", "billions a year" (skill-creator L298/L306). None match because there is no `%/x/times` unit attached to an effect verb; this is correct.

## 5. Suggested next improvements (NOT applied this phase)

1. **Broaden real-doc sampling.** The repo-diversity gap (2 vs. ≥5 repos) is the single biggest limitation. A future run should add marketing-style / product docs with genuine quantified claims to test recall under realistic false-positive pressure.
2. **Consider passive-with-verb-root as a deliberate pattern.** If product wants passive "X was reduced by 40%" counted as a candidate, it already works; if product wants it *excluded*, the Q-VERB-BY regex needs a subject/auxiliary guard. This is a product decision, not a bug.
3. **Capture trailing noun optionally.** Storing a slightly wider span ("achieves 92% accuracy") could make reports more readable, but it would not change E1/E2 semantics. Deferred.

## 6. Known limitations

- 17 redistributable real docs from 2 repos (13 Apache-2.0, 4 MIT). An earlier 22-doc collection included 5 Anthropic files that were later removed because their per-directory LICENSE.txt forbids redistribution; those 5 are historical-only and are not part of the shipped fixture. This corpus is heavy on procedural guidance and light on marketing-style quantified claims; real-world false-positive rate on product-marketing SKILL.md files is not measured.
- **Real-set precision and recall are not computed.** With 0 hand-annotated in-scope-positive spans and 0 C1 flags, denominators are zero; "0 false positives observed" is reported as an observation, not as a precision estimate.
- No network-dependent claims were reachable in this sample; URL association is not exercised by this eval (it belongs to E1, not C1).
- Ambiguous cases (D) were not needed: every numeric span and every qualitative candidate in the sample resolved cleanly to A, B, or C on manual review.
- Metrics are computed only on the synthetic set (13 A spans, 0 B flags); they describe that fixture only and must not be read as real-world accuracy.

## 7. Reproducing this evaluation

```powershell
# From project root (network was used only once, at sample-collection time):
py -3.12 scripts/run_c1_eval.py
# Output: per-doc claim list + tests/fixtures/c1_eval/c1_run.json
```

Pytest remains offline and is unaffected by these fixtures.
