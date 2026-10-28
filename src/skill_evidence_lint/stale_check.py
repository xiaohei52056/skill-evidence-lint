"""E4 — evidence-stale (frozen contract v1.0, see docs/e4-contract.md).

A deterministic, offline, info-level rule. For each (claim, local-path
reference) pair, E4 compares the **declared date metadata** on the
referenced evidence file against the **declared date metadata** on the
SKILL.md frontmatter. It emits a finding only when the evidence's
normalized UTC calendar date is strictly earlier than the skill's.

E4 does NOT judge whether evidence is factually out of date. It does
not read the system clock, git history, or the network. Any ambiguity
causes a silent skip (false-positive cost > false-negative cost).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .models import (
    CandidateClaim,
    EvidenceReference,
    Finding,
    RefType,
    RuleID,
)

# ---------------------------------------------------------------------------
# Constants (frozen by contract)
# ---------------------------------------------------------------------------

MAX_READ_BYTES = 1024 * 1024  # 1 MiB; we read up to 1 MiB+1 to detect overflow.
SUPPORTED_EXTENSIONS = frozenset(
    {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".csv"}
)

# G1a: data-point fields. G1b: generic date fields.
_G1A_FIELDS = ("as_of", "data_date")
_G1B_FIELDS = (
    "date",
    "updated",
    "last_updated",
    "last_modified",
    "generated",
    "run_date",
)
# Skill-side priority fallback (first parseable wins).
_SKILL_FIELDS = ("date", "updated", "last_modified", "version_date")

# Placeholder literals that must never parse as a real date.
_PLACEHOLDERS = frozenset(
    {
        "yyyy-mm-dd",
        "yyyy/mm/dd",
        "xxxx-xx-xx",
        "yyyy.mm.dd",
        "todo",
        "tbd",
        "<date>",
        "n/a",
        "-",
    }
)

# G2: a date embedded in a filename, bounded by start or [-_.] separators.
_FILENAME_DATE_RE = re.compile(
    r"(?:^|[-_.])(?P<d>\d{4}[-/.]\d{2}[-/.]\d{2})(?:[-_.]|$)"
)

# G3: labeled date line. Label whitelist (case-insensitive), colon (ASCII or
# full-width), then a full datetime token that may carry time + timezone.
_G3_DATE_RE = re.compile(
    r"^\s*(?:#\s*|[-*]\s*|>\s*)?"
    r"(?P<label>Last updated|Date|Run on|Generated|As of|Updated|Last modified)"
    r"\s*[:：]\s*"
    r"(?P<date>\d{4}[-/.]\d{2}[-/.]\d{2}"
    r"(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)",
    re.IGNORECASE,
)

_MIN_YEAR = 2000


# ---------------------------------------------------------------------------
# Date parsing (strict ISO subset + UTC normalization)
# ---------------------------------------------------------------------------

def _parse_offset(token: str) -> timezone | None:
    """Parse 'Z' or '+HH:MM' / '+HHMM' / '+HH' into a timezone, or None."""
    if token == "Z":
        return UTC
    sign = 1 if token[0] == "+" else -1
    body = token[1:]
    parts = body.split(":")
    try:
        if len(parts) == 2:
            hours, minutes = int(parts[0]), int(parts[1])
        elif len(parts) == 1 and len(parts[0]) == 4:
            hours, minutes = int(parts[0][:2]), int(parts[0][2:])
        elif len(parts) == 1 and len(parts[0]) == 2:
            hours, minutes = int(parts[0]), 0
        else:
            return None
    except ValueError:
        return None
    total_minutes = sign * (hours * 60 + minutes)
    if not (-14 * 60 <= total_minutes <= 14 * 60):
        return None
    return timezone(__import__("datetime").timedelta(minutes=total_minutes))


def _parse_date_token(raw: str) -> date | None:
    """Parse one date/datetime string into a normalized UTC calendar date.

    Returns None if the string is not in the supported subset, is a calendar
    impossibility, carries fractional seconds, is out-of-range tz, is a
    placeholder, or is earlier than year 2000.
    """
    s = raw.strip().strip("\"'")
    if not s:
        return None
    if s.lower() in _PLACEHOLDERS:
        return None

    # Reject fractional seconds anywhere (contract: not supported).
    if re.search(r"\.\d+", s):
        return None

    # Try date-only forms first.
    m = re.fullmatch(
        r"(?P<y>\d{4})[-/.](?P<mo>\d{2})[-/.](?P<d>\d{2})", s
    )
    if m:
        try:
            y, mo, d = int(m["y"]), int(m["mo"]), int(m["d"])
            if y < _MIN_YEAR:
                return None
            return date(y, mo, d)
        except ValueError:
            return None

    # Try datetime forms: separator is T or space.
    m = re.fullmatch(
        r"(?P<y>\d{4})[-/.](?P<mo>\d{2})[-/.](?P<d>\d{2})"
        r"[T ]"
        r"(?P<h>\d{2}):(?P<mi>\d{2})(?::(?P<s>\d{2}))?"
        r"(?P<tz>Z|[+-]\d{2}:?\d{2})?",
        s,
    )
    if not m:
        return None
    try:
        y, mo, d = int(m["y"]), int(m["mo"]), int(m["d"])
        if y < _MIN_YEAR:
            return None
        h, mi = int(m["h"]), int(m["mi"])
        sec = int(m["s"]) if m["s"] else 0
        tz_token = m["tz"]
    except ValueError:
        return None

    try:
        if tz_token:
            tz = _parse_offset(tz_token)
            if tz is None:
                return None
            dt = datetime(y, mo, d, h, mi, sec, tzinfo=tz)
            return dt.astimezone(UTC).date()
        # Naive datetime: contract says treat as UTC.
        dt = datetime(y, mo, d, h, mi, sec, tzinfo=UTC)
        return dt.date()
    except ValueError:
        return None


def _coerce_date(value: Any) -> date | None:
    """YAML values arrive as str/datetime/date/int; normalize to a date."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            normalized = value.astimezone(UTC).date()
        else:
            normalized = value.date()
        return normalized if normalized.year >= _MIN_YEAR else None
    if isinstance(value, date):
        return value if value.year >= _MIN_YEAR else None
    if isinstance(value, (int, float)):
        # A bare number is not a date (no semver->date mapping allowed).
        return None
    if isinstance(value, str):
        return _parse_date_token(value)
    return None


# ---------------------------------------------------------------------------
# Frontmatter extraction (shared between SKILL.md and evidence files)
# ---------------------------------------------------------------------------

def extract_frontmatter_text(text: str) -> str | None:
    """Return the raw YAML block between leading ``---`` fences, or None.

    This is a thin, independent helper so E4 can parse frontmatter without
    altering parse_text's contract. CRLF and a leading BOM are normalized.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.startswith("\ufeff"):
        normalized = normalized.lstrip("\ufeff")
    lines = normalized.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].rstrip() == "---":
            return "\n".join(lines[1:idx])
    return None


def _fallback_string_frontmatter(fm_text: str) -> dict:
    """Minimal ``key: value`` parser used when safe_load rejects the block.

    We only need the date fields, so treat every value as a raw string.
    This keeps ``date: 2025-02-30`` (invalid) distinguishable from a missing
    field, so the skill-side priority fallback can move on to ``updated``.
    """
    out: dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            out[key] = value
    return out


def parse_frontmatter(fm_text: str | None) -> dict:
    """safe_load frontmatter text; any error -> empty dict (no frontmatter)."""
    if not fm_text or not fm_text.strip():
        return {}
    try:
        loaded = yaml.safe_load(fm_text)
    except (yaml.YAMLError, ValueError):
        # ValueError covers PyYAML rejecting calendar-impossible dates
        # (e.g. 2025-02-30). Fall back to a string parser so we can still
        # distinguish "field present but invalid" from "field absent".
        return _fallback_string_frontmatter(fm_text)
    if not isinstance(loaded, dict):
        return {}
    return loaded


# ---------------------------------------------------------------------------
# Evidence date extraction (G1a -> G1b -> G2 -> G3, group-die)
# ---------------------------------------------------------------------------

def _dates_from_group(fm: dict, fields: tuple[str, ...]) -> list[date]:
    out: list[date] = []
    for f in fields:
        if f in fm and fm[f] is not None:
            d = _coerce_date(fm[f])
            if d is not None:
                out.append(d)
    return out


def _evidence_date(fm: dict, filename: str, content: str) -> date | None:
    """Apply the source-group model. Returns None on any ambiguity/failure."""
    # G1a: exists at all? If any field present but none parse -> die.
    g1a_present = any(f in fm and fm[f] is not None for f in _G1A_FIELDS)
    if g1a_present:
        dates = _dates_from_group(fm, _G1A_FIELDS)
        unique = set(dates)
        if len(unique) == 1:
            return next(iter(unique))
        return None  # present but ambiguous or all-invalid -> die, no fallback

    # G1b
    g1b_present = any(f in fm and fm[f] is not None for f in _G1B_FIELDS)
    if g1b_present:
        dates = _dates_from_group(fm, _G1B_FIELDS)
        unique = set(dates)
        if len(unique) == 1:
            return next(iter(unique))
        return None

    # G2: filename date
    fn_dates = [
        _parse_date_token(m.group("d"))
        for m in _FILENAME_DATE_RE.finditer(filename)
    ]
    fn_dates = [d for d in fn_dates if d is not None]
    fn_unique = set(fn_dates)
    if len(fn_unique) == 1:
        return next(iter(fn_unique))
    if len(fn_unique) > 1:
        return None

    # G3: labeled date lines in content
    g3_dates: list[date] = []
    for line in content.split("\n"):
        m = _G3_DATE_RE.match(line)
        if m:
            d = _parse_date_token(m.group("date"))
            if d is not None:
                g3_dates.append(d)
    g3_unique = set(g3_dates)
    if len(g3_unique) == 1:
        return next(iter(g3_unique))
    return None


def _skill_date(fm: dict) -> date | None:
    """First parseable skill-side date field, in priority order."""
    for f in _SKILL_FIELDS:
        if f in fm and fm[f] is not None:
            d = _coerce_date(fm[f])
            if d is not None:
                return d
    return None


# ---------------------------------------------------------------------------
# File reading (bounded, UTF-8-sig, silent skip on any problem)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _EvidenceFile:
    resolved: Path
    content: str
    fm: dict


def _read_evidence_file(resolved: Path) -> _EvidenceFile | None:
    try:
        raw = resolved.read_bytes()[: MAX_READ_BYTES + 1]
    except OSError:
        return None
    if len(raw) > MAX_READ_BYTES:
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    fm = parse_frontmatter(extract_frontmatter_text(text))
    # Strip frontmatter from content for G3 scanning so that labels inside
    # frontmatter don't get double-counted.
    body_start = extract_frontmatter_text(text)
    if body_start is not None:
        # Reconstruct body: drop the leading --- block.
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        # Find closing fence.
        close = 1
        while close < len(lines) and lines[close].rstrip() != "---":
            close += 1
        if close < len(lines):
            text = "\n".join(lines[close + 1:])
    return _EvidenceFile(resolved=resolved, content=text, fm=fm)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def check_stale(
    claims: tuple[CandidateClaim, ...] | list[CandidateClaim],
    references: tuple[EvidenceReference, ...] | list[EvidenceReference],
    associated_pairs,  # tuple[AssociationPair, ...]
    skill_dir: str | Path,
    skill_frontmatter: dict,
) -> tuple[Finding, ...]:
    """Produce E4 findings. Silent skip on any uncertainty."""
    skill_dt = _skill_date(skill_frontmatter)
    if skill_dt is None:
        return ()

    root = Path(skill_dir).resolve()
    findings: list[Finding] = []
    # Dedup: (claim_id, resolved_path_str) per claim.
    seen: set[tuple[str, str]] = set()

    for pair in associated_pairs:
        claim: CandidateClaim = pair.claim
        ref: EvidenceReference = pair.reference
        if ref.ref_type is not RefType.LOCAL_PATH:
            continue
        # Existence is re-checked locally via resolved.is_file() below.
        # (The existing E2 path-checker emits its own finding for missing
        # paths; we don't depend on ref.exists being populated.)

        raw = ref.raw_path.strip()
        try:
            candidate = root / raw
            resolved = candidate.resolve()
        except (OSError, ValueError):
            continue
        if resolved != root and not resolved.is_relative_to(root):
            continue
        if not resolved.is_file():
            continue
        if resolved.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        key = (claim.claim_id, str(resolved))
        if key in seen:
            continue

        ef = _read_evidence_file(resolved)
        if ef is None:
            continue

        ev_dt = _evidence_date(ef.fm, resolved.name, ef.content)
        if ev_dt is None:
            continue
        if not ev_dt < skill_dt:
            continue

        days_diff = (skill_dt - ev_dt).days
        seen.add(key)
        rel_path = resolved.relative_to(root).as_posix()
        findings.append(
            _e4_finding(
                claim=claim,
                ref=ref,
                rel_path=rel_path,
                evidence_date=ev_dt.isoformat(),
                skill_date=skill_dt.isoformat(),
                days_diff=days_diff,
            )
        )

    # Sort: keep existing global order (line, rule_id, message) but within
    # the same claim, order E4 findings by days_diff descending.
    findings.sort(
        key=lambda f: (
            f.line,
            str(f.rule_id),
            -getattr(f, "days_diff", 0),
            f.message,
        )
    )
    return tuple(findings)


def _e4_finding(
    *,
    claim: CandidateClaim,
    ref: EvidenceReference,
    rel_path: str,
    evidence_date: str,
    skill_date: str,
    days_diff: int,
) -> Finding:
    msg = (
        f"declared evidence date {evidence_date} predates skill date "
        f"{skill_date} by {days_diff} days"
    )
    return Finding(
        rule_id=RuleID.E4,
        message=msg,
        context=ref.context,
        claim_text=claim.text,
        claim_id=claim.claim_id,
        line=ref.line,
        evidence_path=rel_path,
        evidence_date=evidence_date,
        skill_date=skill_date,
        days_diff=days_diff,
    )
