"""C1 candidate English effect-claim extractor.

This module only *proposes* candidates (rule C1). It does not judge whether a
claim is true, does not produce E1/E2 findings, and does not associate claims
with evidence — that belongs to later phases.

Design choices (kept deliberately small and explainable):

* Input is the structured :class:`MarkdownContext` list produced by the parser.
  We never re-parse raw Markdown and never scan by line windows.
* Only paragraph-type contexts are scanned. List-item contexts exist so that
  later association can reach across multiple paragraphs of one item; their
  ``raw_text`` is a *join* of those paragraphs, so scanning them too would
  double-count the same sentence.
* Code blocks, headings, and frontmatter are already excluded by the parser,
  so this extractor never sees their text.
* Patterns are English-word-rooted and require a quantifier (% / percent / x /
  times / pp) or a comparative adjective. Numbers alone (versions, dates,
  config values, timeouts) do not match.
* Negated and hypothetical sentences are filtered out conservatively. The
  remaining ambiguity is documented below and is acceptable for a *candidate*
  extractor.

Known coverage boundary (intentionally NOT matched):

* Subjective claims without a number ("This skill is fast", "It works well").
* Claims phrased purely in the passive without our verbs ("Build time is down
  40%").
* Chinese effect claims are out of scope (product decision: English only).
* Quotes in backticks or inline code — inline code is preserved in paragraph
  text, but such examples are usually illustrative; if they read as real
  quantified claims they will still match, which is acceptable noise for C1.
"""

from __future__ import annotations

import re

from .models import CandidateClaim, ContextType, MarkdownContext

# --------------------------------------------------------------------------- #
# Patterns
# --------------------------------------------------------------------------- #
# Each entry: (pattern_id, compiled regex). All are matched case-insensitively.
#
# Q-VERB-BY      "reduces processing time by 40%", "cuts cost by 2x"
# Q-ACHIEVES-NUM "achieves 92% accuracy", "delivers 30% faster builds"
# Q-NUM-COMP     "2x faster", "30% less memory", "50% fewer errors"
# Q-ZERO         "zero downtime", "zero-config", "near-zero latency"
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Q-VERB-BY",
        re.compile(
            r"\b(?:reduc\w*|improv\w*|increas\w*|cut\w*|low\w*|decreas\w*|boost\w*|"
            r"shorten\w*|speeds?\s+up|sped\s+up)\b"
            r"[^.;]{0,120}?"
            r"\bby\s+\d+(?:\.\d+)?\s*(?:%|percent|x|×|times|pp|percentage\s+points?)",
            re.IGNORECASE,
        ),
    ),
    (
        "Q-ACHIEVES-NUM",
        re.compile(
            r"\b(?:achiev\w*|deliver\w*|ensur\w*|guarantee\w*|provides?)\s+"
            r"\d+(?:\.\d+)?\s*(?:%|percent|x|×|times)",
            re.IGNORECASE,
        ),
    ),
    (
        "Q-NUM-COMP",
        re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:%|percent|x|×|times)\s+"
            r"(?:faster|slower|less|more|higher|lower|smaller|better|worse|"
            r"cheaper|quicker|fewer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Q-ZERO",
        re.compile(
            r"\b(?:near-?zero|zero|0)\s+"
            r"(?:config|setup|latency|downtime|errors?|friction|overhead)\b",
            re.IGNORECASE,
        ),
    ),
]

# Words that turn a matched sentence into something we should NOT treat as a
# present-tense effect claim. Conservative: if any appears within ~40 chars
# before the match, skip it.
_NEGATION = re.compile(
    r"\b(?:not|never|no|without|don'?t|doesn'?t|isn'?t|aren'?t|wasn'?t)\b",
    re.IGNORECASE,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:if|assuming|suppose\w*|could|would|might|should|expected\s+to|"
    r"aims?\s+to|target(?:ing)?|want\s+to|plan(?:ned)?\s+to)\b",
    re.IGNORECASE,
)


def _claim_line(ctx: MarkdownContext, match_start_in_text: int) -> int:
    """1-based physical line of the match inside the original file.

    ``ctx.raw_text`` may contain soft line breaks (``\\n``) when a paragraph
    is wrapped across physical lines; count them to locate the exact line.
    """
    newlines_before = ctx.raw_text.count("\n", 0, match_start_in_text)
    return ctx.start_line + newlines_before


def extract_candidate_claims(
    contexts: list[MarkdownContext] | tuple[MarkdownContext, ...],
) -> list[CandidateClaim]:
    """Extract C1 candidate English effect claims from parsed contexts.

    Only paragraph-type contexts are scanned; list-item contexts are returned
    as association anchors in a later phase. An empty input yields an empty list.
    """
    claims: list[CandidateClaim] = []
    counter = 0

    for ctx in contexts:
        if ctx.type is not ContextType.PARAGRAPH:
            continue

        text = ctx.raw_text
        for pattern_id, regex in _PATTERNS:
            for match in regex.finditer(text):
                # Guard: negation / hypothetical window just before the match.
                window_start = max(0, match.start() - 40)
                window = text[window_start : match.start()]
                if _NEGATION.search(window) or _HYPOTHETICAL.search(window):
                    continue

                counter += 1
                claims.append(
                    CandidateClaim(
                        text=match.group(0).strip(),
                        context=ctx,
                        claim_id=f"c-{counter}",
                        pattern_id=pattern_id,
                        language="en",
                        line=_claim_line(ctx, match.start()),
                    )
                )

    return claims
