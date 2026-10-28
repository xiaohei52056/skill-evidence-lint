"""E4 evidence-stale tests (contract v1.0, A1-A34).

Each test builds a tiny synthetic Skill directory under tmp_path and runs
the full run_check() pipeline. We assert on the emitted findings and on
the JSON report where the contract requires it.
"""

from __future__ import annotations

import pytest

from skill_evidence_lint.models import RuleID
from skill_evidence_lint.report import build_report
from skill_evidence_lint.runner import run_check


def _skill(root, skill_md: str, files: dict[str, str] | None = None):
    """Write SKILL.md and optional evidence files; return root path."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(skill_md, encoding="utf-8")
    for name, content in (files or {}).items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def _e4_findings(result):
    return [f for f in result.findings if f.rule_id is RuleID.E4]


# ---------------------------------------------------------------------------
# A1-A3: basic comparison
# ---------------------------------------------------------------------------

def test_a1_stale_emits_finding_with_259_days(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [data](data.md).\n",
        {"data.md": "---\ndate: 2024-06-15\n---\n"},
    )
    result = run_check(str(skill))
    f = _e4_findings(result)
    assert len(f) == 1
    assert f[0].days_diff == 259
    assert f[0].evidence_date == "2024-06-15"
    assert f[0].skill_date == "2025-03-01"


def test_a2_same_date_no_finding(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [data](data.md).\n",
        {"data.md": "---\ndate: 2025-03-01\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a3_evidence_newer_no_finding(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [data](data.md).\n",
        {"data.md": "---\ndate: 2025-03-02\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


# ---------------------------------------------------------------------------
# A4-A6: G2 filename date and G3 content date
# ---------------------------------------------------------------------------

def test_a4_filename_date_g2(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](benchmark-2024-06-15-final.md).\n",
        {"benchmark-2024-06-15-final.md": "# report\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2024-06-15"


def test_a5_content_date_g3(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "# report\n\nLast updated: 2024-06-15\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1


def test_a6_g3_multiple_different_dates_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "# report\n\nDate: 2024-01-01\n\nLast updated: 2024-06-15\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


# ---------------------------------------------------------------------------
# A7-A11: skill date missing, invalid dates, placeholders, year bounds
# ---------------------------------------------------------------------------

def test_a7_skill_without_date_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ntitle: demo\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "---\ndate: 2024-06-15\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a8_invalid_calendar_date_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "---\ndate: 2025-02-30\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a9_placeholder_date_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "---\ndate: YYYY-MM-DD\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a10_future_date_no_finding_not_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "---\ndate: 2099-01-01\n---\n"},
    )
    # Future date parses fine; evidence_date > skill_date -> no finding.
    assert _e4_findings(run_check(str(skill))) == []


def test_a11_pre_2000_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [report](report.md).\n",
        {"report.md": "---\ndate: 1999-12-31\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


# ---------------------------------------------------------------------------
# A12-A15: extension, URL, multiple evidence, ordering
# ---------------------------------------------------------------------------

def test_a12_non_text_extension_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [img](report.png).\n",
        {"report.png": "binary-bytes"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a13_url_reference_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see <https://example.com/r>.\n",
    )
    # URL ref: E4 silent; E1 may fire but E4 must not.
    assert _e4_findings(run_check(str(skill))) == []


def test_a14_one_stale_one_date_less(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [a](a.md) and [b](b.md).\n",
        {
            "a.md": "---\ndate: 2024-06-15\n---\n",
            "b.md": "no date here\n",
        },
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_path.endswith("a.md")


def test_a15_two_stale_sorted_by_days_diff_desc(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [old](old.md) and [newer](newer.md).\n",
        {
            "old.md": "---\ndate: 2024-01-01\n---\n",
            "newer.md": "---\ndate: 2024-06-15\n---\n",
        },
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 2
    assert f[0].days_diff >= f[1].days_diff
    assert f[0].evidence_path.endswith("old.md")


# ---------------------------------------------------------------------------
# A16-A19: UTC normalization
# ---------------------------------------------------------------------------

def test_a16_utc_cross_day_plus8_early(tmp_path):
    # 2025-03-15 01:00+08:00 == 2025-03-14 17:00 UTC -> date 2025-03-14
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-15\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15T01:00:00+08:00\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2025-03-14"


def test_a17_utc_cross_day_plus8_late(tmp_path):
    # 2025-03-15 23:00+08:00 == 2025-03-15 15:00 UTC -> 2025-03-15
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-16\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15T23:00:00+08:00\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2025-03-15"


def test_a18_utc_cross_day_minus8_no_finding(tmp_path):
    # 2025-03-15 23:00-08:00 == 2025-03-16 07:00 UTC -> 2025-03-16
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-16\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15T23:00:00-08:00\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a19_naive_datetime_treated_as_utc(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-16\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15 10:30\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2025-03-15"


# ---------------------------------------------------------------------------
# A20-A21: fractional seconds, out-of-range tz
# ---------------------------------------------------------------------------

def test_a20_fractional_seconds_rejected(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15T10:30:00.123Z\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a21_out_of_range_tz_rejected(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2025-03-15T10:30:00+15:00\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


# ---------------------------------------------------------------------------
# A22-A24: source-group priority and no-fallback
# ---------------------------------------------------------------------------

def test_a22_g1b_multiple_different_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2024-06-15\nupdated: 2025-02-01\n---\n"},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a23_g1a_priority(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\nas_of: 2024-06-15\nlast_updated: 2025-02-01\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2024-06-15"


def test_a24_g1a_invalid_no_fallback(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\nas_of: not-a-date\ndate: 2024-06-15\n---\n"},
    )
    # as_of present but unparseable -> die, do NOT fall back to date.
    assert _e4_findings(run_check(str(skill))) == []


# ---------------------------------------------------------------------------
# A25-A27: symlink, size limit, encoding
# ---------------------------------------------------------------------------

def test_a25_symlink_escape_silent_skip(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](link.md).\n",
        encoding="utf-8",
    )
    outside = tmp_path / "outside.md"
    outside.write_text("---\ndate: 2024-06-15\n---\n", encoding="utf-8")
    try:
        (root / "link.md").symlink_to(outside)
    except OSError:
        pytest.skip("symlink not creatable in this environment")
    assert _e4_findings(run_check(str(root))) == []


def test_a26_file_over_1_mib_silent_skip(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2024-06-15\n---\n" + ("x" * (1024 * 1024 + 1))},
    )
    assert _e4_findings(run_check(str(skill))) == []


def test_a27_non_utf8_silent_skip(tmp_path):
    root = tmp_path / "s"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        encoding="utf-8",
    )
    # Write invalid UTF-8 bytes.
    (root / "r.md").write_bytes(b"\xff\xfe\xfd---\ndate: 2024-06-15\n---\n")
    assert _e4_findings(run_check(str(root))) == []


# ---------------------------------------------------------------------------
# A28-A29: dedup and wildcard
# ---------------------------------------------------------------------------

def test_a28_same_file_different_writings_dedup(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [a](./a.md) and [b](sub/../a.md).\n",
        {"a.md": "---\ndate: 2024-06-15\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1


def test_a29_wildcard_multi_match_e4_silent(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](reports/*.md).\n",
        {
            "reports/a.md": "---\ndate: 2024-06-15\n---\n",
            "reports/b.md": "---\ndate: 2024-01-01\n---\n",
        },
    )
    result = run_check(str(skill))
    # E4 silent; E7 should fire.
    assert _e4_findings(result) == []
    assert any(f.rule_id is RuleID.E7 for f in result.findings)


# ---------------------------------------------------------------------------
# A30-A31: JSON contract
# ---------------------------------------------------------------------------

def test_a30_json_by_rule_has_e4_zero(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%.\n",
    )
    report = build_report(run_check(str(skill)))
    assert report["summary"]["by_rule"]["E4"] == 0


def test_a31_e4_finding_has_exclusive_fields_others_do_not(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "---\ndate: 2024-06-15\n---\n"},
    )
    report = build_report(run_check(str(skill)))
    e4 = [f for f in report["findings"] if f["rule_id"] == "E4"]
    assert len(e4) == 1
    for k in ("evidence_path", "evidence_date", "skill_date", "days_diff"):
        assert k in e4[0]
    others = [f for f in report["findings"] if f["rule_id"] != "E4"]
    for f in others:
        assert "evidence_path" not in f
        assert "days_diff" not in f


# ---------------------------------------------------------------------------
# A32-A34: full datetime capture, skill fallback, E2/E4 mutual exclusion
# ---------------------------------------------------------------------------

def test_a32_g3_full_datetime_captured(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-16\n---\n\nWe reduce latency by 40%, "
        "see [r](r.md).\n",
        {"r.md": "# r\n\nLast updated: 2025-03-15 10:30:00Z\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].evidence_date == "2025-03-15"


def test_a33_skill_invalid_date_falls_back_to_updated(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-02-30\nupdated: 2025-03-01\n---\n\n"
        "We reduce latency by 40%, see [r](r.md).\n",
        {"r.md": "---\ndate: 2024-06-15\n---\n"},
    )
    f = _e4_findings(run_check(str(skill)))
    assert len(f) == 1
    assert f[0].skill_date == "2025-03-01"


def test_a34_e2_e4_mutual_exclusion(tmp_path):
    skill = _skill(
        tmp_path / "s",
        "---\ndate: 2025-03-01\n---\n\nWe reduce latency by 40%, "
        "see [r](missing.md).\n",
    )
    result = run_check(str(skill))
    assert any(f.rule_id is RuleID.E2 for f in result.findings)
    assert _e4_findings(result) == []
