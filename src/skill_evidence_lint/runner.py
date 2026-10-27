"""End-to-end check pipeline (Phase 5B).

This module wires together the already-tested building blocks:

    resolve SKILL.md  ->  parse_text  ->  extract claims (C1)
                     ->  extract evidence references
                     ->  associate_evidence  (E1)
                     ->  check_local_paths    (E2)
                     ->  merged, sorted findings

It deliberately contains no new lint logic: it only orchestrates the existing
modules and maps user-facing problems to :class:`InputError`. The CLI layer
turns that error into exit code 2 and any other unexpected exception into
exit code 3. Findings themselves never change the exit code (CI reports,
never blocks).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .claim_extractor import extract_candidate_claims
from .evidence_association import associate_evidence
from .evidence_extractor import extract_evidence_references
from .models import Finding, RuleID
from .parser import parse_text
from .path_checker import check_local_paths


class InputError(Exception):
    """Raised when the user-supplied path cannot be turned into a SKILL.md."""


@dataclass(frozen=True)
class RunResult:
    """The deterministic outcome of a successful check run."""

    skill_md_path: str
    claim_count: int
    reference_count: int
    findings: tuple[Finding, ...]

    def count_for(self, rule_id: RuleID) -> int:
        return sum(1 for f in self.findings if f.rule_id is rule_id)


def resolve_skill_md(skill_path: str) -> Path:
    """Locate the SKILL.md file to check.

    Convention (contract):

    * If ``skill_path`` is an existing directory, look for ``SKILL.md`` inside.
    * If ``skill_path`` is an existing file, its basename must be exactly
      ``SKILL.md`` so arbitrary Markdown files are not silently treated as
      Skill manifests.
    * Anything else (missing path, directory without SKILL.md, file not
      named SKILL.md, permission problems) raises :class:`InputError`.
    """
    if not skill_path or not skill_path.strip():
        raise InputError("no path provided")

    candidate = Path(skill_path).expanduser()

    if not candidate.exists():
        raise InputError(f"path not found: {skill_path}")

    if candidate.is_dir():
        target = candidate / "SKILL.md"
        if not target.is_file():
            raise InputError(
                f"directory {skill_path!r} does not contain SKILL.md"
            )
        return target

    if candidate.is_file():
        if candidate.name != "SKILL.md":
            raise InputError(
                f"expected a file named SKILL.md, got {candidate.name!r}"
            )
        return candidate

    raise InputError(f"not a directory or regular file: {skill_path}")


def run_check(skill_path: str) -> RunResult:
    """Run the full pipeline. ``InputError`` is raised for bad input."""
    skill_md = resolve_skill_md(skill_path)
    skill_dir = skill_md.parent.resolve()

    # Read text as UTF-8. Unicode/OS errors here are unexpected environment
    # problems and propagate to the CLI (mapped to exit code 3).
    text = skill_md.read_text(encoding="utf-8")

    parsed = parse_text(text)
    claims = extract_candidate_claims(parsed.contexts)
    references = extract_evidence_references(parsed.contexts)

    association = associate_evidence(claims, references)
    e2_findings = check_local_paths(references, skill_dir)

    findings = list(association.findings) + list(e2_findings)
    # Deterministic order: line, rule id, then message for stability.
    findings.sort(key=lambda f: (f.line, str(f.rule_id), f.message))

    return RunResult(
        skill_md_path=str(skill_md),
        claim_count=len(claims),
        reference_count=len(references),
        findings=tuple(findings),
    )
