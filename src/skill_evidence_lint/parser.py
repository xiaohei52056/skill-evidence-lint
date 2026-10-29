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
class FenceBlock:
    """A fenced code block outside the paragraph/list-item context model.

    E3 uses these to recognize commands that are directly adjacent to a claim
    (no intervening paragraph, list item, or heading). The fence is *not*
    turned into a claim/evidence context — it is a sibling block.
    """

    start_line: int
    end_line: int
    info: str
    text: str


@dataclass(frozen=True)
class Section:
    """A Markdown heading and the body that belongs to it (until the next
    heading of equal or higher level).

    ``start_line`` is the heading line (1-based, original file).
    ``end_line`` is the first line of the next equal/higher-level heading
    (or the end of the document). ``body_text`` is the raw lines between
    ``start_line + 1`` and ``end_line - 1``, joined by ``\n``.
    """

    level: int
    title: str
    start_line: int
    end_line: int
    body_text: str


@dataclass(frozen=True)
class ParseResult:
    """Outcome of parsing one Markdown document."""

    contexts: tuple[MarkdownContext, ...]
    fences: tuple[FenceBlock, ...] = field(default_factory=tuple)
    sections: tuple[Section, ...] = field(default_factory=tuple)
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
    fences: list[FenceBlock] = []
    stack: list[_OpenListItem] = []
    paragraph_counter = 0
    list_item_counter = 0
    in_heading = False
    pending_heading_level = 0
    pending_heading_line = 0
    headings: list[tuple[int, str, int]] = []  # (level, title, start_line)

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        ttype = tok.type

        if ttype == "heading_open":
            in_heading = True
            pending_heading_level = int(tok.tag[1])  # h1 -> 1
            pending_heading_line = _to_1based(tok.map, offset)[0]
            i += 1
            continue

        if ttype == "heading_close":
            in_heading = False
            i += 1
            continue

        if ttype == "inline" and in_heading:
            headings.append(
                (pending_heading_level, tok.content.strip(), pending_heading_line)
            )
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

        if ttype == "hr":
            i += 1
            continue

        if ttype in ("fence", "code_block"):
            # Capture fenced blocks for E3 adjacent-command detection, but do
            # NOT turn them into claim/evidence contexts.
            f_start, f_end = _to_1based(tok.map, offset)
            fences.append(
                FenceBlock(
                    start_line=f_start,
                    end_line=f_end,
                    info=(tok.info or "").strip(),
                    text=tok.content or "",
                )
            )
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

    # Build Section objects from headings. Body is raw lines between the
    # heading line and the next heading of equal or higher level (or EOF).
    body_lines = body.split("\n")
    sections: list[Section] = []
    for idx, (level, title, h_line) in enumerate(headings):
        end_line = len(body_lines) + 1  # 1-based exclusive
        for later_level, _later_title, later_line in headings[idx + 1 :]:
            if later_level <= level:
                end_line = later_line
                break
        # Body lines are body[h_line .. end_line-2] in 0-based body_lines.
        # h_line is 1-based original file; body is offset-shifted, but body
        # line k corresponds to original line k + offset + 1. We already have
        # h_line in original coordinates; convert to body 0-based index.
        body_start_0 = h_line - offset - 1  # exclusive of heading line itself
        body_end_0 = end_line - offset - 1
        body_slice = body_lines[body_start_0 + 1 : body_end_0]
        sections.append(
            Section(
                level=level,
                title=title,
                start_line=h_line,
                end_line=end_line,
                body_text="\n".join(body_slice),
            )
        )

    return ParseResult(
        contexts=tuple(contexts),
        fences=tuple(fences),
        sections=tuple(sections),
        diagnostics=tuple(diagnostics),
    )
