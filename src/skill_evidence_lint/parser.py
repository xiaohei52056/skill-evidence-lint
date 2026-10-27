"""Markdown context parser.

Turns the text of a ``SKILL.md`` file into a list of structured
:class:`MarkdownContext` objects: one per paragraph, and one per list item.

Strictness rules (product decisions):

* Only a paragraph or a list item may later carry a claim/evidence link.
* Headings, fenced code blocks, indented code blocks, and YAML frontmatter
  are *not* turned into contexts.
* A paragraph directly inside a list item is linked to that list item via
  ``enclosing_list_item_id``; paragraphs inside a *nested* list item are
  linked to the nested item, never to its parent.
* Line numbers are 1-based physical line numbers of the original file
  (CRLF-safe: line endings are normalized before parsing).
* We never scan "nearby lines": association is only ever via these explicit
  context ids.

The walker deliberately uses markdown-it-py's block tokens (``map`` field)
rather than splitting on blank lines, and never invokes anything in the file.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .models import ContextType, MarkdownContext


@dataclass(frozen=True)
class ParseResult:
    """Outcome of parsing one Markdown document."""

    contexts: tuple[MarkdownContext, ...]
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    def paragraphs(self) -> list[MarkdownContext]:
        return [c for c in self.contexts if c.type is ContextType.PARAGRAPH]

    def list_items(self) -> list[MarkdownContext]:
        return [c for c in self.contexts if c.type is ContextType.LIST_ITEM]


@dataclass
class _OpenListItem:
    """Mutable accumulator for a list item being walked."""

    context_id: str
    start_line: int  # 1-based inclusive
    end_line: int  # 1-based inclusive
    prose_parts: list[str] = field(default_factory=list)


def _strip_frontmatter(text: str) -> tuple[int, str]:
    """Remove YAML frontmatter (``---`` ... ``---``) from the very top.

    Returns ``(line_offset, body)`` where ``line_offset`` is the number of
    physical lines consumed (0-based), so callers can map body token lines
    back to original 1-based line numbers.
    """
    lines = text.split("\n")
    if lines and lines[0].rstrip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].rstrip() == "---":
                consumed = idx + 1  # 0-based lines 0..idx inclusive
                body = "\n".join(lines[consumed:])
                return consumed, body
    return 0, text


def _to_1based(token_map: list[int] | None, offset: int) -> tuple[int, int]:
    """Convert a 0-based, end-exclusive token map to 1-based inclusive lines."""
    if token_map is None:
        return (0, 0)
    start0, end0 = token_map
    return start0 + offset + 1, end0 + offset


def parse_text(text: str) -> ParseResult:
    """Parse Markdown text into structured contexts.

    The input text may use CRLF; line endings are normalized first. An empty
    (or whitespace-only) document yields an empty context list.
    """
    diagnostics: list[str] = []

    # Normalize line endings so line numbers match physical lines 1:1.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    offset, body = _strip_frontmatter(normalized)

    md = MarkdownIt("commonmark")
    tokens: list[Token] = md.parse(body)

    contexts: list[MarkdownContext] = []
    stack: list[_OpenListItem] = []
    paragraph_counter = 0
    list_item_counter = 0
    in_heading = False

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        ttype = tok.type

        if ttype == "heading_open":
            in_heading = True
            i += 1
            continue

        if ttype == "heading_close":
            in_heading = False
            i += 1
            continue

        if ttype == "inline" and in_heading:
            # Heading text is not a context; skip silently.
            i += 1
            continue

        if ttype == "paragraph_open":
            # A paragraph is always: paragraph_open, inline, paragraph_close.
            inline = tokens[i + 1] if i + 1 < n else None
            if inline is None or inline.type != "inline":
                diagnostics.append(
                    f"paragraph_open at token {i} not followed by inline; skipped"
                )
                i += 1
                continue

            start_line, end_line = _to_1based(tok.map, offset)
            paragraph_counter += 1
            pid = f"p-{paragraph_counter}"
            enclosing = stack[-1].context_id if stack else None

            ctx = MarkdownContext(
                type=ContextType.PARAGRAPH,
                raw_text=inline.content,
                start_line=start_line,
                end_line=end_line,
                context_id=pid,
                enclosing_list_item_id=enclosing,
            )
            contexts.append(ctx)
            if stack:
                stack[-1].prose_parts.append(inline.content)
            i += 3
            continue

        if ttype in ("bullet_list_open", "ordered_list_open"):
            # Just descend; list_item_open pushes real frames.
            i += 1
            continue

        if ttype in ("bullet_list_close", "ordered_list_close", "paragraph_close"):
            i += 1
            continue

        if ttype == "list_item_open":
            start_line, end_line = _to_1based(tok.map, offset)
            list_item_counter += 1
            item = _OpenListItem(
                context_id=f"li-{list_item_counter}",
                start_line=start_line,
                end_line=end_line,
            )
            stack.append(item)
            i += 1
            continue

        if ttype == "list_item_close":
            if not stack:
                diagnostics.append("list_item_close without matching open; ignored")
                i += 1
                continue
            item = stack.pop()
            list_ctx = MarkdownContext(
                type=ContextType.LIST_ITEM,
                raw_text="\n\n".join(p.strip() for p in item.prose_parts if p.strip()),
                start_line=item.start_line,
                end_line=item.end_line,
                context_id=item.context_id,
                enclosing_list_item_id=None,
            )
            contexts.append(list_ctx)
            i += 1
            continue

        if ttype in ("fence", "code_block", "hr"):
            # Deliberately excluded from contexts.
            i += 1
            continue

        if ttype == "inline":
            # Standalone inline without paragraph_open (e.g. heading text).
            # We already skip headings; anything else is unexpected.
            diagnostics.append(f"unexpected inline token at {i}: {tok.content[:40]!r}")
            i += 1
            continue

        # Unknown block token: record rather than silently mis-parsing.
        diagnostics.append(f"unhandled token type {ttype!r}; skipped")
        i += 1

    if stack:
        diagnostics.append(
            "unclosed list item(s) at end of input: "
            + ", ".join(s.context_id for s in stack)
        )

    # Emit contexts in document order. List items are finalized at their
    # close token, which for nested items happens before the parent closes;
    # sorting by start line restores top-to-bottom order.
    contexts.sort(key=lambda c: (c.start_line, c.end_line, c.context_id))

    return ParseResult(contexts=tuple(contexts), diagnostics=tuple(diagnostics))
