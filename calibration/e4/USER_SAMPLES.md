# User-Provided Real Skill Intake

This document describes how to contribute real SKILL.md samples for E4
calibration. No samples have been provided yet — this file establishes
the intake process so that when you (the user) have samples, they can be
added consistently.

## What we need

Between 20–30 real SKILL.md files that you have the right to test against
the linter. Ideal samples include:

- A `SKILL.md` with a parseable date baseline in its frontmatter
  (`date`, `updated`, `last_modified`, or `version_date`).
- At least one quantitative claim (e.g. "we cut latency by 30%") linked
  to a local evidence file (a relative `.md`/`.txt`/`.json` path).
- Evidence files whose declared dates (frontmatter, filename, or
  labeled content line) you can identify.

Aim for diversity: some samples where evidence is older than the skill
date (expected E4 finding), some where it is equal/newer (expected no
E4), and some where E4 should silently skip (missing path, ambiguous
dates, oversize files, etc.).

## Privacy and authorization checklist

Before contributing any sample:

1. **Do you have the right to store this file in this repo?**
   - If it is your own work (or your employer's work under an open
     license), state that explicitly.
   - If it is from a third-party public repo, we need: repo URL,
     pinned commit SHA, license name, and LICENSE file location.
   - If it is private/proprietary, keep it local. We can run the linter
     against it without committing it, but do not paste it here.
2. **Strip secrets.** Remove API keys, tokens, internal hostnames,
   personal names, email addresses, and absolute private paths
   (`C:\Users\you\...`, `/home/you/...`).
3. **Do not assume public = redistributable.** A file being viewable on
   GitHub does not grant us the right to copy it into this repository.

## How to contribute

Option A — local-only run (no commit):
1. Place your sample directory somewhere on disk (e.g. `D:\my-skills\foo\`).
2. Run: `py -3.12 -m skill_evidence_lint --format json D:\my-skills\foo`
3. Paste the JSON output here (after redacting anything sensitive).
4. Tell us your expected label (expected-e4 / expected-no-e4 /
   out-of-scope) and why.

Option B — committed sample (after license confirmation):
1. Create a directory `calibration/e4/real/<your-skill-id>/`.
2. Drop the `SKILL.md` and referenced evidence files in it, redacted.
3. Add a row to `calibration/e4/manifest.csv` with the source, pinned
   SHA, license, and your label.
4. Run `py -3.12 calibration\e4\run_calibration.py` and confirm the
   actual output matches your label.

## Labels (per frozen contract v1.0)

| Label | Meaning |
|---|---|
| `expected-e4` | All preconditions met; evidence date < skill date; linter should emit one E4 finding. |
| `expected-no-e4` | All preconditions met; evidence date >= skill date; no E4 finding. |
| `out-of-scope` | Contract requires silent skip (missing path, ambiguous date, oversize, non-UTF-8, URL ref, etc.). Not counted as a true negative. |
| `ambiguous` | Contract does not uniquely decide; we flag it and propose a contract v1.1 note rather than forcing a label. |

## Current status

- **Real samples contributed: 0.**
- The 24 fixtures under `calibration/e4/samples/` are hand-authored
  decision-matrix tests, not real skills. They remain the regression
  suite but do not count toward the §11.2 "real skill" threshold.
- Until real samples with confirmed authorization are provided, the
  calibration state is **CALIBRATION BLOCKED — awaiting user input**.
