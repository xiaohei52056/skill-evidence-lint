# E4 Contract v1.1 — Change Proposal

**Status:** proposed, not ratified. v1.0 remains the active frozen contract.
**Date:** 2026-10-29
**Branch:** `phase-2/quality-and-e3`

This proposal records two backward-compatible improvements made in
P2.6c.8. They are implemented behind the v1.1 label; v1.0 text in
`docs/e4-contract.md` is unchanged.

---

## Change 1 — Accept `last_updated` as a skill-side baseline field

### v1.0 behavior (frozen)

Skill-side priority (contract §3): `date → updated → last_modified → version_date`.

### v1.1 proposed behavior

Priority becomes: `date → updated → last_updated → last_modified → version_date`.

`last_updated` is accepted **only at top level** of SKILL.md frontmatter.
Nested forms such as `metadata.last_updated` are **not** flattened; they
remain out of scope (a separate, larger change).

### Compatibility

- Skills that already use `date` or `updated` are unaffected (they still
  win).
- Skills with only `last_updated` (common in real-world skills like E01,
  E03) now get a recognized skill date.
- All existing strict parsing rules apply unchanged: placeholder
  rejection, calendar-impossible rejection, year ≥2000, tz range ±14:00,
  first parseable wins.

### Tests added

- `test_a35_skill_last_updated_only` — `last_updated` alone works.
- `test_a36_updated_takes_precedence_over_last_updated` — `updated` wins.
- `test_a37_last_updated_invalid_falls_to_version_date` — invalid
  `last_updated` falls through.
- `test_a38_last_updated_placeholder_rejected` — placeholder rejected.

---

## Change 2 — Backtick-wrapped strict paths emitted as LOCAL_PATH

### v1.0 behavior (frozen)

Inline code spans in backticks were masked out before path scanning and
emitted only as `RefType.COMMAND`. A backtick string like
`` `examples/foo.md` `` never reached E1/E2/E4 as a local-path reference.

### v1.1 proposed behavior

After emitting each backtick span as `COMMAND`, the extractor additionally
emits it as `RefType.LOCAL_PATH` **if and only if** the whole backtick
string matches the strict `_LOCAL_PATH` regex (relative path with slash,
or bare filename with a supported evidence extension, no spaces, no
shell metacharacters).

- COMMAND is **always preserved**; LOCAL_PATH is added.
- Strings with spaces, flags, shell metacharacters, or unsupported
  extensions (e.g. `python run.py`, `cat my file.md`, `deploy.exe`)
  remain COMMAND only.
- E2/E4 still enforce existence, root containment, symlink safety, and
  read caps. This change only affects *detection*, not validation.

### Compatibility

- Existing 24 fixtures and A1–A34 tests unchanged (they don't use
  backtick paths for evidence).
- Real skills that write `` `evidence/foo.md` `` now correctly associate
  that reference with nearby claims.
- No existing COMMAND is dropped.

### Tests added

- `test_backtick_strict_path_emitted_as_both_command_and_local_path`
- `test_backtick_command_not_treated_as_path`
- `test_backtick_bare_filename_with_extension_is_path`
- `test_backtick_unsupported_extension_stays_command_only`
- `test_backtick_path_with_space_not_treated_as_path`

---

## Out of scope (deliberately not changed)

- Nested frontmatter flattening (`metadata.last_updated`).
- E1 claim pattern expansion (thresholds, absolute metrics, qualitative
  claims).
- E4 date source groups (G1a/G1b/G2/G3).
- Finding schema (still v1; additive fields unchanged).
- Severity levels.

---

## Ratification status

This proposal is **implemented in code** on the branch but is **not
ratified** as a formal contract version. The v1.0 file remains the
authoritative contract until a separate ratification step.
