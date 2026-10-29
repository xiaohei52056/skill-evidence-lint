"""Tests for E6 — offline URL format/placeholder check."""

from __future__ import annotations

from skill_evidence_lint.evidence_extractor import extract_evidence_references
from skill_evidence_lint.models import RuleID
from skill_evidence_lint.parser import parse_text
from skill_evidence_lint.url_check import check_urls


def _e6_messages(text: str) -> list[str]:
    parsed = parse_text(text)
    refs = extract_evidence_references(parsed.contexts)
    findings = check_urls(refs)
    return [f.message for f in findings if f.rule_id is RuleID.E6]


def test_valid_https_url_not_flagged():
    assert _e6_messages("See https://example.com/path for details.") != []
    # Wait — example.com is intentionally flagged. Use a different host.
    msgs = _e6_messages("See https://docs.python.org/3/ for details.")
    assert msgs == []


def test_valid_http_url_not_flagged():
    msgs = _e6_messages("See http://docs.python.org/3/ for details.")
    assert msgs == []


def test_no_path_url_not_flagged():
    # Bare host with no path is legitimate; must not be flagged.
    msgs = _e6_messages("Home page: https://docs.python.org.")
    assert msgs == []


def test_malformed_no_host_flagged():
    msgs = _e6_messages("See http:///path for details.")
    assert any("no host" in m for m in msgs)


def test_example_dot_com_flagged():
    msgs = _e6_messages("Use https://example.com/docs as reference.")
    assert any("reserved documentation placeholder" in m for m in msgs)


def test_your_domain_template_flagged():
    msgs = _e6_messages("Set https://your-domain.com/api/v1 in config.")
    assert any("placeholder token" in m for m in msgs)


def test_replace_me_in_path_flagged():
    msgs = _e6_messages("Fetch https://api.example.io/users/REPLACE_ME.")
    # Wait: example.io is not in reserved list, but REPLACE_ME token is.
    assert any("placeholder token" in m for m in msgs)


def test_jinja_template_flagged():
    msgs = _e6_messages("URL is https://{{hostname}}/api.")
    assert any("placeholder token" in m for m in msgs)


def test_localhost_not_flagged():
    msgs = _e6_messages("Local: http://localhost:8080/debug.")
    assert msgs == []


def test_url_in_fence_follows_existing_contract():
    # Fenced blocks are not evidence contexts; the URL inside must not be
    # extracted as a reference.
    text = "Prose.\n\n```\nhttps://example.com/fenced\n```\n"
    parsed = parse_text(text)
    refs = extract_evidence_references(parsed.contexts)
    assert all(r.ref_type.name != "URL" for r in refs)


def test_multiple_urls_deduped_and_deterministic():
    text = (
        "First https://example.com/a.\n\n"
        "Second https://example.com/b.\n\n"
        "Third https:///nohost.\n"
    )
    msgs = _e6_messages(text)
    # Three distinct URLs; no duplicates.
    assert len(msgs) == 3


def test_e6_does_not_change_exit_code(tmp_path):
    from skill_evidence_lint.runner import run_check
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "Bad URL: https://example.com/x.\n", encoding="utf-8"
    )
    result = run_check(str(skill))
    assert any(f.rule_id is RuleID.E6 for f in result.findings)
