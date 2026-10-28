"""Tests for E5 — empty evidence section."""

from __future__ import annotations

from skill_evidence_lint.evidence_section import check_sections
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text


def _e5_lines(findings):
    return [f.line for f in findings if f.rule_id is RuleID.E5]


def _e5_titles(findings):
    return [f.message.split("'")[1] for f in findings if f.rule_id is RuleID.E5]


def test_empty_evidence_section():
    text = "# Intro\n\n## Evidence\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert _e5_titles(findings) == ["Evidence"]


def test_empty_benchmark_results_evaluation():
    for title in ("Evidence", "Benchmark", "Results", "Evaluation"):
        text = f"# Intro\n\n## {title}\n"
        parsed = parse_text(text)
        findings = check_sections(parsed.sections)
        assert _e5_titles(findings) == [title], title


def test_case_insensitive_heading():
    text = "# Intro\n\n## evidence\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert _e5_titles(findings) == ["evidence"]


def test_each_placeholder():
    for ph in ("TODO", "TBD", "N/A", "coming soon", "Add evidence here"):
        text = f"# Intro\n\n## Evidence\n\n{ph}\n"
        parsed = parse_text(text)
        findings = check_sections(parsed.sections)
        assert _e5_titles(findings) == ["Evidence"], ph


def test_section_with_prose_not_flagged():
    text = (
        "# Intro\n\n## Evidence\n\n"
        "We ran the benchmark on 1000 samples and observed a 40% improvement.\n"
    )
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert findings == ()


def test_section_with_local_path_not_flagged():
    text = (
        "# Intro\n\n## Evidence\n\n"
        "See [benchmark](results/benchmark.md).\n"
    )
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert findings == ()


def test_section_followed_by_another_heading():
    # Evidence body is empty; next heading terminates it.
    text = "# Intro\n\n## Evidence\n\n## Next\n\nSome prose.\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert _e5_titles(findings) == ["Evidence"]


def test_heading_inside_fence_not_flagged():
    text = (
        "# Intro\n\n"
        "```markdown\n"
        "## Evidence\n"
        "```\n"
    )
    parsed = parse_text(text)
    # The fenced block is captured as a fence, not a section.
    assert all(s.title != "Evidence" for s in parsed.sections)
    findings = check_sections(parsed.sections)
    assert findings == ()


def test_unrelated_heading_not_flagged():
    text = (
        "# Intro\n\n## Evidence and metrics\n\nSome prose.\n\n## Performance\n\nx.\n"
    )
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert findings == ()


def test_multiple_empty_sections():
    text = "# Intro\n\n## Evidence\n\n## Benchmark\n\n## Results\n\n## Evaluation\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    assert sorted(_e5_titles(findings)) == [
        "Benchmark",
        "Evaluation",
        "Evidence",
        "Results",
    ]


def test_subsection_does_not_make_parent_empty():
    # Parent ## Evidence followed by ### Benchmark is NOT empty: the parent's
    # body includes its subsection. Only the placeholder subsection flags.
    text = "# Intro\n\n## Evidence\n\n### Benchmark\n\nTODO\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    titles = _e5_titles(findings)
    assert "Benchmark" in titles
    assert "Evidence" not in titles


def test_deterministic_ordering_by_line():
    text = "# Intro\n\n## Results\n\n## Evidence\n"
    parsed = parse_text(text)
    findings = check_sections(parsed.sections)
    lines = _e5_lines(findings)
    assert lines == sorted(lines)
