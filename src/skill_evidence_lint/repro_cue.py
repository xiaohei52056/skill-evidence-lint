"""E3 — reproducibility-cue coverage for numeric effect claims.

E3 is a *warning* rule. For every numeric effect claim C1 detected, it asks:
does the claim's own Markdown context (same paragraph or enclosing list item)
contain at least one recognizable textual reproducibility cue?

Three cue categories are recognized, all deterministic and regex-based:

1. **Command cue** — an inline code span (backtick-wrapped) whose first
   whitespace-separated token is an allowlisted command (``npm``, ``python``,
   ``node``, ``go``, ``cargo``, ``bash``, ...). Detection only; the command is
   never executed.
2. **Input / dataset / configuration cue** — phrases such as
   ``on dataset X``, ``with input Y``, ``using configuration Z``.
3. **Metric-definition cue** — phrases such as ``measured as ...``,
   ``accuracy on ...``, ``pass rate``, ``success rate``.

If at least one cue category is present, E3 stays silent. If none is present,
E3 emits a warning. The warning means **"no recognizable reproducibility cue
was found in the local context"** — it does NOT mean the claim is false, that
no benchmark ran, or that the result is actually unreproducible.

Deliberate boundaries:

* Fenced code blocks are not scanned here. They are block-level siblings, not
  members of a paragraph/list-item context, so associating them with a claim
  would require a separate heuristic. This is documented as a known gap.
* Arbitrary inline code that is not an allowlisted command (e.g. ``foo``) does
  not count.
* A cue in a neighboring paragraph or list item does not count.
* No network access, no command execution, no LLM judgment.
"""

from __future__ import annotations

import re

from .models import CandidateClaim, Finding, MarkdownContext, RuleID

# --------------------------------------------------------------------------- #
# Command allowlist. First token of an inline code span must match one of these.
# --------------------------------------------------------------------------- #
_ALLOWED_COMMANDS = frozenset(
    {
        "npm",
        "npx",
        "node",
        "pnpm",
        "yarn",
        "python",
        "python3",
        "py",
        "pip",
        "pip3",
        "go",
        "cargo",
        "rustc",
        "bash",
        "sh",
        "zsh",
        "make",
        "pytest",
        "tox",
        "docker",
        "uv",
    }
)

# Inline code spans.
_BACKTICK = re.compile(r"`([^`\n]+)`")

# Input / dataset / configuration cues.
_INPUT_CUE = re.compile(
    r"\b(?:on|using|with)\s+"
    r"(?:the\s+)?"
    r"(?:dataset|benchmark|input|configuration|config|workload|corpus)\b"
    r"\s+[A-Za-z0-9_./-]+",
    re.IGNORECASE,
)

# Metric-definition cues.
_METRIC_CUE = re.compile(
    r"\b(?:measured\s+(?:as|on|using|with)"
    r"|defined\s+as"
    r"|metric\s+(?:is|:|=)"
    r"|(?:pass|success|accuracy|coverage|latency)\s+rate"
    r"|accuracy\s+on"
    r"|on\s+(?:the\s+)?(?:pass|success)\s+rate"
    r")\b",
    re.IGNORECASE,
)


def _has_command_cue(text: str) -> bool:
    for m in _BACKTICK.finditer(text):
        first = m.group(1).strip().split()[0].lower() if m.group(1).strip() else ""
        if first in _ALLOWED_COMMANDS:
            return True
    return False


def has_repro_cues(context_text: str) -> tuple[bool, bool, bool]:
    """Return ``(command_cue, input_cue, metric_cue)`` booleans for a context."""
    return (
        _has_command_cue(context_text),
        bool(_INPUT_CUE.search(context_text)),
        bool(_METRIC_CUE.search(context_text)),
    )


def check_repro_cues(
    claims: list[CandidateClaim] | tuple[CandidateClaim, ...],
) -> tuple[Finding, ...]:
    """Emit E3 warnings for numeric claims lacking all three cue categories."""
    findings: list[Finding] = []
    for claim in claims:
        ctx: MarkdownContext = claim.context
        cmd, inp, metric = has_repro_cues(ctx.raw_text)
        if cmd or inp or metric:
            continue
        missing = []
        if not cmd:
            missing.append("command")
        if not inp:
            missing.append("input/dataset/config")
        if not metric:
            missing.append("metric-definition")
        message = (
            "No reproducibility cue in the same paragraph or list item "
            f"(missing: {', '.join(missing)}). This is a coverage observation, "
            "not a judgment that the claim is false or unreproducible."
        )
        findings.append(
            Finding(
                rule_id=RuleID.E3,
                message=message,
                context=ctx,
                claim_text=claim.text,
                claim_id=claim.claim_id,
                line=claim.line,
            )
        )
    return tuple(findings)
