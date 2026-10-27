"""End-to-end CLI tests for Phase 5B."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from skill_evidence_lint.cli import app

runner = CliRunner()


def _write_skill(root: Path, body: str, name: str = "SKILL.md") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / name
    p.write_text(body, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #
def test_clean_skill_dir_exit_zero(tmp_path: Path):
    _write_skill(tmp_path, "A short introduction.\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "Findings : 0" in result.output
    assert "No issues found" in result.output


def test_skill_md_path_directly(tmp_path: Path):
    p = _write_skill(tmp_path, "Hello.\n")
    result = runner.invoke(app, [str(p)])
    assert result.exit_code == 0
    assert str(p) in result.output


def test_other_markdown_file_rejected(tmp_path: Path):
    other = tmp_path / "notes.md"
    other.write_text("Hello.\n", encoding="utf-8")
    result = runner.invoke(app, [str(other)])
    assert result.exit_code == 2
    assert "SKILL.md" in result.output


def test_claim_with_existing_local_path_no_e1_no_e2(tmp_path: Path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.md").write_text("# bench", encoding="utf-8")
    _write_skill(
        tmp_path,
        "The tool reduces latency by 30% (see evidence/bench.md).\n",
    )
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=0" in result.output
    assert "E2=0" in result.output


def test_claim_with_url_no_e1_no_network(tmp_path: Path):
    _write_skill(tmp_path, "We improve accuracy by 15% (https://example.com/x).\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=0" in result.output
    assert "E2=0" in result.output


# --------------------------------------------------------------------------- #
# E1 / E2
# --------------------------------------------------------------------------- #
def test_claim_without_reference_emits_e1_exit_zero(tmp_path: Path):
    _write_skill(tmp_path, "We reduce cost by 10% with no reference.\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=1" in result.output
    assert "E2=0" in result.output


def test_command_only_does_not_clear_e1(tmp_path: Path):
    _write_skill(tmp_path, "We reduce cost by 10% (run `python bench.py`).\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=1" in result.output


def test_missing_local_path_emits_e2_exit_zero(tmp_path: Path):
    _write_skill(tmp_path, "We reduce cost by 5% (see evidence/nope.md).\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E2=1" in result.output


def test_both_e1_and_e2_reported(tmp_path: Path):
    body = (
        "Claim one reduces cost by 5% (see evidence/missing.md).\n"
        "\n"
        "Claim two improves speed by 20%.\n"
    )
    _write_skill(tmp_path, body)
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=1" in result.output
    assert "E2=1" in result.output


def test_adjacent_paragraph_ref_does_not_clear_e1(tmp_path: Path):
    body = (
        "We reduce cost by 5%.\n"
        "\n"
        "See evidence/bench.md.\n"
    )
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.md").write_text("ok", encoding="utf-8")
    _write_skill(tmp_path, body)
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    # Reference exists in a different paragraph -> E1 still raised.
    assert "E1=1" in result.output
    assert "E2=0" in result.output


def test_different_list_items_do_not_share_reference(tmp_path: Path):
    body = (
        "- Item A: reduces cost by 5%.\n"
        "- Item B: see evidence/bench.md.\n"
    )
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "bench.md").write_text("ok", encoding="utf-8")
    _write_skill(tmp_path, body)
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "E1=1" in result.output


def test_code_block_is_not_scanned(tmp_path: Path):
    body = (
        "Real claim: improves speed by 20%.\n"
        "\n"
        "```\n"
        "fake: reduces cost by 90% and evidence/fake.md\n"
        "```\n"
    )
    _write_skill(tmp_path, body)
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    # Only the real claim exists; code-block text is ignored.
    assert "Claims   : 1" in result.output
    assert "E1=1" in result.output
    assert "E2=0" in result.output


def test_chinese_claim_not_counted(tmp_path: Path):
    _write_skill(tmp_path, "该优化将处理时间减少了 40%。\n")
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0
    assert "Claims   : 0" in result.output


# --------------------------------------------------------------------------- #
# Skill root is SKILL.md's parent, not CWD
# --------------------------------------------------------------------------- #
def test_resolution_uses_skill_root_not_cwd(tmp_path: Path, monkeypatch):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "evidence").mkdir()
    (skill_dir / "evidence" / "ok.md").write_text("ok", encoding="utf-8")
    _write_skill(skill_dir, "We reduce cost by 5% (see evidence/ok.md).\n")

    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    result = runner.invoke(app, [str(skill_dir)])
    assert result.exit_code == 0
    assert "E1=0" in result.output
    assert "E2=0" in result.output


# --------------------------------------------------------------------------- #
# Input errors -> exit 2
# --------------------------------------------------------------------------- #
def test_missing_path_exit_two(tmp_path: Path):
    result = runner.invoke(app, [str(tmp_path / "nope")])
    assert result.exit_code == 2
    assert "not found" in result.output.lower()


def test_directory_without_skill_md_exit_two(tmp_path: Path):
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 2
    assert "SKILL.md" in result.output


# --------------------------------------------------------------------------- #
# Internal error -> exit 3 (via controlled mock)
# --------------------------------------------------------------------------- #
def test_internal_error_exit_two_or_three(tmp_path, monkeypatch):
    _write_skill(tmp_path, "Hello.\n")

    import skill_evidence_lint.runner as runner_mod

    def boom(_text):  # noqa: ANN001
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(runner_mod, "parse_text", boom)
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 3
    assert "internal error" in result.output.lower()
    assert "simulated internal failure" in result.output
    # Default: no full traceback dumped to stderr/output.
    assert "Traceback (most recent call last)" not in result.output
