"""Tests for 4A evidence-reference extractor."""

from skill_evidence_lint.evidence_extractor import extract_evidence_references
from skill_evidence_lint.models import RefType
from skill_evidence_lint.parser import parse_text


def extract(doc: str):
    return extract_evidence_references(parse_text(doc).contexts)


# --------------------------------------------------------------------------- #
# local_path
# --------------------------------------------------------------------------- #
def test_local_path_with_slash():
    refs = extract("See evidence/bench.md for numbers.")
    paths = [r for r in refs if r.ref_type is RefType.LOCAL_PATH]
    assert [r.raw_path for r in paths] == ["evidence/bench.md"]


def test_bare_filename_with_extension():
    refs = extract("The setup is documented in README.md.")
    paths = [r for r in refs if r.ref_type is RefType.LOCAL_PATH]
    assert [r.raw_path for r in paths] == ["README.md"]


def test_markdown_link_href_is_captured():
    refs = extract("Details in [the doc](docs/setup.md).")
    paths = [r for r in refs if r.ref_type is RefType.LOCAL_PATH]
    assert "docs/setup.md" in [r.raw_path for r in paths]


# --------------------------------------------------------------------------- #
# url
# --------------------------------------------------------------------------- #
def test_url_is_detected_syntax_only():
    refs = extract("Reference: https://example.com/guide/x.")
    urls = [r for r in refs if r.ref_type is RefType.URL]
    assert [r.raw_path for r in urls] == ["https://example.com/guide/x"]
    for r in refs:
        assert r.exists is None


# --------------------------------------------------------------------------- #
# command
# --------------------------------------------------------------------------- #
def test_backtick_command_is_command_type():
    refs = extract("Run `python scripts/bench.py` to reproduce.")
    cmds = [r for r in refs if r.ref_type is RefType.COMMAND]
    assert [r.raw_path for r in cmds] == ["python scripts/bench.py"]


def test_command_contents_not_double_counted_as_path():
    refs = extract("Run `python run.py` and inspect out.json.")
    types = [(r.ref_type, r.raw_path) for r in refs]
    # run.py appears only as the command, not as a local_path.
    assert (RefType.LOCAL_PATH, "run.py") not in types
    assert (RefType.COMMAND, "python run.py") in types
    assert (RefType.LOCAL_PATH, "out.json") in types


# --------------------------------------------------------------------------- #
# Negative examples
# --------------------------------------------------------------------------- #
def test_versions_dates_config_are_not_paths():
    refs = extract(
        "Requires Python 3.11, released 2024-05-01, set timeout=30 and v2.4.1."
    )
    assert refs == []


def test_plain_sentence_without_path_yields_nothing():
    refs = extract("This paragraph talks about speedups but names no file.")
    assert refs == []


# --------------------------------------------------------------------------- #
# Line numbers, context ids, dedupe
# --------------------------------------------------------------------------- #
def test_line_and_context_ids_are_accurate():
    doc = "Intro.\n\nSee evidence/a.md and b.json for details.\n"
    refs = extract(doc)
    by_type = {(r.ref_type, r.raw_path) for r in refs}
    assert (RefType.LOCAL_PATH, "evidence/a.md") in by_type
    assert (RefType.LOCAL_PATH, "b.json") in by_type
    a = next(r for r in refs if r.raw_path == "evidence/a.md")
    assert a.line == 3
    assert a.context.context_id == "p-2"
    assert a.context.enclosing_list_item_id is None


def test_reference_inside_list_item_inherits_enclosing_id():
    refs = extract("- Reproduce via evidence/run.md.")
    assert len(refs) == 1
    assert refs[0].context.enclosing_list_item_id == "li-1"


def test_duplicate_in_same_context_recorded_once():
    refs = extract("evidence/a.md and again evidence/a.md.")
    same = [r for r in refs if r.raw_path == "evidence/a.md"]
    assert len(same) == 1


def test_empty_input_returns_empty_list():
    assert extract_evidence_references([]) == []
    assert extract("") == []
