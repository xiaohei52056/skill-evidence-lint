"""Tests for the minimal data model."""

from skill_evidence_lint.models import (
    CandidateClaim,
    CheckReport,
    ContextType,
    EvidenceReference,
    Finding,
    MarkdownContext,
    RuleID,
)


def make_paragraph(text: str = "It reduces latency by 30%.") -> MarkdownContext:
    return MarkdownContext(
        type=ContextType.PARAGRAPH,
        raw_text=f"  {text}\n",
        start_line=3,
        end_line=5,
    )


def test_context_text_is_trimmed():
    ctx = make_paragraph()
    assert ctx.text == "It reduces latency by 30%."
    assert ctx.type is ContextType.PARAGRAPH
    assert ctx.start_line == 3
    assert ctx.end_line == 5


def test_candidate_claim_holds_text_and_context():
    ctx = make_paragraph()
    claim = CandidateClaim(text="reduces latency by 30%", context=ctx)
    assert claim.context is ctx
    assert "latency" in claim.text


def test_evidence_reference_defaults_to_unchecked():
    ctx = make_paragraph()
    ref = EvidenceReference(raw_path="evidence/bench.md", context=ctx)
    assert ref.exists is None


def test_finding_carries_rule_and_message():
    ctx = make_paragraph()
    finding = Finding(
        rule_id=RuleID.E1,
        message="no in-context evidence reference",
        context=ctx,
        claim_text="reduces latency by 30%",
    )
    assert finding.rule_id is RuleID.E1
    assert finding.context is ctx


def test_report_collects_and_filters():
    ctx = make_paragraph()
    other_ctx = MarkdownContext(
        type=ContextType.LIST_ITEM,
        raw_text="- caches results",
        start_line=7,
        end_line=7,
    )
    report = CheckReport(
        skill_path="demo-skill",
        contexts=[ctx, other_ctx],
        claims=[CandidateClaim(text="reduces latency", context=ctx)],
        references=[EvidenceReference(raw_path="evidence/a.md", context=other_ctx)],
        findings=[
            Finding(RuleID.E1, "missing evidence", ctx, claim_text="reduces latency"),
            Finding(RuleID.E2, "file not found", other_ctx),
        ],
    )

    assert report.claim_count == 1
    assert len(report.contexts) == 2
    assert len(report.references) == 1
    assert {f.rule_id for f in report.findings_for(RuleID.E1)} == {RuleID.E1}
    assert len(report.findings_for(RuleID.E2)) == 1
    assert report.findings_for(RuleID.C1) == []
