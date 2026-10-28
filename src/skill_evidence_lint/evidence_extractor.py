"""4A: evidence-reference extractor.

Scans paragraph-type contexts (the same granular unit C1 uses) and records
three kinds of references:

* ``local_path`` — a relative file path or a bare filename with a common
  evidence extension (e.g. ``evidence/bench.md``, ``README.md``).
* ``url`` — an ``http(s)://`` URL. Syntax only: we never fetch it.
* ``command`` — backtick-wrapped inline code (e.g. ``python run.py``). A
  command is *not* a local evidence file; its ``ref_type`` marks it so later
  phases do not treat it as file existence evidence.

Conservatism rules:

* We scan only paragraph contexts, never the joined list-item text (that would
  duplicate references).
* Backtick spans are masked out of the text before path/URL scanning so a
  command like ``python run.py`` is not double-counted as a local path.
* Versions (``v1.2.3``), dates (``2024-05-01``), config values
  (``timeout=30``) are not paths: they lack a slash and a whitelisted extension.
* A reference being detected is NOT evidence that the file exists or that any
  claim is true. Existence checks (E2), path traversal, symlink and network
  checks are deliberately out of scope for this phase.
"""

from __future__ import annotations

import re

from .models import ContextType, EvidenceReference, MarkdownContext, RefType

# Inline code spans in the paragraph source.
_BACKTICK = re.compile(r"`([^`\n]+)`")

# http(s) URLs. We trim trailing sentence punctuation so "see x.md." does not
# swallow the period.
_URL = re.compile(r"https?://[^\s)<>]+", re.IGNORECASE)

# Local path: either contains a slash (relative path) or ends in a whitelisted
# evidence extension. We deliberately do NOT match bare words, bare numbers,
# versions or dates.
_PATH_EXT = (
    r"(?:md|markdown|json|ya?ml|txt|csv|tsv|log|pdf|png|jpe?g|svg|py|sh|toml|ini)"
)
_SEGMENT = r"[A-Za-z0-9._~*-]+"
_LOCAL_PATH = re.compile(
    r"(?<![\w/.)])"
    r"(?:\.{1,2}/)?" + _SEGMENT + r"(?:/" + _SEGMENT + r")*"
    r"(?:\." + _PATH_EXT + r")"
    r"(?![\w])",
    re.IGNORECASE,
)


def _match_line(ctx: MarkdownContext, offset_in_text: int) -> int:
    newlines_before = ctx.raw_text.count("\n", 0, offset_in_text)
    return ctx.start_line + newlines_before


def _mask(text: str, spans: list[tuple[int, int]]) -> str:
    """Replace given [start, end) spans with spaces (keeps offsets stable)."""
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def extract_evidence_references(
    contexts: list[MarkdownContext] | tuple[MarkdownContext, ...],
) -> list[EvidenceReference]:
    """Extract evidence references from parsed contexts.

    Only paragraph-type contexts are scanned; an empty input yields an empty list.
    """
    references: list[EvidenceReference] = []
    counter = 0

    for ctx in contexts:
        if ctx.type is not ContextType.PARAGRAPH:
            continue

        text = ctx.raw_text
        seen_in_ctx: set[str] = set()

        # 1) Backtick commands first; mask them so their contents are not
        #    scanned as paths/URLs.
        masked = text
        cmd_spans: list[tuple[int, int, str]] = []
        for m in _BACKTICK.finditer(text):
            cmd_text = m.group(1).strip()
            if not cmd_text:
                continue
            cmd_spans.append((m.start(), m.end(), cmd_text))

        masked = _mask(text, [(s, e) for s, e, _ in cmd_spans])

        for start, _end, cmd_text in cmd_spans:
            key = (RefType.COMMAND, cmd_text)
            if key in seen_in_ctx:
                continue
            seen_in_ctx.add(key)
            counter += 1
            references.append(
                EvidenceReference(
                    raw_path=cmd_text,
                    context=ctx,
                    reference_id=f"r-{counter}",
                    ref_type=RefType.COMMAND,
                    line=_match_line(ctx, start),
                )
            )

        # 2) URLs in the masked text.
        for m in _URL.finditer(masked):
            url = m.group(0).rstrip(".,;:!?)")
            key = (RefType.URL, url)
            if key in seen_in_ctx:
                continue
            seen_in_ctx.add(key)
            counter += 1
            references.append(
                EvidenceReference(
                    raw_path=url,
                    context=ctx,
                    reference_id=f"r-{counter}",
                    ref_type=RefType.URL,
                    line=_match_line(ctx, m.start()),
                )
            )

        # 3) Local paths in the remaining text.
        for m in _LOCAL_PATH.finditer(masked):
            path = m.group(0)
            key = (RefType.LOCAL_PATH, path)
            if key in seen_in_ctx:
                continue
            seen_in_ctx.add(key)
            counter += 1
            references.append(
                EvidenceReference(
                    raw_path=path,
                    context=ctx,
                    reference_id=f"r-{counter}",
                    ref_type=RefType.LOCAL_PATH,
                    line=_match_line(ctx, m.start()),
                )
            )

    return references
