"""Offline C1 evaluation runner (dev-only helper, NOT part of pytest).

This script reuses the real production parser and claim_extractor to scan the
downloaded real SKILL.md fixtures in tests/fixtures/c1_eval/real/. It writes a
JSON summary to tests/fixtures/c1_eval/c1_run.json which is then hand-annotated
into categories A/B/C/D in docs/c1-evaluation.md.

Run from project root:
    py -3.12 scripts/run_c1_eval.py

This script never downloads anything, never reads evidence file contents, and
never follows URLs. Network access for sample collection happened separately.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make src importable when running from a checkout without editable install.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_evidence_lint.claim_extractor import extract_candidate_claims  # noqa: E402
from skill_evidence_lint.parser import parse_text  # noqa: E402

REAL_DIR = ROOT / "tests" / "fixtures" / "c1_eval" / "real"
SYNTH_DIR = ROOT / "tests" / "fixtures" / "c1_eval" / "synthetic"
OUT = ROOT / "tests" / "fixtures" / "c1_eval" / "c1_run.json"


def _scan(files: list[Path], results: dict[str, object]) -> None:
    for path in sorted(files):
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        parsed = parse_text(text)
        claims = extract_candidate_claims(parsed.contexts)
        results[path.name] = {
            "paragraph_count": sum(
                1 for c in parsed.contexts if c.type.value == "paragraph"
            ),
            "diagnostics": list(parsed.diagnostics),
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "line": c.line,
                    "pattern_id": c.pattern_id,
                    "text": c.text,
                    "context_id": c.context.context_id,
                    "enclosing_list_item_id": c.context.enclosing_list_item_id,
                }
                for c in claims
            ],
        }
        print(f"\n=== {path.name} ({len(claims)} claims) ===")
        for c in claims:
            print(f"  L{c.line:>4}  [{c.pattern_id}]  {c.text}")


def main() -> int:
    results: dict[str, object] = {}
    print("--- REAL ---")
    _scan(list(REAL_DIR.glob("*.md")), results)
    print("\n--- SYNTHETIC ---")
    _scan(list(SYNTH_DIR.glob("*.md")), results)

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
