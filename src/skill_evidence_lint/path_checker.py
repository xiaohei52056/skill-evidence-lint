"""5A: E2 local evidence path safety and existence checks.

Only ``RefType.LOCAL_PATH`` references are checked. URLs are never fetched;
commands are not filesystem evidence.

Security model:

* The root directory is fixed to the directory that contains ``SKILL.md``.
  It is resolved to an absolute path once, up front; the process working
  directory is never used.
* Every referenced path is resolved with :meth:`Path.resolve`, which expands
  ``..`` segments and any symlinks. A reference is accepted only when the
  resolved path is ``root`` itself or is contained within ``root``.
  A symlink escaping the root therefore fails containment, just like ``..``.
* We only stat metadata. We never open, read, or execute the referenced file.
* Fail-safe: any OSError (permission denied, broken symlink, invalid bytes,
  etc.) becomes an E2 finding rather than crashing the whole run.

E2 is a normal finding, not a program error. It means the local reference
could not be resolved to an existing path inside the Skill root — it does not
judge whether any claim is true.
"""

from __future__ import annotations

from pathlib import Path

from .models import EvidenceReference, Finding, RefType, RuleID


def _is_within(root: Path, candidate: Path) -> bool:
    return candidate == root or candidate.is_relative_to(root)


def check_local_paths(
    references: list[EvidenceReference] | tuple[EvidenceReference, ...],
    skill_dir: str | Path,
) -> list[Finding]:
    """Check every LOCAL_PATH reference against ``skill_dir`` (the Skill root).

    Returns one E2 finding per reference that is missing, escapes the root,
    or cannot be resolved. References of type URL or COMMAND are ignored.
    """
    root = Path(skill_dir).resolve()
    findings: list[Finding] = []

    for ref in references:
        if ref.ref_type is not RefType.LOCAL_PATH:
            continue

        raw = ref.raw_path.strip()

        try:
            if not raw:
                raise ValueError("empty path")

            # ``root / raw`` makes absolute paths override root (by design):
            # an absolute reference is therefore outside the root unless it
            # itself equals the root.
            candidate = root / raw
            resolved = candidate.resolve()

            if not _is_within(root, resolved):
                findings.append(
                    _e2(ref, f"path '{raw}' escapes the Skill root directory")
                )
                continue

            if not resolved.exists():
                findings.append(
                    _e2(ref, f"referenced path '{raw}' does not exist")
                )
                continue

        except (OSError, ValueError) as exc:
            # Fail-safe: never let a single bad path crash the run.
            findings.append(
                _e2(ref, f"path '{raw}' could not be resolved: {exc}")
            )

    return findings


def _e2(ref: EvidenceReference, message: str) -> Finding:
    return Finding(
        rule_id=RuleID.E2,
        message=message,
        context=ref.context,
        claim_text=None,
        claim_id="",
        line=ref.line,
    )
