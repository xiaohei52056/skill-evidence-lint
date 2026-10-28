"""E6 — URL format and placeholder check (offline-only).

Despite the rule id ``evidence-url-unreachable``, this rule **never** makes
a network request, DNS lookup, or redirect check. It only performs
deterministic local parsing of URLs already extracted by the evidence
extractor and flags two narrow classes:

1. **Malformed authority** — a URL that starts with ``http://`` or
   ``https://`` but has no host after the scheme (e.g. ``http:///path``,
   ``http://``).
2. **Obvious placeholder** — the host or path contains a reserved example
   domain (``example.com`` / ``.org`` / ``.net`` / ``.edu``), an explicit
   template token (``your-domain``, ``replace_me``, ``TODO``, ``{{...}}``),
   or ``xxxx``.

Deliberately NOT flagged:

* ``localhost``, private IPs, bare domains, and URLs without a path.
* Any unfamiliar hostname — we do not guess whether a server exists.
* Domains that merely look unusual.

The finding message says the URL *appears malformed or is an obvious
placeholder*; it never claims the URL is actually unreachable.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from .models import EvidenceReference, Finding, RefType, RuleID

# Reserved documentation domains (RFC 2606 / IANA).
_EXAMPLE_HOSTS = frozenset(
    {"example.com", "example.org", "example.net", "example.edu"}
)

# Substrings that clearly indicate a template / placeholder URL.
_PLACEHOLDER_SUBSTRINGS = (
    "your-domain",
    "yourdomain",
    "your_host",
    "your-host",
    "replace_me",
    "replace-me",
    "replaceme",
    "{{",
    "}}",
    "xxxx",
)


def _classify(url: str) -> str | None:
    """Return a short reason string if the URL is malformed/placeholder, else None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "URL could not be parsed"

    if parts.scheme not in ("http", "https"):
        # The extractor already only emits http(s), but be defensive.
        return None

    if not parts.netloc:
        return "URL has no host after scheme"

    host = parts.netloc.lower()
    # Strip optional userinfo:port for host comparison.
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]

    if host in _EXAMPLE_HOSTS:
        return f"host {host!r} is a reserved documentation placeholder"

    haystack = (parts.netloc + "/" + (parts.path or "")).lower()
    for token in _PLACEHOLDER_SUBSTRINGS:
        if token in haystack:
            return f"URL contains placeholder token {token!r}"

    return None


def check_urls(
    references: list[EvidenceReference] | tuple[EvidenceReference, ...],
) -> tuple[Finding, ...]:
    """Emit E6 info findings for malformed or placeholder URL references."""
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()
    for ref in references:
        if ref.ref_type is not RefType.URL:
            continue
        reason = _classify(ref.raw_path)
        if reason is None:
            continue
        key = (ref.raw_path, ref.line)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                rule_id=RuleID.E6,
                message=(
                    f"Evidence URL {ref.raw_path!r} appears malformed or is "
                    f"an obvious placeholder ({reason}). Network reachability "
                    "was not checked."
                ),
                context=ref.context,
                claim_text=None,
                claim_id="",
                line=ref.line,
            )
        )
    return tuple(findings)
