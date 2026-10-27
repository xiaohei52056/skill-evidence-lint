"""Tests for the C1 English candidate-claim extractor."""

from skill_evidence_lint.claim_extractor import extract_candidate_claims
from skill_evidence_lint.parser import parse_text


def extract(doc: str):
    return extract_candidate_claims(parse_text(doc).contexts)


# --------------------------------------------------------------------------- #
# Positive examples
# --------------------------------------------------------------------------- #
def test_quantified_verb_by_percent():
    claims = extract("This pipeline reduces processing time by 40%.")
    assert len(claims) == 1
    assert claims[0].pattern_id == "Q-VERB-BY"
    assert "reduces processing time by 40%" in claims[0].text
    assert claims[0].language == "en"


def test_achieves_percent_accuracy():
    claims = extract("The model achieves 92% accuracy on the benchmark.")
    assert [c.pattern_id for c in claims] == ["Q-ACHIEVES-NUM"]


def test_num_x_comparative():
    claims = extract("Indexing is 2x faster than the previous version.")
    assert [c.pattern_id for c in claims] == ["Q-NUM-COMP"]


def test_zero_downtime():
    claims = extract("The failover design guarantees zero downtime during rollout.")
    ids = {c.pattern_id for c in claims}
    assert ids == {"Q-ZERO"}


def test_case_and_punctuation_robust():
    claims = extract("REDUCES latency BY 30%!")
    assert len(claims) == 1
    assert "reduces" in claims[0].text.lower()


def test_multiple_claims_in_one_context():
    claims = extract(
        "It reduces latency by 30% and improves throughput by 2x for large files."
    )
    ids = [c.claim_id for c in claims]
    assert len(claims) == 2
    assert len(set(ids)) == 2
    patterns = {c.pattern_id for c in claims}
    assert patterns == {"Q-VERB-BY"}


# --------------------------------------------------------------------------- #
# Negative examples (must NOT produce candidates)
# --------------------------------------------------------------------------- #
def test_imperative_with_number_does_not_match():
    claims = extract("Run the build script and set timeout to 30 seconds.")
    assert claims == []


def test_version_numbers_do_not_match():
    claims = extract("This skill requires Python 3.11 and works with v2.4.1.")
    assert claims == []


def test_dates_and_config_do_not_match():
    claims = extract(
        "Released on 2024-05-01. Set max_retries=5 and port=8080 in config."
    )
    assert claims == []


def test_negated_claim_is_filtered():
    claims = extract("This change does not reduce processing time by 40%.")
    assert claims == []


def test_hypothetical_claim_is_filtered():
    claims = extract("If we optimize the parser, it could reduce latency by 30%.")
    assert claims == []


def test_chinese_effect_claim_not_output():
    claims = extract("该优化将处理时间减少了 40%，准确率提升 15%。")
    assert claims == []


# --------------------------------------------------------------------------- #
# Line numbers, context ids, list-item wiring
# --------------------------------------------------------------------------- #
def test_line_number_and_context_id_are_accurate():
    doc = (
        "Intro.\n"
        "\n"
        "The optimizer reduces build time by 25%.\n"
        "\n"
        "Closing note.\n"
    )
    claims = extract(doc)
    assert len(claims) == 1
    c = claims[0]
    assert c.line == 3
    assert c.context.context_id == "p-2"
    assert c.context.enclosing_list_item_id is None


def test_soft_wrapped_paragraph_line_is_accurate():
    # A single paragraph wrapped across two physical lines; the match starts
    # at "reduces" on the first physical line of the paragraph (file line 3).
    doc = "Intro.\n\nThe optimizer reduces\nbuild time by 25%.\n"
    claims = extract(doc)
    assert len(claims) == 1
    assert claims[0].line == 3


def test_adjacent_paragraphs_have_distinct_context_ids():
    doc = (
        "First claim reduces cost by 10%.\n"
        "\n"
        "Second claim improves accuracy by 5%.\n"
    )
    claims = extract(doc)
    assert len(claims) == 2
    assert claims[0].context.context_id != claims[1].context.context_id


def test_claim_inside_list_item_inherits_enclosing_id():
    doc = "- The loader reduces startup time by 50%."
    claims = extract(doc)
    assert len(claims) == 1
    assert claims[0].context.type.name == "PARAGRAPH"
    assert claims[0].context.enclosing_list_item_id == "li-1"


# --------------------------------------------------------------------------- #
# Code block exclusion (integration with the parser)
# --------------------------------------------------------------------------- #
def test_code_block_content_is_not_scanned():
    doc = (
        "Intro.\n"
        "\n"
        "```\n"
        "fake_example: reduces time by 90%\n"
        "```\n"
        "\n"
        "Real claim: improves accuracy by 15%.\n"
    )
    claims = extract(doc)
    texts = [c.text for c in claims]
    assert len(claims) == 1
    assert "90%" not in texts[0]
    assert "15%" in texts[0]


def test_indented_code_block_content_is_not_scanned():
    doc = "Intro.\n\n    fake: reduces time by 90%\n\nReal claim: cuts cost by 20%.\n"
    claims = extract(doc)
    assert len(claims) == 1
    assert "90%" not in claims[0].text


# --------------------------------------------------------------------------- #
# Empty input
# --------------------------------------------------------------------------- #
def test_empty_input_returns_empty_list():
    assert extract_candidate_claims([]) == []
    assert extract("") == []
