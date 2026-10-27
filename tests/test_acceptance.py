"""Phase 6 v0.1 acceptance suite.

Exercises the real pipeline (``run_check``) against hand-written Skill
fixtures in a temporary directory. Each test maps to one acceptance case
(A–J) so the coverage is explicit in the report. No network, no real paths.
"""

from __future__ import annotations

from pathlib import Path

from skill_evidence_lint.models import RuleID
from skill_evidence_lint.runner import run_check


def write_skill(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / "SKILL.md"
    p.write_text(body, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# A. Clean Skill: no claims, no findings.
# --------------------------------------------------------------------------- #
def test_a_clean_skill(tmp_path: Path):
    write_skill(tmp_path, "A short introduction.\n")
    result = run_check(str(tmp_path))
    assert result.claim_count == 0
    assert result.reference_count == 0
    assert result.findings == ()


# --------------------------------------------------------------------------- #
# B. Claim + same-paragraph local path that exists: no E1, no E2.
# --------------------------------------------------------------------------- #
def test_b_claim_with_existing_local_path(tmp_path: Path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.md").write_text("ok", encoding="utf-8")
    write_skill(tmp_path, "We reduce cost by 10% (see evidence/bench.md).\n")
    result = run_check(str(tmp_path))
    assert result.claim_count == 1
    assert result.count_for(RuleID.E1) == 0
    assert result.count_for(RuleID.E2) == 0


# --------------------------------------------------------------------------- #
# C. Claim + same-paragraph URL: no E1, no network.
# --------------------------------------------------------------------------- #
def test_c_claim_with_url(tmp_path: Path):
    write_skill(tmp_path, "We improve accuracy by 15% (https://example.com/x).\n")
    result = run_check(str(tmp_path))
    assert result.count_for(RuleID.E1) == 0
    assert result.count_for(RuleID.E2) == 0


# --------------------------------------------------------------------------- #
# D. Claim + backtick command only: E1 raised.
# --------------------------------------------------------------------------- #
def test_d_command_only_still_emits_e1(tmp_path: Path):
    write_skill(tmp_path, "We reduce cost by 10% (run `python bench.py`).\n")
    result = run_check(str(tmp_path))
    assert result.count_for(RuleID.E1) == 1
    assert result.count_for(RuleID.E2) == 0


# --------------------------------------------------------------------------- #
# E. Reference in adjacent paragraph: E1 still raised.
# --------------------------------------------------------------------------- #
def test_e_adjacent_paragraph_ref_does_not_clear_e1(tmp_path: Path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.md").write_text("ok", encoding="utf-8")
    write_skill(
        tmp_path,
        "We reduce cost by 10%.\n\nSee evidence/bench.md.\n",
    )
    result = run_check(str(tmp_path))
    assert result.count_for(RuleID.E1) == 1
    assert result.count_for(RuleID.E2) == 0


# --------------------------------------------------------------------------- #
# F. Both E1 and E2 in one Skill.
# --------------------------------------------------------------------------- #
def test_f_e1_and_e2_together(tmp_path: Path):
    write_skill(
        tmp_path,
        "We reduce cost by 5% (see evidence/missing.md).\n\n"
        "We improve speed by 20%.\n",
    )
    result = run_check(str(tmp_path))
    assert result.count_for(RuleID.E1) == 1
    assert result.count_for(RuleID.E2) == 1
    # Deterministic ordering: line asc, then rule id.
    lines = [(f.line, str(f.rule_id)) for f in result.findings]
    assert lines == sorted(lines)


# --------------------------------------------------------------------------- #
# G. Local path escaping the Skill root: E2.
# --------------------------------------------------------------------------- #
def test_g_path_outside_root_emits_e2(tmp_path: Path):
    write_skill(tmp_path, "See ../escape.md.\n")
    result = run_check(str(tmp_path))
    assert result.count_for(RuleID.E2) == 1


# --------------------------------------------------------------------------- #
# H. Numbers that are versions / dates / instructions are not C1 claims.
# --------------------------------------------------------------------------- #
def test_h_version_date_instruction_not_claims(tmp_path: Path):
    write_skill(
        tmp_path,
        "Requires Python 3.11, released 2024-05-01. Run build with timeout=30.\n",
    )
    result = run_check(str(tmp_path))
    assert result.claim_count == 0
    assert result.findings == ()


# --------------------------------------------------------------------------- #
# I. Code block examples are not scanned as claims or references.
# --------------------------------------------------------------------------- #
def test_i_code_block_not_scanned(tmp_path: Path):
    write_skill(
        tmp_path,
        "Real claim: improves speed by 20%.\n\n"
        "```\n"
        "fake: reduces cost by 90% (evidence/fake.md)\n"
        "```\n",
    )
    result = run_check(str(tmp_path))
    assert result.claim_count == 1  # only the real claim
    assert result.reference_count == 0  # code block excluded
    assert result.count_for(RuleID.E1) == 1


# --------------------------------------------------------------------------- #
# J. Chinese claims do not enter the English C1 denominator.
# --------------------------------------------------------------------------- #
def test_j_chinese_claim_not_counted(tmp_path: Path):
    write_skill(tmp_path, "该优化将处理时间减少了 40%，准确率提升 15%。\n")
    result = run_check(str(tmp_path))
    assert result.claim_count == 0
    assert result.findings == ()


# --------------------------------------------------------------------------- #
# E1 message wording must not overclaim.
# --------------------------------------------------------------------------- #
def test_e1_message_is_coverage_observation(tmp_path: Path):
    write_skill(tmp_path, "We reduce cost by 10%.\n")
    result = run_check(str(tmp_path))
    e1 = result.findings[0]
    assert e1.rule_id is RuleID.E1
    assert "coverage observation" in e1.message.lower()
    assert "not a judgment" in e1.message.lower()
