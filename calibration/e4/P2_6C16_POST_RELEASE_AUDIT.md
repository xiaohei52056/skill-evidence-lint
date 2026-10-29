# P2.6c.16 — Post-release Audit

**Date:** 2026-10-29
**Audited commit:** `21866083497ba5bb6b1aed6ed6801f7b4e78c9a8` (main)
**Tag:** `v0.1.0` (annotated, tag object `b74cf146b4111a6d14fe142af727125c3078cf37`)
**PyPI:** https://pypi.org/project/skill-evidence-lint/0.1.0/

---

## 1. Verified facts

| Item | Result |
|---|---|
| Local branch | `main`, clean, HEAD `2186608` |
| Remote main | `2186608` (matches) |
| `v0.1.0` tag on origin | `b74cf14` → annotated tag → commit `2186608` |
| PR #1 | merged (merge commit `2186608`) |
| PyPI package 0.1.0 | exists, installable from PyPI |
| Wheel/sdist on PyPI | both uploaded (64 KB wheel, 82 KB sdist) |
| Runtime deps installed | `typer`, `markdown-it-py`, `pyyaml` (all pulled by pip) |
| CLI entry point | `skill-evidence-lint.exe` registered and runs |
| `--help` | works, documents `--format text/json` |
| Text output on valid skill | exit 0 |
| `--format json` output | exit 0, schema `skill-evidence-lint.report.v1`, `summary.by_rule` contains E1–E7 |
| Bad path | exit 2 (InputError) |
| CI (latest run on `2186608`) | all 4 required jobs success |

Isolated-venv install verification (not source dir):
```
C:\Users\ccb\AppData\Local\Temp\sel_audit_venv\Scripts\python.exe -m pip install skill-evidence-lint==0.1.0
→ Successfully installed ... skill-evidence-lint-0.1.0 ... pyyaml-6.0.3 ...
```

## 2. CI matrix — intentional scope

`.github/workflows/tests.yml` defines a 3×2 matrix but explicitly
**excludes** `macos-latest / py3.11` and `windows-latest / py3.11` with
the comment "Keep the matrix focused". Effective 4 jobs:

| Job | Status (latest run on main) |
|---|---|
| ubuntu-latest / py3.11 | success |
| ubuntu-latest / py3.12 | success |
| macos-latest / py3.12 | success |
| windows-latest / py3.12 | success |

This is a deliberate, documented scope. No change needed. README's
"Python 3.11+" and cross-platform claim are consistent with this matrix
(3.11 is covered on Linux; macOS/Windows on 3.12).

## 3. Findings

### BLOCKER
None. The published wheel/sdist is functional: install, CLI, JSON
schema, exit codes, and dependencies all verified from PyPI.

### WARNING — GitHub Release body is stale (not a package defect)

The existing GitHub Release v0.1.0 (published 2026-10-27, *before* the
phase-2 merge) contains:

- "**Not yet published to PyPI.** Install from source" — **now false**.
- Only lists checks C1, E1, E2 — **omits E3, E4, E5, E6, E7** that are
  actually in the v0.1.0 wheel.
- Dependencies listed as `typer`, `markdown-it-py` — **omits `pyyaml`**
  (which the wheel requires at runtime for frontmatter parsing).
- Does not mention JSON report output.

This is a GitHub-page issue only; the PyPI package itself is correct.
No tool available in this runtime can update an existing GitHub Release
body (no `update_release` MCP; `gh` CLI not installed). The corrected
body text is provided below for the maintainer to paste via the GitHub
web UI.

### NOTE

- E4 real-world positive calibration remains incomplete (0 real
  expected-e4 across 29 public SKILL.md files). This is disclosed in
  CHANGELOG; not a blocker for initial release.
- 3 symlink tests skip on local Windows (WinError 1314 permission);
  the windows-latest CI job runs as `runner` and either passes or
  skips without failing.
- CHANGELOG/README use em-dashes and arrows correctly in UTF-8; the
  earlier console mojibake was a PowerShell code-page display artifact,
  not a file-encoding defect.

## 4. Corrected GitHub Release body (paste into web UI)

```
## skill-evidence-lint v0.1.0

First public release. Static linter for `SKILL.md` files used by AI
agents. Install from PyPI:

    pip install skill-evidence-lint

### Checks

- **C1** — candidate English effect-claim extraction
  (`Q-VERB-BY`, `Q-ACHIEVES-NUM`, `Q-NUM-COMP`, `Q-ZERO`).
- **E1** — strict same-paragraph / same-list-item evidence association.
- **E2** — local path safety and existence checks (no URL fetching).
- **E3** — numeric claims without adjacent reproducibility cues
  (command / input / metric).
- **E4** — evidence-stale: compares evidence file dates against the
  Skill baseline date (claim-scoped; see `docs/e4-contract.md`).
- **E5** — empty `## Evidence` / `## Benchmark` / `## Results` /
  `## Evaluation` sections.
- **E6** — malformed or placeholder URLs (offline; no network calls).
- **E7** — ambiguous local path references (offline).

Output: human-readable text (default) or `--format json` with schema
`skill-evidence-lint.report.v1`.

### Exit codes

- `0` — check completed. Findings are reports, not failures.
- `2` — user input error.
- `3` — unexpected internal error.

### Runtime

Python 3.11+. Dependencies: `typer`, `markdown-it-py`, `pyyaml`.

### Calibration disclosure

E4 was validated on 24 hand-authored synthetic fixtures
(8 TP / 0 FP / 0 FN). Real-world evidence-backed Skills are rare in the
current public corpus; 29 public SKILL.md files inspected were out of
scope, so E4 has **zero real-world positive samples** to date. E4
flags staleness, not truth.
```

## 5. Local quality gate (this run, on `main` @ `2186608`)

```
pytest:   215 passed, 3 skipped (Windows symlink WinError 1314)
ruff:     All checks passed!
sdist:    skill_evidence_lint-0.1.0.tar.gz built
wheel:    skill_evidence_lint-0.1.0-py3-none-any.whl built
twine check: both PASSED
```

## 6. Decision: no v0.1.1

The published v0.1.0 wheel/sdist is functional and correctly packaged.
The only defect (stale GitHub Release body) lives on the GitHub page,
not in the distribution. Pushing a 0.1.1 solely to fix release notes
would be unnecessary churn.

**Recommended action:** update the GitHub Release body via the web UI
using the text in §4. No code change, no tag, no PyPI re-upload.

## 7. Items left unverified

- GitHub Release body could not be edited programmatically (no tool).
- PyPI "Files" tab hash not recomputed from disk (twine upload already
  computed and server-validated SHA256).
