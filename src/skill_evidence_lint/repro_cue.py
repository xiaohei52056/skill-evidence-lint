"""E3 — reproducibility-cue coverage for numeric effect claims.

E3 is a *warning* rule. For every numeric effect claim C1 detected, it asks:
does the claim's own Markdown context (same paragraph or enclosing list item)
contain at least one recognizable textual reproducibility cue — OR is a
fenced command block directly adjacent to the context with no intervening
paragraph, list item, or heading?

Three cue categories are recognized, all deterministic and regex-based:

1. **Command cue** — an inline code span whose first token is an allowlisted
   command *and* the command carries a positional argument (not just
   ``--version`` / ``--help``), OR a directly adjacent fenced block whose
   info tag is a shell language (``bash``, ``sh``, ``shell``, ``console``,
   ``python``, ``shell-session``) and whose first non-comment line starts with
   an allowlisted command.
2. **Input / dataset / configuration cue** — phrases such as
   ``on dataset X``, ``with input Y``, ``using configuration Z``.
3. **Metric-definition cue** — phrases such as ``measured as ...``,
   ``accuracy on ...``, ``pass rate``, ``success rate``.

If at least one cue category is present, E3 stays silent. If none is present,
E3 emits a warning. The warning means **"no recognizable reproducibility cue
was found in the local context"** — it does NOT mean the claim is false, that
no benchmark ran, or that the result is actually unreproducible.

Deliberate boundaries:

* A fenced block is only associated with a claim when it sits in the gap
  between the claim's context and the next paragraph/list item/heading. A
  fence under a different list item, or separated by another paragraph, does
  not count.
* Environment-only commands (``python --version``, ``node --help``) are
  filtered out: they do not reference a benchmark, script, or dataset.
* Arbitrary inline code that is not an allowlisted command does not count.
* No network access, no command execution, no LLM judgment.
"""

from __future__ import annotations

import re

from .models import CandidateClaim, Finding, MarkdownContext, RuleID
from .parser import FenceBlock

# --------------------------------------------------------------------------- #
# Command allowlist. First token of an inline code span or a fence line must
# match one of these.
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

# Fence info tags that indicate a shell / command block.
_SHELL_FENCE_INFO = frozenset(
    {"bash", "sh", "shell", "shell-session", "console", "zsh", "python", "py"}
)

# Flags that indicate an environment-only command with no positional target.
_ENV_FLAGS = frozenset(
    {"--version", "--help", "-V", "-v", "-h", "--env", "--info", "--version-all"}
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


def _command_has_positional(command_text: str) -> bool:
    """Return True if the command has something beyond env-only flags."""
    tokens = command_text.strip().split()
    if not tokens:
        return False
    # Drop the binary itself; remaining tokens should contain at least one
    # positional (not a pure flag).
    rest = tokens[1:]
    if not rest:
        return False
    return any(not tok.startswith("-") for tok in rest)


def _inline_command_cue(text: str) -> bool:
    for m in _BACKTICK.finditer(text):
        body = m.group(1).strip()
        if not body:
            continue
        first = body.split()[0].lower()
        if first in _ALLOWED_COMMANDS and _command_has_positional(body):
            return True
    return False


def _fence_command_cue(
    claim_context: MarkdownContext,
    fences: tuple[FenceBlock, ...],
    contexts: tuple[MarkdownContext, ...],
) -> bool:
    """Return True if a shell fence sits directly after the claim context.

    "Directly after" means the fence starts after the claim context ends, and
    before the next paragraph/list item starts. A fence separated by another
    context, or belonging to a different list item, does not count.
    """
    claim_end = claim_context.end_line
    # Next context (paragraph or list item) after the claim.
    next_start = None
    for c in contexts:
        if c.start_line > claim_end:
            if next_start is None or c.start_line < next_start:
                next_start = c.start_line

    for f in fences:
        if f.start_line <= claim_end:
            continue
        if next_start is not None and f.start_line >= next_start:
            continue
        # This fence sits in the gap between the claim and the next context.
        if f.info.lower() not in _SHELL_FENCE_INFO:
            continue
        for raw_line in f.text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("$"):
                continue
            first = line.split()[0].lower()
            if first in _ALLOWED_COMMANDS and _command_has_positional(line):
                return True
    return False


def has_repro_cues(
    context_text: str,
    *,
    fence_cue: bool = False,
) -> tuple[bool, bool, bool]:
    """Return ``(command_cue, input_cue, metric_cue)`` booleans for a context."""
    return (
        _inline_command_cue(context_text) or fence_cue,
        bool(_INPUT_CUE.search(context_text)),
        bool(_METRIC_CUE.search(context_text)),
    )


def check_repro_cues(
    claims: list[CandidateClaim] | tuple[CandidateClaim, ...],
    contexts: tuple[MarkdownContext, ...] | None = None,
    fences: tuple[FenceBlock, ...] = (),
) -> tuple[Finding, ...]:
    """Emit E3 warnings for numeric claims lacking all three cue categories."""
    ctx_tuple = contexts if contexts is not None else tuple(
        {c.context.context_id: c.context for c in claims}.values()
    )
    findings: list[Finding] = []
    for claim in claims:
        ctx: MarkdownContext = claim.context
        fence_cue = _fence_command_cue(ctx, fences, ctx_tuple)
        cmd, inp, metric = has_repro_cues(ctx.raw_text, fence_cue=fence_cue)
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
