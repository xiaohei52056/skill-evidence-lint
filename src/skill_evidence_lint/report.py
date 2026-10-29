"""Stable, versioned JSON report serializer.

Contract: schema id ``skill-evidence-lint.report.v1``.

The serializer only projects existing ``RunResult`` data into JSON. It does
not re-run rules, infer severities beyond the documented rule table, or add
facts about claim truth / evidence sufficiency. Fields are stable; adding
new top-level keys in a future version bumps the schema id.

Exit-code / stdout contract: when ``--format json`` is selected, **only**
the JSON document is written to stdout. Diagnostics go to stderr. The exit
code is unchanged (0 = check completed, findings do not block).
"""

from __future__ import annotations

import json
from importlib import metadata

from .models import RuleID
from .runner import RunResult

SCHEMA_ID = "skill-evidence-lint.report.v1"

# Documented severity per rule id (matches README and rule contract).
# C1 is internal counting only and is not emitted as a finding.
_SEVERITY: dict[str, str] = {
    "E1": "warning",
    "E2": "error",
    "E3": "warning",
    "E4": "info",
    "E5": "warning",
    "E6": "info",
    "E7": "info",
}

_RULE_ORDER = ["E1", "E2", "E3", "E4", "E5", "E6", "E7"]


def _tool_version() -> str:
    try:
        return metadata.version("skill-evidence-lint")
    except metadata.PackageNotFoundError:
        return "0.0.0+local"


def _claim_to_dict(claim) -> dict:
    return {
        "claim_id": claim.claim_id,
        "text": claim.text,
        "line": claim.line,
        "pattern_id": claim.pattern_id,
        "language": claim.language,
        "context_id": claim.context.context_id,
    }


def _ref_to_dict(ref) -> dict:
    return {
        "reference_id": ref.reference_id,
        "ref_type": str(ref.ref_type),
        "raw": ref.raw_path,
        "line": ref.line,
        "language": ref.language,
        "context_id": ref.context.context_id,
        "exists": ref.exists,
    }


def _finding_to_dict(finding) -> dict:
    rule = str(finding.rule_id)
    out = {
        "rule_id": rule,
        "severity": _SEVERITY.get(rule, "info"),
        "line": finding.line,
        "message": finding.message,
        "claim_id": finding.claim_id,
        "claim_text": finding.claim_text,
    }
    # E4-only fields; contract §7.2 says these appear ONLY on E4 findings.
    if rule == "E4":
        out["evidence_path"] = finding.evidence_path
        out["evidence_date"] = finding.evidence_date
        out["skill_date"] = finding.skill_date
        out["days_diff"] = finding.days_diff
    return out


def build_report(result: RunResult) -> dict:
    """Project a RunResult into a stable-schema dict."""
    by_rule = {rule: result.count_for(RuleID(rule)) for rule in _RULE_ORDER}
    return {
        "schema": SCHEMA_ID,
        "tool": {
            "name": "skill-evidence-lint",
            "version": _tool_version(),
        },
        "input": {
            "skill_md_path": result.skill_md_path,
        },
        "summary": {
            "claims": result.claim_count,
            "references": result.reference_count,
            "findings": len(result.findings),
            "by_rule": by_rule,
        },
        "claims": [_claim_to_dict(c) for c in result.claims],
        "references": [_ref_to_dict(r) for r in result.references],
        "findings": [_finding_to_dict(f) for f in result.findings],
    }


def dumps(result: RunResult) -> str:
    """Serialize a RunResult to a single JSON string (deterministic key order)."""
    return json.dumps(
        build_report(result),
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    )
