"""Minimal data model for skill-evidence-lint.

Phase 1 only defines the shapes. Later phases will fill in how Markdown is
split into contexts, how English claims are extracted, and how evidence
references are associated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ContextType(StrEnum):
    """The smallest unit that may carry a claim and/or an evidence reference."""

    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"


class RuleID(StrEnum):
    """Rule identifiers used in findings.

    C1 is a candidate claim (not a violation). E1/E2 are findings reported in
    later phases.
    """

    C1 = "C1"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"


@dataclass(frozen=True)
class MarkdownContext:
    """One paragraph or one list item of a SKILL.md file.

    ``context_id`` is a stable, unique identifier assigned by the parser:
    paragraphs use ``p-<n>`` and list items use ``li-<n>`` (document order).

    For paragraph contexts, ``enclosing_list_item_id`` is the id of the list
    item that directly contains the paragraph (or ``None`` for top-level
    paragraphs). For list-item-level contexts it is always ``None``.
    """

    type: ContextType
    raw_text: str
    start_line: int
    end_line: int
    context_id: str = ""
    enclosing_list_item_id: str | None = None

    @property
    def text(self) -> str:
        """Trimmed text of the context."""
        return self.raw_text.strip()


@dataclass(frozen=True)
class CandidateClaim:
    """An English effect claim candidate (rule C1).

    Being a candidate is not itself a violation; it only counts toward the
    coverage denominator. ``claim_id`` is a stable counter id assigned by the
    extractor; ``pattern_id`` identifies which conservative rule fired; ``line``
    is the 1-based physical line of the match. ``context_id`` and
    ``enclosing_list_item_id`` remain reachable via ``context``.
    """

    text: str
    context: MarkdownContext
    claim_id: str = ""
    pattern_id: str = ""
    language: str = "en"
    line: int = 0


class RefType(StrEnum):
    """Kind of evidence reference detected in a context."""

    LOCAL_PATH = "local_path"
    URL = "url"
    COMMAND = "command"


@dataclass(frozen=True)
class EvidenceReference:
    """A reference found inside a context.

    ``raw_path`` holds the original matched text (for URLs this is the URL
    itself; for commands it is the backtick-wrapped command text).
    ``exists`` stays ``None`` until a later phase performs path-safety and
    filesystem checks; detecting a reference is NOT proof the evidence is
    valid or that any claim is true.
    """

    raw_path: str
    context: MarkdownContext
    reference_id: str = ""
    ref_type: RefType = RefType.LOCAL_PATH
    language: str = "en"
    line: int = 0
    # None = not yet checked; True/False = after path-safety + existence check.
    exists: bool | None = None


@dataclass(frozen=True)
class Finding:
    """A reported lint finding (E1 or E2; C1 is not reported as a finding)."""

    rule_id: RuleID
    message: str
    context: MarkdownContext
    claim_text: str | None = None
    claim_id: str = ""
    line: int = 0


@dataclass
class CheckReport:
    """The aggregate result of checking one Skill directory."""

    skill_path: str
    contexts: list[MarkdownContext] = field(default_factory=list)
    claims: list[CandidateClaim] = field(default_factory=list)
    references: list[EvidenceReference] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def claim_count(self) -> int:
        return len(self.claims)

    def findings_for(self, rule_id: RuleID) -> list[Finding]:
        return [f for f in self.findings if f.rule_id is rule_id]
