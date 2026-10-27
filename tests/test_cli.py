"""Tests for the Typer CLI entry point."""

from typer.testing import CliRunner

from skill_evidence_lint.cli import app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "skill-evidence-lint" in result.output
    assert "skill_path" in result.output


def test_nonexistent_path_exits_two():
    result = runner.invoke(app, ["some/skill/dir"])
    assert result.exit_code == 2
    assert "not found" in result.output.lower()


def test_missing_path_is_rejected():
    # Missing required argument -> Typer exits with code 2.
    result = runner.invoke(app, [])
    assert result.exit_code == 2
