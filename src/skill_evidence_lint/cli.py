"""Typer CLI entry point.

Exit-code contract (product decision):

* ``0`` — check completed, whether or not E1/E2 findings were reported.
* ``2`` — user input was invalid (missing path, missing SKILL.md, ...).
* ``3`` — an unexpected internal error occurred.
"""

from __future__ import annotations

import typer

from .models import RuleID
from .runner import InputError, RunResult, run_check

app = typer.Typer(
    name="skill-evidence-lint",
    help=(
        "Static lint for AI Skill SKILL.md files. Detects English effect "
        "claims and verifies in-context evidence references."
    ),
    add_completion=False,
)


def _print_report(result: RunResult) -> None:
    typer.echo("skill-evidence-lint")
    typer.echo(f"  SKILL.md : {result.skill_md_path}")
    typer.echo(f"  Claims   : {result.claim_count}")
    typer.echo(f"  Refs     : {result.reference_count}")
    typer.echo(f"  Findings : {len(result.findings)}")

    if not result.findings:
        typer.echo(
            "No issues found by currently implemented rules (C1/E1/E2/E3/E5/E6/E7)."
        )
    else:
        for f in result.findings:
            typer.echo(f"  {f.rule_id} (line {f.line}): {f.message}")

    e1 = result.count_for(RuleID.E1)
    e2 = result.count_for(RuleID.E2)
    e3 = result.count_for(RuleID.E3)
    e5 = result.count_for(RuleID.E5)
    e6 = result.count_for(RuleID.E6)
    e7 = result.count_for(RuleID.E7)
    typer.echo(
        f"Summary: E1={e1} E2={e2} E3={e3} E5={e5} E6={e6} E7={e7}. "
        "Findings are reports, not failures."
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    skill_path: str = typer.Argument(
        ...,
        help=(
            "Path to a Skill directory (must contain SKILL.md), or directly "
            "to a SKILL.md file."
        ),
    ),
) -> None:
    """Check a Skill directory for evidence-backed English claims (E1/E2)."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        result = run_check(skill_path)
    except InputError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort guard
        # Concise summary only; no full traceback by default. Exit code 3.
        typer.echo(f"internal error: {exc}", err=True)
        raise typer.Exit(code=3) from exc

    _print_report(result)
    # Findings never cause a non-zero exit.
    raise typer.Exit(code=0)


if __name__ == "__main__":  # pragma: no cover
    app()
