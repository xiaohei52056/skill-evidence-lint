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
published agent skills) has not been satisfied. The current fixtures prove
the rule behaves per contract on representative structures, but real-world
messiness (varied YAML dialects, unexpected date field names, mixed
frontmatter styles) is not yet exercised. Do not claim production-grade
calibration until a real corpus is imported and labeled.
