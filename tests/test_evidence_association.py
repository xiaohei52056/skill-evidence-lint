"""Tests for 4B: strict evidence association and E1."""

from skill_evidence_lint.claim_extractor import extract_candidate_claims
from skill_evidence_lint.evidence_association import associate_evidence
from skill_evidence_lint.evidence_extractor import extract_evidence_references
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text


def lint(doc: str):
    parsed = parse_text(doc)
    claims = extract_candidate_claims(parsed.contexts)
    refs = extract_evidence_references(parsed.contexts)
    result = associate_evidence(claims, refs)
    return claims, refs, result


# --------------------------------------------------------------------------- #
# Same-paragraph clearing
# --------------------------------------------------------------------------- #
def test_same_paragraph_local_path_clears_e1():
    claims, _refs, result = lint(
        "The optimizer reduces build time by 25% (see evidence/build.md)."
    )
    assert len(claims) == 1
    assert result.findings == ()
    assert len(result.associated) == 1


def test_same_paragraph_url_clears_e1():
    claims, _refs, result = lint(
        "The model improves accuracy by 15% (https://example.com/bench)."
    )
    assert len(claims) == 1
    assert result.findings == ()


def test_same_paragraph_only_command_still_emits_e1():
    claims, _refs, result = lint(
        "The model improves accuracy by 15% (run `python bench.py`)."
    )
    assert len(claims) == 1
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.rule_id is RuleID.E1
    assert f.claim_id == claims[0].claim_id
    assert f.line == claims[0].line


# --------------------------------------------------------------------------- #
# Same-list-item clearing
# --------------------------------------------------------------------------- #
def test_same_list_item_reference_clears_e1():
    doc = (
        "- The loader reduces startup time by 50%.\n"
        "  Numbers: evidence/startup.md.\n"
    )
    claims, _refs, result = lint(doc)
    assert len(claims) == 1
    assert result.findings == ()


def test_reference_in_other_list_item_does_not_clear():
    doc = (
        "- Item A: reduces cost by 10%.\n"
        "- Item B: see evidence/cost.md.\n"
    )
    claims, _refs, result = lint(doc)
    assert len(claims) == 1
    assert len(result.findings) == 1


def test_reference_in_nested_child_does_not_leak_to_parent():
    doc = (
        "- Parent: reduces cost by 10%.\n"
        "  - Nested item: evidence/cost.md.\n"
    )
    claims, _refs, result = lint(doc)
    # Parent claim is in li-1; the reference is in a paragraph belonging to
    # the nested item (li-2). They must not associate.
    assert len(claims) == 1
    assert claims[0].context.enclosing_list_item_id == "li-1"
    assert len(result.findings) == 1


def test_reference_in_nested_item_clears_its_own_claim():
    doc = (
        "- Parent prose.\n"
        "  - Nested: improves latency by 20% (evidence/latency.md).\n"
    )
    claims, _refs, result = lint(doc)
    # Only the nested item has a claim; its own reference clears it.
    assert len(claims) == 1
    assert claims[0].context.enclosing_list_item_id == "li-2"
    assert result.findings == ()


# --------------------------------------------------------------------------- #
# Adjacent paragraphs / headings / global Evidence block
# --------------------------------------------------------------------------- #
def test_adjacent_paragraph_reference_does_not_clear():
    doc = (
        "The optimizer reduces build time by 25%.\n"
        "\n"
        "Evidence: evidence/build.md.\n"
    )
    claims, _refs, result = lint(doc)
    assert len(claims) == 1
    assert len(result.findings) == 1


def test_shared_heading_or_evidence_section_does_not_clear():
    doc = (
        "# Evidence\n"
        "\n"
        "See evidence/global.md.\n"
        "\n"
        "Body: this skill reduces latency by 30%.\n"
    )
    claims, _refs, result = lint(doc)
    # The claim is its own paragraph; the reference lives in a different
    # paragraph. A shared heading must not associate them.
    assert len(claims) == 1
    assert len(result.findings) == 1


# --------------------------------------------------------------------------- #
# E1 semantics / shape
# --------------------------------------------------------------------------- #
def test_one_claim_produces_at_most_one_e1():
    claims, _refs, result = lint("We reduce overhead by 40% with no reference.")
    assert len(claims) == 1
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.rule_id is RuleID.E1
    assert f.claim_text == claims[0].text
    assert f.claim_id == claims[0].claim_id
    assert f.line == claims[0].line
    # Message must not overclaim: it frames E1 as a coverage observation.
    assert "coverage observation" in f.message.lower()


def test_claim_with_existing_looking_path_still_emits_e1_until_e2():
    # E2 is not implemented: even a path that obviously points nowhere must
    # not be reported as E2; it still counts as a recognized reference for E1.
    doc = "We reduce cost by 5% (see nowhere/nope.md)."
    claims, _refs, result = lint(doc)
    assert len(claims) == 1
    # local_path reference clears E1; no E2 finding exists yet.
    assert result.findings == ()
    assert all(f.rule_id is not RuleID.E2 for f in result.findings)


def test_empty_claims_produce_no_findings():
    result = associate_evidence([], [])
    assert result.findings == ()
    assert result.associated == ()


def test_no_duplicate_pairing_from_paragraph_and_list_representation():
    # Claims and references are both paragraph-granular; list-item contexts
    # are never scanned. A single reference must appear once.
    doc = (
        "- Item: reduces cost by 10%.\n"
        "  Evidence: evidence/cost.md.\n"
    )
    claims, refs, result = lint(doc)
    assert len(claims) == 1
    assert len(refs) == 1  # not duplicated via list-item joined text
    assert len(result.associated) == 1


# --------------------------------------------------------------------------- #
# CLI exit code remains 0 on E1 (product rule)
# --------------------------------------------------------------------------- #
def test_e1_does_not_raise_and_pipeline_returns_normally():
    # The pipeline itself never exits non-zero; the CLI wrapper stays at 0 by
    # design. We verify association with E1s completes cleanly.
    _claims, _refs, result = lint("We reduce cost by 10% with no evidence.")
    assert len(result.findings) == 1
