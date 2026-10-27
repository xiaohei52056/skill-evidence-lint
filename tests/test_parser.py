"""Tests for the Markdown context parser."""

from skill_evidence_lint.parser import parse_text


# --------------------------------------------------------------------------- #
# Basic paragraphs
# --------------------------------------------------------------------------- #
def test_plain_paragraph_text_and_lines():
    doc = "First paragraph.\n\nSecond paragraph."
    result = parse_text(doc)
    paras = result.paragraphs()

    assert [p.text for p in paras] == ["First paragraph.", "Second paragraph."]
    # 1-based lines: para 1 spans line 1, para 2 starts at line 3.
    assert (paras[0].start_line, paras[0].end_line) == (1, 1)
    assert (paras[1].start_line, paras[1].end_line) == (3, 3)
    assert result.diagnostics == ()


def test_adjacent_paragraphs_have_distinct_ids():
    doc = "A.\n\nB.\n\nC."
    paras = parse_text(doc).paragraphs()
    ids = [p.context_id for p in paras]
    assert ids == ["p-1", "p-2", "p-3"]
    assert len(set(ids)) == 3


# --------------------------------------------------------------------------- #
# Headings
# --------------------------------------------------------------------------- #
def test_heading_is_not_merged_with_following_paragraph():
    doc = "# Title\n\nBody paragraph here."
    result = parse_text(doc)
    paras = result.paragraphs()

    assert [p.text for p in paras] == ["Body paragraph here."]
    # Body starts on line 3, not line 1.
    assert paras[0].start_line == 3
    assert result.list_items() == []


# --------------------------------------------------------------------------- #
# Code blocks are excluded
# --------------------------------------------------------------------------- #
def test_fenced_code_block_is_excluded():
    doc = "Intro.\n\n```\nshould not be a paragraph\n```\n\nAfter."
    paras = parse_text(doc).paragraphs()
    assert [p.text for p in paras] == ["Intro.", "After."]
    assert all("should not" not in p.text for p in paras)


def test_indented_code_block_is_excluded():
    doc = "Intro.\n\n    four space code line\n\nAfter."
    paras = parse_text(doc).paragraphs()
    assert [p.text for p in paras] == ["Intro.", "After."]


# --------------------------------------------------------------------------- #
# Frontmatter
# --------------------------------------------------------------------------- #
def test_frontmatter_is_not_treated_as_paragraph():
    doc = "---\ntitle: Demo\n---\n\nReal body.\n"
    result = parse_text(doc)
    paras = result.paragraphs()

    assert [p.text for p in paras] == ["Real body."]
    # frontmatter consumes lines 1..3; body is on line 5.
    assert paras[0].start_line == 5
    assert result.diagnostics == ()


def test_no_frontmatter_when_only_hr_at_top():
    # A lone `---` without a closing pair is a thematic break, not frontmatter.
    doc = "---\n\nBody."
    paras = parse_text(doc).paragraphs()
    assert [p.text for p in paras] == ["Body."]


# --------------------------------------------------------------------------- #
# Empty / edge inputs
# --------------------------------------------------------------------------- #
def test_empty_file_returns_no_contexts():
    result = parse_text("")
    assert result.contexts == ()
    assert result.paragraphs() == []
    assert result.list_items() == []


def test_whitespace_only_file_returns_no_contexts():
    result = parse_text("\n\n  \n\n")
    assert result.contexts == ()


# --------------------------------------------------------------------------- #
# CRLF
# --------------------------------------------------------------------------- #
def test_crlf_does_not_shift_line_numbers():
    doc = "Line one.\r\n\r\nLine two.\r\n"
    paras = parse_text(doc).paragraphs()
    assert [p.text for p in paras] == ["Line one.", "Line two."]
    assert paras[0].start_line == 1
    assert paras[1].start_line == 3


# --------------------------------------------------------------------------- #
# List items
# --------------------------------------------------------------------------- #
def test_distinct_list_items_have_distinct_ids():
    doc = "- Alpha.\n- Beta.\n- Gamma."
    result = parse_text(doc)
    items = result.list_items()
    assert [i.context_id for i in items] == ["li-1", "li-2", "li-3"]
    assert [i.text for i in items] == ["Alpha.", "Beta.", "Gamma."]


def test_paragraph_inside_list_item_links_to_that_item_only():
    doc = "- First item claim.\n\n  Continuation of first.\n- Second item."
    result = parse_text(doc)
    paras = result.paragraphs()
    items = result.list_items()

    # Two list items.
    assert [i.context_id for i in items] == ["li-1", "li-2"]

    # First item has two paragraphs (separated by a blank line inside the item).
    first_paras = [p for p in paras if p.enclosing_list_item_id == "li-1"]
    assert [p.text for p in first_paras] == [
        "First item claim.",
        "Continuation of first.",
    ]

    # Second item's paragraph must link to li-2, never li-1.
    second_paras = [p for p in paras if p.enclosing_list_item_id == "li-2"]
    assert [p.text for p in second_paras] == ["Second item."]

    # No paragraph leaks across items.
    leaked = [p for p in paras if p.enclosing_list_item_id not in ("li-1", "li-2")]
    assert leaked == []


def test_top_level_paragraphs_have_no_enclosing_item():
    doc = "Top paragraph.\n\n- In item."
    paras = parse_text(doc).paragraphs()
    assert paras[0].enclosing_list_item_id is None
    assert paras[1].enclosing_list_item_id == "li-1"


# --------------------------------------------------------------------------- #
# Nested lists
# --------------------------------------------------------------------------- #
def test_nested_list_ownership_is_explicit():
    doc = (
        "- Parent item.\n"
        "  - Nested A.\n"
        "  - Nested B.\n"
        "- Another top item.\n"
    )
    result = parse_text(doc)
    items = result.list_items()
    item_ids = [i.context_id for i in items]

    # Parent, then two nested children, then the sibling top item.
    assert item_ids == ["li-1", "li-2", "li-3", "li-4"]

    paras = result.paragraphs()
    by_item = {p.enclosing_list_item_id: p.text for p in paras}
    assert by_item["li-1"] == "Parent item."
    assert by_item["li-2"] == "Nested A."
    assert by_item["li-3"] == "Nested B."
    assert by_item["li-4"] == "Another top item."

    # Nested items' paragraphs must NOT be attributed to the parent item's prose.
    parent = next(i for i in items if i.context_id == "li-1")
    assert "Nested A" not in parent.text
    assert "Nested B" not in parent.text


# --------------------------------------------------------------------------- #
# Mixed document: end-to-end smoke
# --------------------------------------------------------------------------- #
def test_mixed_document_counts():
    doc = (
        "---\nkey: v\n---\n"
        "\n"
        "# Heading\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "- Item one.\n"
        "- Item two.\n"
        "  - Nested.\n"
        "\n"
        "Closing paragraph.\n"
    )
    result = parse_text(doc)
    assert result.diagnostics == ()

    para_texts = [p.text for p in result.paragraphs()]
    assert para_texts == [
        "Intro paragraph.",
        "Item one.",
        "Item two.",
        "Nested.",
        "Closing paragraph.",
    ]
    item_ids = [i.context_id for i in result.list_items()]
    assert item_ids == ["li-1", "li-2", "li-3"]
