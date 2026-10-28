"""Tests for E3 — reproducibility-cue coverage."""

from __future__ import annotations

from skill_evidence_lint.claim_extractor import extract_candidate_claims
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text
from skill_evidence_lint.repro_cue import check_repro_cues, has_repro_cues


def _claims_for(text: str):
    parsed = parse_text(text)
    return extract_candidate_claims(parsed.contexts), parsed


# --- inline cue presence detection ----------------------------------------- #


def test_command_cue_npm_in_inline_code():
    # `npm run benchmark` has a positional arg, so it counts.
    assert has_repro_cues("run `npm run benchmark` to verify.") == (
        True,
        False,
        False,
    )


def test_command_cue_python_with_script():
    cmd, _, _ = has_repro_cues("execute `python tests/bench.py` for numbers.")
    assert cmd is True


def test_env_only_command_does_not_count():
    # `python --version` is environment-only; no positional target.
    cmd, _, _ = has_repro_cues("run `python --version` to check setup.")
    assert cmd is False


def test_arbitrary_backtick_does_not_count_as_command():
    assert has_repro_cues("We improved by 40%, see `foo` for details.")[0] is False


def test_input_cue_dataset_phrase():
    cmd, inp, _ = has_repro_cues(
        "We observed 40% improvement on dataset imagenette."
    )
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


# --- end-to-end E3 finding emission ---------------------------------------- #


def test_numeric_claim_with_no_cue_emits_e3():
    text = "We reduced processing time by 40%."
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1
    assert findings[0].rule_id is RuleID.E3
    assert "command" in findings[0].message
    assert "input/dataset/config" in findings[0].message
    assert "metric-definition" in findings[0].message


def test_numeric_claim_with_inline_benchmark_command_no_e3():
    text = "We reduced processing time by 40%, run `python bench.py`."
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert findings == ()


def test_env_only_command_still_emits_e3():
    # `python --version` is not a benchmark cue; E3 must still fire.
    text = "We reduced processing time by 40%, run `python --version`."
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1


def test_numeric_claim_with_input_cue_no_e3():
    text = "We reduced processing time by 40% on dataset imagenette."
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert findings == ()


def test_numeric_claim_with_metric_cue_no_e3():
    text = "We achieve 92% pass rate on the smoke suite."
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert findings == ()


def test_cue_in_other_paragraph_does_not_count():
    text = (
        "We reduced processing time by 40%.\n\n"
        "To reproduce, run `python bench.py`."
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1


def test_cue_in_other_list_item_does_not_count():
    text = (
        "- We reduced processing time by 40%.\n"
        "- Reproduce with `python bench.py`."
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1
    assert any(f.rule_id is RuleID.E3 for f in findings)


# --- fenced command block association --------------------------------------- #


def test_fenced_benchmark_block_immediately_after_claim():
    text = (
        "We reduced processing time by 40%.\n\n"
        "```bash\n"
        "python benchmark.py --dataset imagenette\n"
        "```\n"
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert findings == (), findings


def test_fenced_block_separated_by_paragraph_does_not_count():
    text = (
        "We reduced processing time by 40%.\n\n"
        "Here is some unrelated prose.\n\n"
        "```bash\n"
        "python benchmark.py\n"
        "```\n"
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1


def test_fenced_block_under_different_list_item_does_not_count():
    text = (
        "- We reduced processing time by 40%.\n"
        "- Notes:\n"
        "  ```bash\n"
        "  python benchmark.py\n"
        "  ```\n"
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    # The claim is in the first list item; the fence is in the second item.
    assert len(findings) == 1


def test_fenced_env_only_command_does_not_silence_e3():
    text = (
        "We reduced processing time by 40%.\n\n"
        "```bash\n"
        "python --version\n"
        "```\n"
    )
    claims, parsed = _claims_for(text)
    findings = check_repro_cues(
        claims, contexts=parsed.contexts, fences=parsed.fences
    )
    assert len(findings) == 1
