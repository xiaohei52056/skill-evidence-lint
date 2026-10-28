"""E7 — ambiguous evidence path (offline, root-confined glob).

E7 only fires for local path references that contain a ``*`` wildcard. It
resolves the pattern against the Skill root using stdlib :meth:`Path.glob`
(no subprocess, no shell) and reports an info finding when **more than
one safe, in-root match** exists.

Security model (reuses E2's root confinement):

* The pattern is resolved relative to the Skill root.
* Every candidate match is ``resolve()``d and must be contained in the
  resolved root (same containment test E2 uses). Matches that escape via
  ``..`` or a symlink outside the root are discarded, not followed.
* If zero safe matches exist, E7 stays silent and E2 reports the missing
  path. If exactly one safe match exists, the reference is unambiguous.
* Result ordering is stable (sorted by resolved relative path).
* No file contents are read; only metadata / directory listing.

Supported wildcard syntax: only ``*`` within individual path segments (e.g.
``benchmarks/*.md``, ``reports/v*/summary.json``). The contract explicitly
states that ``?`` and ``**`` are **not** special: they must be treated as
literal characters. Because :meth:`Path.glob` would otherwise interpret
``?`` as a single-character wildcard and ``**`` as recursive matching,
patterns containing either are handled conservatively — no glob expansion
is performed, so E7 stays silent and the normal E2 existence check
applies.
"""

from __future__ import annotations

from pathlib import Path

from .models import EvidenceReference, Finding, RefType, RuleID


def _is_supported_wildcard(pattern: str) -> bool:
    """Return True only if the pattern uses '*' within segments and no other glob magic."""
    if "*" not in pattern:
        return False
    # ? and ** are explicitly out of contract; do not let Path.glob interpret them.
    if "?" in pattern or "**" in pattern:
        return False
    return True


def _safe_matches(root: Path, pattern: str) -> list[Path]:
    """Return sorted safe, in-root matches for a glob pattern under root."""
    if not _is_supported_wildcard(pattern):
        return []
    root_resolved = root.resolve()
    safe: list[Path] = []
    try:
        for candidate in root_resolved.glob(pattern):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved == root_resolved or resolved.is_relative_to(root_resolved):
                safe.append(resolved)
    except (OSError, ValueError):
        return []
    safe.sort()
    return safe


def check_ambiguity(
    references: list[EvidenceReference] | tuple[EvidenceReference, ...],
    skill_dir: str | Path,
) -> tuple[Finding, ...]:
    """Emit E7 info findings for wildcard references that match >1 in-root file."""
    root = Path(skill_dir)
    findings: list[Finding] = []
    for ref in references:
        if ref.ref_type is not RefType.LOCAL_PATH:
            continue
        raw = ref.raw_path.strip()
        if "*" not in raw or not _is_supported_wildcard(raw):
            # No wildcard, or unsupported wildcard syntax (?, **): E7 stays
            # silent; E2 reports existence/root-confinement normally.
            continue
        matches = _safe_matches(root, raw)
        if len(matches) <= 1:
            continue
        # Stable, short display: paths relative to root.
        try:
            rel = [str(m.relative_to(root.resolve())).replace("\\", "/") for m in matches]
        except ValueError:
            rel = [str(m) for m in matches]
        findings.append(
            Finding(
                rule_id=RuleID.E7,
                message=(
                    f"Wildcard reference {raw!r} matches {len(matches)} files "
                    "inside the Skill root; pick one explicitly. Matches: "
                    + ", ".join(rel[:5])
                    + ("..." if len(rel) > 5 else "")
                    + "."
                ),
                context=ref.context,
                claim_text=None,
                claim_id="",
                line=ref.line,
            )
        )
    return tuple(findings)
