"""E5 — empty evidence section.

Recognizes ``## Evidence``, ``## Benchmark``, ``## Results``, and
``## Evaluation`` headings (case-insensitive on the heading text, but the
heading must be exactly one of these words — no "Evidence and metrics" or
"Performance results" variants).

A recognized section is flagged as E5 when:

* its body contains no non-whitespace content at all, or
* its body, after stripping whitespace and Markdown decoration, is exactly
  one of a small explicit placeholder tokens (``TODO``, ``TBD``, ``N/A``,
  ``coming soon``, ``add evidence here``).

Anything else — a paragraph with a local path or URL, a list, a fenced
code block, a sentence of prose — is treated as non-empty and clears E5.

E5 is a deterministic, read-only check. It does not open referenced files,
fetch URLs, or judge whether the evidence is sufficient or truthful.
"""

from __future__ import annotations

from .models import ContextType, Finding, MarkdownContext, RuleID
from .parser import Section

# Exact heading titles that count as evidence sections. Lowercase.
_RECOGNIZED = frozenset(
    {"evidence", "benchmark", "results", "evaluation"}
)

# Exact placeholder bodies (case-insensitive, after stripping Markdown
# emphasis/list markers).
_PLACEHOLDERS = frozenset(
    {
        "todo",
        "tbd",
        "n/a",
        "na",
        "coming soon",
        "add evidence here",
        "add benchmark here",
        "add results here",
    }
)


def _normalize_body(body: str) -> str:
    """Strip Markdown decoration so placeholders match consistently."""
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Strip leading list markers and emphasis wrappers.
        for marker in ("- ", "* ", "+ ", "1. ", "> ", "### ", "## ", "# "):
            if line.startswith(marker):
                line = line[len(marker) :].strip()
        # Strip surrounding emphasis / backticks.
        line = line.strip("*_`[]()")
        if line:
            out.append(line)
    return " ".join(out).strip()


def check_sections(sections: tuple[Section, ...]) -> tuple[Finding, ...]:
    """Emit E5 warnings for empty or placeholder-only evidence sections."""
    findings: list[Finding] = []
    for sec in sections:
        if sec.title.lower() not in _RECOGNIZED:
            continue
        normalized = _normalize_body(sec.body_text)
        if normalized == "":
            reason = "section has no content"
        elif normalized.lower() in _PLACEHOLDERS:
            reason = f"section body is a placeholder ({normalized!r})"
        else:
            continue

        ctx = MarkdownContext(
            type=ContextType.PARAGRAPH,
            raw_text=sec.title,
            start_line=sec.start_line,
            end_line=sec.start_line,
            context_id=f"section-{sec.start_line}",
        )
        findings.append(
            Finding(
                rule_id=RuleID.E5,
                message=(
                    f"Evidence section '{sec.title}' is empty "
                    f"({reason}). This is a coverage observation, not a "
                    "judgment that evidence is missing or insufficient."
                ),
                context=ctx,
                claim_text=None,
                claim_id="",
                line=sec.start_line,
            )
        )
    return tuple(findings)
