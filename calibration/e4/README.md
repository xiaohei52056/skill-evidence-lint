# E4 Calibration Set

This directory holds the E4 `evidence-stale` calibration fixtures required
by `docs/e4-contract.md` §11.2.

## How to run

```powershell
py -3.12 calibration\e4\run_calibration.py
```

The script (re)generates every sample under `samples/`, runs the current
E4 implementation against each, and prints a table of expected vs. actual
E4 findings. It is offline and read-only with respect to the skill content
— it never executes commands inside the samples.

## Sample provenance

All 24 samples under `samples/` are **hand-authored, redacted fixtures**
modeled after real-world SKILL.md patterns. They are not copied from any
public repository and contain no personal data, tokens, or internal paths.

This is a deliberate limitation: at the time of P2.6c we did not have a
license-cleared corpus of 20–30 real public SKILL.md files to import. The
fixtures cover the contract's decision matrix (positive, negative, and
out-of-scope paths) so that regressions are caught, but they do **not**
constitute the "real public Skill" calibration the contract envisions. A
future pass that imports real-world skills with explicit license clearance
is tracked as P2.6c-followup.

## Labels

| Sid | Kind | Why |
|---|---|---|
| P01 | positive | G1b evidence date older than skill date |
| P02 | positive | G1a `as_of` wins over G1b `updated`; evidence older |
| P03 | positive | G2 filename date older |
| P04 | positive | G3 labeled content date older |
| P05 | positive | Skill `date` invalid, falls back to `updated` |
| P06 | positive | Two stale evidence files for one claim (both fire) |
| P07 | positive | ISO datetime with `Z` normalizes to UTC calendar day |
| P08 | positive | Single-match `*` wildcard resolves to one file |
| N01 | negative | Evidence date equals skill date |
| N02 | negative | Evidence date newer than skill date |
| N03 | negative | G1b group ambiguity (`date` + `updated` differ) → silent |
| N04 | negative | Placeholder date `YYYY-MM-DD` → silent |
| N05 | negative | No date anywhere in evidence → silent |
| O01 | out-of-scope | Missing local path → E2 owns; E4 silent |
| O02 | out-of-scope | URL reference → E4 silent |
| O03 | out-of-scope | Multi-match wildcard → E7 owns; E4 silent |
| O04 | out-of-scope | `.png` extension not in allowlist → silent |
| O05 | out-of-scope | No skill frontmatter date → silent |
| O06 | out-of-scope | Pre-2000 evidence date → silent |
| O07 | out-of-scope | Fractional seconds → silent |
| O08 | out-of-scope | Tz offset `+15:00` outside ±14:00 → silent |
| O09 | out-of-scope | Calendar-impossible date `2025-02-30` → silent |
| O10 | out-of-scope | Evidence file > 1 MiB → silent |
| O11 | out-of-scope | Non-UTF-8 evidence content → silent |

## Latest calibration run

```
total samples : 24
positives     : 8 (expected E4 >= 1)
  true positives : 8
  false negatives: 0
negatives     : 5 (expected E4 == 0)
  false positives: 0
out-of-scope  : 11 (expected E4 == 0)
  oos violations : 0
```

Contract §11.2 thresholds:

- 20–30 samples: **24** ✅ (but see provenance caveat — fixtures, not
  imported real-world Skills).
- 0 false positives: **0** ✅
- ≥5 expected positives detected: **8** ✅

## Known gap

The "real public Skill" corpus requirement (license-cleared samples from
published agent skills) has **not** been satisfied. The current fixtures
prove the rule behaves per contract on representative structures, but
real-world messiness (varied YAML dialects, unexpected date field names,
mixed frontmatter styles) is not yet exercised. Do not claim production-grade
calibration until a real corpus is imported and labeled.

## P2.6c.1 — Public corpus acquisition attempt (2026-10-29)

We attempted to acquire a license-cleared public Skill corpus. Results:

### Candidates inspected

| Source | License | Verdict |
|---|---|---|
| `anthropics/skills` (the canonical public skill repo) | Frontmatter says "see LICENSE.txt"; root LICENSE returned 404; README says "many skills open source (Apache 2.0)" but `docx/pdf/pptx/xlsx` are "source-available, not open source" | **License unverified** — could not pin a commit SHA (GitHub API rate-limited for this IP); no root LICENSE; per-skill LICENSE.txt files not individually fetched within this session. |

### Structural finding

Spot-checked `brand-guidelines`, `mcp-builder`, `skill-creator`:

- Frontmatter contains only `name` + `description` (+ sometimes a
  `license` pointer). **No `date`/`updated`/`as_of`/`version_date` fields.**
- Body is instructional prose ("Create an MCP server…", "Apply brand
  colors…"), not quantitative claims ("we cut latency by 40%") paired
  with local evidence files.
- No `.md`/`.txt` evidence files referenced by local path with date
  metadata.

These skills are **structurally out-of-scope for E4**: even with a
valid license, they would produce zero E1 claims and zero E4 findings.
They are useful as "real-world negative/out-of-scope" examples but do
not provide the positive cases the contract requires (≥5 expected
positives detected).

### Why we stopped here

1. **License uncertainty**: root LICENSE 404, API rate-limited, per-skill
   LICENSE.txt not fetched. We cannot redistribute content until the
   license is pinned and verified.
2. **Structural mismatch**: the dominant public skill ecosystem today
   (2026-10) consists of instruction/tutorial skills, not evidence-backed
   technical claims. E4 was designed for a narrower SKILL.md shape
   (quantitative claim + local benchmark/report reference). The public
   corpus does not yet exercise that shape at scale.
3. **No fabrication**: we will not pad the count with 20 skills that are
   all out-of-scope, nor copy content under an unverified license.

### Recommendation for P2.6c-followup

A real positive-case corpus will likely come from one of:

- User's own evidence-backed SKILL.md files (the original target use
  case), licensed under the project's own license.
- Technical report / benchmark / research repos that publish results
  as SKILL.md files with dated evidence subfolders (does not yet exist
  as a recognizable ecosystem).
- A future point at which anthropics/skills or a community repo starts
  publishing evidence-backed skills with date frontmatter.

Until then, the 24-fixture decision-matrix set remains the regression
suite; the contract §11.2 "real public Skill" threshold is **not met**.

## P2.6c.3 — Public corpus run (2026-10-29)

We fetched 23 candidate public SKILL.md files from the provided list and
ran the current E4 implementation against each (as a standalone skill
directory with only the SKILL.md present). Results:

- 22 of 23 URLs returned valid SKILL.md content (A11 NVIDIA path 404'd).
- 0 skills produced any E1 claim ("by N%" pattern) — all 22 are
  instruction/tutorial prose, not quantitative claims backed by dated
  evidence files.
- 0 E4 findings across all 22 samples (expected: with no claims, there
  is nothing for E4 to associate).
- E2 fired on missing referenced files (we only downloaded SKILL.md,
  not the referenced `references/*.md` sub-files). This is correct
  behavior; E2 owns missing paths and E4 stays silent.
- 6 samples had a date-like frontmatter field (`last_updated`): A01–A05
  (PracticalSwan, `2026-09-08`) and A12 (Confluent, `2026-07-09`). Even
  for these, no numeric claim exists, so E4 correctly produces nothing.

### Calibration counts

| Bucket | Count |
|---|---|
| Candidate links provided | 23 |
| Valid SKILL.md files fetched | 22 |
| License explicitly verified | 0 (all "partial" or "unknown"; GitHub API rate-limited, no pinned SHA) |
| expected-e4 (labeled before running) | 0 |
| expected-no-e4 | 0 |
| out-of-scope | 22 |
| ambiguous | 0 |
| TP | n/a (no expected positives) |
| FP | 0 |
| FN | n/a |

### Contract §11.2 threshold check

- 20–30 real samples: **22 fetched** (count met, but license unverified
  for redistribution; files analyzed read-only, not committed).
- 0 false positives: **0** ✅.
- ≥5 expected positives detected: **0** ❌ — the public skill ecosystem
  does not contain evidence-backed quantitative claims in SKILL.md files.

### Verdict

**CALIBRATION INCOMPLETE.** The public corpus confirms E4 produces no
false positives on real-world instruction skills (good — 0 FP across 22
real files), but it provides zero positive cases. The rule's positive
path is only exercised by the hand-authored fixtures. To meet the ≥5
positive threshold, we need user-supplied SKILL.md files that actually
make quantitative claims against dated evidence — i.e. the original
target use case of this linter.
