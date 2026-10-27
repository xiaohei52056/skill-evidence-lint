"""4B: strict evidence association and the E1 rule.

Association rules (product decision — strict mode):

* A claim may only be paired with an evidence reference that lives in:
  * the **same paragraph** (identical paragraph-level ``context_id``), or
  * the **same list item** (identical non-None ``enclosing_list_item_id``).
* Top-level paragraphs never associate with neighbouring paragraphs.
* Different list items never associate, even when adjacent.
* Nested lists attach claims/references only to their innermost list item.
* Headings, shared sections, or a global "Evidence" block never associate.

Reference-type policy:

* ``local_path`` and ``url`` references count as recognizable evidence for E1.
  This phase does NOT check file existence (E2) or reachability.
* ``command`` references do NOT count: a backtick command example is not, by
  itself, evidence backing a claim.

E1 means: "no qualifying reference was detected in the allowed context". It is
a coverage observation, never a verdict that the claim is false or invalid.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    CandidateClaim,
    EvidenceReference,
    Finding,
    RefType,
    RuleID,
)

# Reference types that clear E1. Commands are deliberately excluded.
_COUNTING_TYPES = frozenset({RefType.LOCAL_PATH, RefType.URL})

_E1_MESSAGE = (
    "No local-path or URL evidence reference found in the same paragraph or "
    "the enclosing list item. This is a coverage observation, not a judgment "
    "that the claim is false or that evidence is invalid."
)


@dataclass(frozen=True)
class AssociationPair:
    """A claim paired with a qualifying reference (diagnostic, not a verdict)."""

    claim: CandidateClaim
    reference: EvidenceReference


@dataclass(frozen=True)
class AssociationResult:
    """Outcome of associating claims with references."""

    findings: tuple[Finding, ...]
    associated: tuple[AssociationPair, ...]


def _ref_counts(ref: EvidenceReference) -> bool:
    return ref.ref_type in _COUNTING_TYPES


def _is_same_paragraph(claim: CandidateClaim, ref: EvidenceReference) -> bool:
    return ref.context.context_id == claim.context.context_id


def _is_same_list_item(claim: CandidateClaim, ref: EvidenceReference) -> bool:
    claim_item = claim.context.enclosing_list_item_id
    ref_item = ref.context.enclosing_list_item_id
    return claim_item is not None and claim_item == ref_item


def associate_evidence(
    claims: list[CandidateClaim] | tuple[CandidateClaim, ...],
    references: list[EvidenceReference] | tuple[EvidenceReference, ...],
) -> AssociationResult:
    """Pair claims with qualifying references and emit E1 for unpaired claims."""
    qualifying = [r for r in references if _ref_counts(r)]

    findings: list[Finding] = []
    pairs: list[AssociationPair] = []

    for claim in claims:
        matched = [
            r
            for r in qualifying
            if _is_same_paragraph(claim, r) or _is_same_list_item(claim, r)
        ]

        if matched:
            for ref in matched:
                pairs.append(AssociationPair(claim=claim, reference=ref))
            continue

        findings.append(
            Finding(
                rule_id=RuleID.E1,
                message=_E1_MESSAGE,
                context=claim.context,
                claim_text=claim.text,
                claim_id=claim.claim_id,
                line=claim.line,
            )
        )

    return AssociationResult(findings=tuple(findings), associated=tuple(pairs))
