"""Generate E4 calibration samples and run the linter against each.

This script is idempotent: it (re)writes every sample under
calibration/e4/samples/, runs run_check() on each, and prints a table of
expected vs. actual E4 findings. It does NOT execute anything inside the
samples; it only reads SKILL.md / evidence text.

Labels are human-authored in LABELS below per the frozen contract v1.0.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"

sys.path.insert(0, str(ROOT.parents[1] / "src"))

from skill_evidence_lint.models import RuleID
from skill_evidence_lint.runner import run_check


@dataclass
class Sample:
    sid: str
    kind: str          # "positive" | "negative" | "out-of-scope"
    reason: str
    skill_md: str
    files: dict[str, str]


# ---------------------------------------------------------------------------
# 24 samples. Each is a realistic multi-section SKILL.md with one or more
# numeric claims linked to local evidence. Labels follow the frozen contract.
# ---------------------------------------------------------------------------

SAMPLES_DATA: list[Sample] = [
    # ---- Positive E4 cases (evidence date < skill date) -------------------
    Sample(
        "P01", "positive",
        "G1b date on evidence older than skill date",
        "---\ndate: 2025-06-01\n---\n\nWe cut p95 latency by 30% — see [bench](bench.md).\n",
        {"bench.md": "---\ndate: 2024-01-15\n---\n# Bench\n"},
    ),
    Sample(
        "P02", "positive",
        "G1a as_of wins; evidence older",
        "---\ndate: 2025-06-01\n---\n\nWe reduced error rate by 40% — see [report](metrics/report.md).\n",
        {"metrics/report.md": "---\nas_of: 2024-11-01\nupdated: 2025-05-01\n---\n# R\n"},
    ),
    Sample(
        "P03", "positive",
        "G2 filename date, older",
        "---\ndate: 2025-06-01\n---\n\nWe cut bundle size by 18% — see [build](builds/release-2024-09-10-notes.md).\n",
        {"builds/release-2024-09-10-notes.md": "# notes\nNo frontmatter.\n"},
    ),
    Sample(
        "P04", "positive",
        "G3 labeled content date, older",
        "---\ndate: 2025-06-01\n---\n\nWe cut test coverage misses by 22% — see [cov](coverage.md).\n",
        {"coverage.md": "# Coverage report\n\nLast updated: 2024-03-22\n"},
    ),
    Sample(
        "P05", "positive",
        "Skill date uses updated: (date field invalid, fallback)",
        "---\ndate: not-a-date\nupdated: 2025-06-01\n---\n\nWe cut cold start by 40% — see [cold](cold.md).\n",
        {"cold.md": "---\ndate: 2024-12-01\n---\n"},
    ),
    Sample(
        "P06", "positive",
        "Two stale evidence files for one claim, both fire",
        "---\ndate: 2025-06-01\n---\n\nWe cut cost by 25% — see [a](a.md) and [b](b.md).\n",
        {
            "a.md": "---\ndate: 2024-01-01\n---\n",
            "b.md": "---\ndate: 2024-09-01\n---\n",
        },
    ),
    Sample(
        "P07", "positive",
        "ISO datetime with Z tz, normalizes to UTC calendar day",
        "---\ndate: 2025-06-01\n---\n\nWe cut memory by 12% — see [mem](mem.md).\n",
        {"mem.md": "---\ndate: 2024-06-15T23:00:00Z\n---\n"},
    ),
    Sample(
        "P08", "positive",
        "Single-match wildcard reference uses resolved file",
        "---\ndate: 2025-06-01\n---\n\nWe cut flake rate by 50% — see [logs](logs/2024-08-*.md).\n",
        {"logs/2024-08-01.md": "---\ndate: 2024-08-01\n---\n"},
    ),

    # ---- Negative E4 cases (evidence newer/same, no finding expected) -----
    Sample(
        "N01", "negative",
        "Evidence date equals skill date",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2025-06-01\n---\n"},
    ),
    Sample(
        "N02", "negative",
        "Evidence date newer than skill date",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2025-07-01\n---\n"},
    ),
    Sample(
        "N03", "negative",
        "G1b group ambiguity (two different dates) -> silent, no finding",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2024-01-01\nupdated: 2024-05-01\n---\n"},
    ),
    Sample(
        "N04", "negative",
        "Placeholder date (YYYY-MM-DD) -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: YYYY-MM-DD\n---\n"},
    ),
    Sample(
        "N05", "negative",
        "Evidence file has no date anywhere -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "# no date here at all\n"},
    ),

    # ---- Out-of-scope (contract requires silent skip; not a true neg) ----
    Sample(
        "O01", "out-of-scope",
        "Missing local path -> E2 owns it; E4 silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](missing.md).\n",
        {},
    ),
    Sample(
        "O02", "out-of-scope",
        "URL reference -> E4 silent (E1/E6 may fire)",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see <https://example.com/b>.\n",
        {},
    ),
    Sample(
        "O03", "out-of-scope",
        "Wildcard multi-match -> E7 owns ambiguity; E4 silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [r](runs/*.md).\n",
        {
            "runs/a.md": "---\ndate: 2024-01-01\n---\n",
            "runs/b.md": "---\ndate: 2024-05-01\n---\n",
        },
    ),
    Sample(
        "O04", "out-of-scope",
        "Non-text extension (.png) -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [img](chart.png).\n",
        {"chart.png": "binary"},
    ),
    Sample(
        "O05", "out-of-scope",
        "No skill frontmatter date -> silent",
        "---\ntitle: demo\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2024-01-01\n---\n"},
    ),
    Sample(
        "O06", "out-of-scope",
        "Pre-2000 evidence date -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 1999-12-31\n---\n"},
    ),
    Sample(
        "O07", "out-of-scope",
        "Fractional seconds -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2024-06-15T10:30:00.123Z\n---\n"},
    ),
    Sample(
        "O08", "out-of-scope",
        "Out-of-range tz (+15:00) -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2024-06-15T10:30:00+15:00\n---\n"},
    ),
    Sample(
        "O09", "out-of-scope",
        "Calendar-impossible date (2025-02-30) -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2025-02-30\n---\n"},
    ),
    Sample(
        "O10", "out-of-scope",
        "Evidence file over 1 MiB -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        {"b.md": "---\ndate: 2024-01-01\n---\n" + ("x" * (1024 * 1024 + 10))},
    ),
    Sample(
        "O11", "out-of-scope",
        "Non-UTF-8 content -> silent",
        "---\ndate: 2025-06-01\n---\n\nWe cut latency by 10% — see [b](b.md).\n",
        None,
    ),
]


def _materialize() -> None:
    if SAMPLES.exists():
        shutil.rmtree(SAMPLES)
    SAMPLES.mkdir(parents=True)
    for s in SAMPLES_DATA:
        d = SAMPLES / s.sid
        d.mkdir()
        (d / "SKILL.md").write_text(s.skill_md, encoding="utf-8")
        for name, content in (s.files or {}).items():
            p = d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        if s.sid == "O11":
            (d / "b.md").write_bytes(b"\xff\xfe\xfd---\ndate: 2024-01-01\n---\n")


def _run() -> list[dict]:
    rows = []
    for s in SAMPLES_DATA:
        d = SAMPLES / s.sid
        result = run_check(str(d))
        e4 = [f for f in result.findings if f.rule_id is RuleID.E4]
        rows.append({
            "sid": s.sid,
            "kind": s.kind,
            "reason": s.reason,
            "e4_count": len(e4),
            "e4_days": [f.days_diff for f in e4],
        })
    return rows


def main() -> int:
    _materialize()
    rows = _run()

    pos = [r for r in rows if r["kind"] == "positive"]
    neg = [r for r in rows if r["kind"] == "negative"]
    oos = [r for r in rows if r["kind"] == "out-of-scope"]

    tp = sum(1 for r in pos if r["e4_count"] >= 1)
    fn = sum(1 for r in pos if r["e4_count"] == 0)
    fp = sum(1 for r in neg if r["e4_count"] >= 1)
    # Out-of-scope: E4 must be silent (0 findings). Count violations.
    oos_violations = [r for r in oos if r["e4_count"] >= 1]

    print(f"{'sid':5} {'kind':13} {'e4':3} {'days':18} reason")
    for r in rows:
        print(f"{r['sid']:5} {r['kind']:13} {r['e4_count']:<3} {str(r['e4_days']):18} {r['reason']}")

    print()
    print(f"total samples : {len(rows)}")
    print(f"positives     : {len(pos)} (expected E4 >= 1)")
    print(f"  true positives : {tp}")
    print(f"  false negatives: {fn}")
    print(f"negatives     : {len(neg)} (expected E4 == 0)")
    print(f"  false positives: {fp}")
    print(f"out-of-scope  : {len(oos)} (expected E4 == 0)")
    print(f"  oos violations : {len(oos_violations)}")

    (SAMPLES / "_results.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
