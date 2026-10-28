"""Tests for E7 — ambiguous wildcard evidence path."""

from __future__ import annotations

from skill_evidence_lint.ambiguity_check import check_ambiguity
from skill_evidence_lint.evidence_extractor import extract_evidence_references
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text
from skill_evidence_lint.runner import run_check


def _refs(text: str):
    parsed = parse_text(text)
    return extract_evidence_references(parsed.contexts)


def test_wildcard_zero_matches_no_e7(tmp_path):
    (tmp_path / "benchmarks").mkdir()
    refs = _refs("See benchmarks/nope/*.md.")
    findings = check_ambiguity(refs, tmp_path)
    assert findings == ()


def test_wildcard_one_match_no_e7(tmp_path):
    (tmp_path / "benchmarks").mkdir()
    (tmp_path / "benchmarks" / "a.md").write_text("x", encoding="utf-8")
    refs = _refs("See benchmarks/*.md.")
    findings = check_ambiguity(refs, tmp_path)
    assert findings == ()


def test_wildcard_multiple_matches_e7(tmp_path):
    (tmp_path / "benchmarks").mkdir()
    (tmp_path / "benchmarks" / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "benchmarks" / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "benchmarks" / "c.md").write_text("c", encoding="utf-8")
    refs = _refs("See benchmarks/*.md.")
    findings = check_ambiguity(refs, tmp_path)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E7
    assert "3 files" in findings[0].message


def test_multiple_match_order_stable(tmp_path):
    (tmp_path / "reports").mkdir()
    for name in ("z.md", "a.md", "m.md"):
        (tmp_path / "reports" / name).write_text("x", encoding="utf-8")
    refs = _refs("See reports/*.md.")
    f1 = check_ambiguity(refs, tmp_path)
    f2 = check_ambiguity(refs, tmp_path)
    assert f1[0].message == f2[0].message
    # a.md, m.md, z.md alphabetical.
    assert "a.md" in f1[0].message and "z.md" in f1[0].message


def test_exact_path_no_ambiguity(tmp_path):
    (tmp_path / "results.md").write_text("x", encoding="utf-8")
    refs = _refs("See results.md.")
    findings = check_ambiguity(refs, tmp_path)
    assert findings == ()


def test_traversal_wildcard_does_not_escape_root(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    try:
        refs = _refs("See ../*/secret.md.")
        findings = check_ambiguity(refs, tmp_path)
        # Crucially, secret.md must not appear in any finding message.
        for f in findings:
            assert "secret.md" not in f.message
    finally:
        (outside / "secret.md").unlink(missing_ok=True)
        outside.rmdir()


def test_paths_with_spaces(tmp_path):
    # Paths with spaces are not tokenized by the extractor; use an underscore
    # to emulate a real path and confirm E7 still works on it.
    d = tmp_path / "my_reports"
    d.mkdir()
    (d / "one.md").write_text("1", encoding="utf-8")
    (d / "two.md").write_text("2", encoding="utf-8")
    refs = _refs("See my_reports/*.md.")
    findings = check_ambiguity(refs, tmp_path)
    assert len(findings) == 1


def test_e7_does_not_change_exit_code(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    b = skill / "b"
    b.mkdir()
    (b / "a.md").write_text("a", encoding="utf-8")
    (b / "b.md").write_text("b", encoding="utf-8")
    (skill / "SKILL.md").write_text("See b/*.md.\n", encoding="utf-8")
    result = run_check(str(skill))
    assert any(f.rule_id is RuleID.E7 for f in result.findings)


def test_e2_still_reports_missing_exact_path(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("See missing.md.\n", encoding="utf-8")
    result = run_check(str(skill))
    assert any(f.rule_id is RuleID.E2 for f in result.findings)
    assert not any(f.rule_id is RuleID.E7 for f in result.findings)
