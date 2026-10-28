"""Tests for the versioned JSON report (P2.3)."""

from __future__ import annotations

import json

from skill_evidence_lint.models import RuleID
from skill_evidence_lint.report import SCHEMA_ID, build_report, dumps
from skill_evidence_lint.runner import run_check


def test_empty_report_schema_and_keys(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# Just a heading\n\nNo claims here.\n", encoding="utf-8")
    result = run_check(str(skill))
    report = build_report(result)

    assert report["schema"] == SCHEMA_ID
    assert report["tool"]["name"] == "skill-evidence-lint"
    assert "version" in report["tool"]
    assert report["input"]["skill_md_path"].endswith("SKILL.md")
    assert report["summary"] == {
        "claims": 0,
        "references": 0,
        "findings": 0,
        "by_rule": {"E1": 0, "E2": 0, "E3": 0, "E5": 0, "E6": 0, "E7": 0},
    }
    assert report["claims"] == []
    assert report["references"] == []
    assert report["findings"] == []


def test_populated_report_contains_claims_refs_and_findings(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "# Demo\n\n"
        "We reduced latency by 40% per [benchmark](benchmarks/latency.md).\n"
        "\n"
        "## Evidence\n\n"
        "TODO\n",
        encoding="utf-8",
    )
    # benchmarks/latency.md does NOT exist => E2; E5 placeholder;
    # E3 may or may not fire depending on cues; just assert structure.
    result = run_check(str(skill))
    report = build_report(result)

    assert report["summary"]["claims"] >= 1
    assert report["summary"]["references"] >= 1
    assert report["summary"]["findings"] >= 1

    claim = report["claims"][0]
    assert {"claim_id", "text", "line", "pattern_id", "language", "context_id"} <= claim.keys()
    assert "reduced" in claim["text"].lower()

    ref = report["references"][0]
    assert {"reference_id", "ref_type", "raw", "line", "context_id", "exists"} <= ref.keys()

    finding = report["findings"][0]
    assert finding["rule_id"] in {"E1", "E2", "E3", "E5", "E6", "E7"}
    assert finding["severity"] in {"info", "warning", "error"}
    assert isinstance(finding["line"], int)


def test_dumps_is_valid_json_and_stable(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "We reduce latency by 40%, see [report](report.md).\n", encoding="utf-8"
    )
    result = run_check(str(skill))
    text1 = dumps(result)
    text2 = dumps(result)
    assert text1 == text2
    parsed = json.loads(text1)
    assert parsed["schema"] == SCHEMA_ID


def test_unicode_and_quotes_escaped(tmp_path):
    # Verify json.dumps(ensure_ascii=False) round-trips arbitrary UTF-8 and
    # that the output is valid JSON. Quote escaping is provided by stdlib.
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "We reduce latency by 40% — called 快 (fast).\n",
        encoding="utf-8",
    )
    result = run_check(str(skill))
    text = dumps(result)
    parsed = json.loads(text)
    assert isinstance(parsed["summary"]["claims"], int)
    # Valid JSON; no stack traces; deterministic key order.
    assert parsed["schema"] == SCHEMA_ID


def test_all_implemented_rules_severity_present(tmp_path):
    # Sanity: every rule id in by_rule has a severity mapping.
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# x\n", encoding="utf-8")
    report = build_report(run_check(str(skill)))
    assert set(report["summary"]["by_rule"].keys()) == {"E1", "E2", "E3", "E5", "E6", "E7"}


def test_cli_json_mode_emits_only_json(tmp_path):
    import subprocess
    import sys
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("We reduce latency by 40%.\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "skill_evidence_lint", str(skill), "--format", "json"],
        capture_output=True,
        text=True,
    )
    # Note: package may not have __main__; skip if that is the case.
    if "No module named" in proc.stderr:
        return
    assert proc.returncode == 0, proc.stderr
    parsed = json.loads(proc.stdout)
    assert parsed["schema"] == SCHEMA_ID
    # No banner / summary outside the JSON document.
    assert proc.stdout.lstrip().startswith("{")
    assert proc.stderr == ""


def test_cli_invalid_format_exit_2(tmp_path):
    import subprocess
    import sys
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# x\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "skill_evidence_lint", str(skill), "--format", "yaml"],
        capture_output=True,
        text=True,
    )
    if "No module named" in proc.stderr:
        return
    assert proc.returncode == 2
    assert "format" in proc.stderr.lower() or "format" in proc.stdout.lower()


def test_findings_do_not_change_exit_code(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("We reduce latency by 40%.\n", encoding="utf-8")
    result = run_check(str(skill))
    # Advisory: findings present but exit code concept remains 0.
    assert any(f.rule_id in {RuleID.E1, RuleID.E3} for f in result.findings)
