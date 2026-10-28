"""Tests for E3 — reproducibility-cue coverage."""

from __future__ import annotations

from skill_evidence_lint.claim_extractor import extract_candidate_claims
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text
from skill_evidence_lint.repro_cue import check_repro_cues, has_repro_cues


def _claims_for(text: str):
    parsed = parse_text(text)
    return extract_candidate_claims(parsed.contexts), parsed


def _e3_lines(findings):
    return [f.line for f in findings if f.rule_id is RuleID.E3]


# --- cue presence detection ------------------------------------------------- #


def test_command_cue_npm_in_inline_code():
    assert has_repro_cues("run `npm run benchmark` to verify.") == (
        True,
        False,
        False,
    )


def test_command_cue_python_in_inline_code():
    assert has_repro_cues("execute `python tests/bench.py` for numbers.")[0] is True


def test_input_cue_dataset_phrase():
    cmd, inp, _ = has_repro_cues("We observed 40% improvement on dataset imagenette.")
    assert inp is True
    assert cmd is False


def test_input_cue_using_config():
    _, inp, _ = has_repro_cues("Latency dropped using configuration tuned-4096.")
    assert inp is True


def test_metric_cue_pass_rate():
    _, _, metric = has_repro_cues("We achieve 92% pass rate on the smoke suite.")
    assert metric is True


def test_metric_cue_measured_as():
    _, _, metric = has_repro_cues("Throughput went up, measured as requests/sec.")
    assert metric is True


def test_arbitrary_backtick_does_not_count_as_command():
    # `foo` is not an allowlisted command.
    assert has_repro_cues("We improved by 40%, see `foo` for details.")[0] is False


# --- end-to-end E3 finding emission ----------------------------------------- #


def test_numeric_claim_with_no_cue_emits_e3():
    text = "We reduced processing time by 40%."
    claims, _ = _claims_for(text)
    findings = check_repro_cues(claims)
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E3
    assert "command" in findings[0].message
    assert "input/dataset/config" in findings[0].message
    assert "metric-definition" in findings[0].message


def test_numeric_claim_with_command_cue_emits_no_e3():
    text = "We reduced processing time by 40%, run `python bench.py`."
    claims, _ = _claims_for(text)
    assert check_repro_cues(claims) == ()


def test_numeric_claim_with_input_cue_emits_no_e3():
    text = "We reduced processing time by 40% on dataset imagenette."
    claims, _ = _claims_for(text)
    assert check_repro_cues(claims) == ()


def test_numeric_claim_with_metric_cue_emits_no_e3():
    text = "We achieve 92% pass rate on the smoke suite."
    claims, _ = _claims_for(text)
    assert check_repro_cues(claims) == ()


def test_cue_in_other_paragraph_does_not_count():
    # Claim in paragraph 1; cue in paragraph 2. E3 must still fire.
    text = (
        "We reduced processing time by 40%.\n\n"
        "To reproduce, run `python bench.py`."
    )
    claims, _ = _claims_for(text)
    findings = check_repro_cues(claims)
    assert len(findings) == 1


def test_cue_in_other_list_item_does_not_count():
    text = (
        "- We reduced processing time by 40%.\n"
        "- Reproduce with `python bench.py`."
    )
    claims, _parsed = _claims_for(text)
    # The first list item carries the claim; the second item is a different
    # context and must not satisfy the cue for the first.
    findings = check_repro_cues(claims)
    assert len(findings) == 1
    # Both bullets are top-level list items; E3 should fire on the claim item.
    assert any(f.rule_id is RuleID.E3 for f in findings)


def test_non_allowlisted_command_does_not_silence_e3():
    # `foobar` is not in the allowlist; E3 should still fire.
    text = "We reduced processing time by 40%, see `foobar`."
    claims, _ = _claims_for(text)
    findings = check_repro_cues(claims)
    assert len(findings) == 1


def test_unrelated_command_in_context_silences_e3_by_design():
    # `python` is allowlisted even if the command itself is unrelated. The
    # rule is conservative about cues, not about judging relevance.
    text = "We reduced processing time by 40%, run `python --version`."
    claims, _ = _claims_for(text)
    assert check_repro_cues(claims) == ()
