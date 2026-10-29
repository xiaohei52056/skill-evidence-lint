# Changelog

This project follows [Keep a Changelog](https://keepachangelog.com/)
loosely. Versions are tagged on `main`; this file records notable changes
on the `phase-2/quality-and-e3` branch before the first post-0.1.0
release.

## Unreleased (phase-2/quality-and-e3)

### Added

- **E3** `evidence-no-repro-steps`: numeric effect claims must be
  adjacent to a recognizable command, input/dataset/config, or
  metric-definition cue. Fenced command blocks directly adjacent to a
  claim count; environment-only commands (`python --version`) do not.
- **E5** `evidence-section-empty`: `## Evidence` / `## Benchmark` /
  `## Results` / `## Evaluation` sections that are empty or placeholder-
  only.
- **E6** `evidence-url-unreachable` (info, offline): flags malformed
  URLs, reserved example domains (`example.com/.org/.net/.edu`), and
  obvious template tokens (`your-domain`, `replace_me`, `{{...}}`).
  Never makes a network request.
- **E7** `evidence-path-ambiguous` (info, offline): local path
  references containing `*` within a single segment; `?` and `**` are
  treated literally and fall through to E2.
- **E4** `evidence-stale` (info, offline): compares declared date
  metadata on referenced evidence files against the Skill's frontmatter
  baseline date. See `docs/e4-contract.md` for the frozen v1.0 contract.
  E4 is **claim-scoped**: it only evaluates `(claim, evidence_ref)` pairs
  where E1 recognizes an effect claim and the reference shares the same
  Markdown context. E2 and E4 are mutually exclusive per pair (E2 owns
  missing/escaped paths; E4 only runs on files that exist inside the Skill
  root).
- **JSON report output**: `skill-evidence-lint --format json <path>`.

### E4 compatibility notes (implemented; contract v1.1 proposal)

Two backward-compatible improvements were added during calibration:

1. **Skill baseline field `last_updated`** is now recognized. The skill-
   side priority is `date → updated → last_updated → last_modified →
   version_date`. Only top-level frontmatter fields are read; nested
   `metadata.*` is not flattened.
2. **Backtick-wrapped strict relative paths** (e.g. `` `examples/foo.md` ``)
   are now emitted as a `LOCAL_PATH` reference in addition to being
   emitted as `COMMAND`. Commands with spaces, shell flags, or
   unsupported extensions remain `COMMAND` only. Path existence, root
   containment, symlink, size, and encoding checks are unchanged.

These are documented in `docs/e4-contract-v1.1-proposal.md`. They are
**proposed v1.1 changes**, not yet ratified; the frozen v1.0 contract in
`docs/e4-contract.md` is unchanged. All existing strict date parsing,
placeholder rejection, E2/E4 mutual exclusion, and finding schema
behavior is unchanged.

### Calibration status disclosure

- **Synthetic fixtures:** 24 hand-authored samples (8 expected-e4,
  5 expected-no-e4, 11 out-of-scope). 8/8 positives detected, 0 false
  positives, 0 false negatives. These prove E4 logic on its designed
  decision branches.
- **Real public corpus:** 29 SKILL.md files across 13+ independent
  sources were inspected. None contained an E1-recognized effect claim
  paired with a dated local evidence file. E4 produced 0 findings (and
  0 false positives) on all of them.
- **Real expected-e4: 0.** Formal real TP/FP/FN is n/a. E4's positive
  path has not been exercised on a real evidence-backed Skill; this is
  an ecosystem gap (public skills are procedural instructions, not
  evidence reports), not a code defect.

### Changed — JSON schema (additive, no version bump)

The JSON report schema ID remains **`skill-evidence-lint.report.v1`**.
The E4 integration makes the following *additive* changes:

1. `summary.by_rule` gains a new key `"E4"`. It is always present (even
   when the count is 0). Previously the key set was `{E1,E2,E3,E5,E6,E7}`;
   it is now `{E1,E2,E3,E4,E5,E6,E7}`.
2. `findings[]` objects whose `rule_id == "E4"` gain four optional
   fields: `evidence_path`, `evidence_date`, `skill_date`,
   `days_diff`. These fields do **not** appear on findings of any other
   rule (they are not emitted as `null`).

This is an additive extension under the v1 contract. Consumers that:

- ignore unknown fields and tolerate new `by_rule` keys — compatible.
- strictly validate `by_rule` against a fixed key set — will need to
  add `"E4"` to their allow-list.

A strict breaking change (renaming, removing, or retyping existing
fields) would bump the schema ID to `v2`. No such change has been made.

### Dependencies

- `pyyaml>=6.0` is a runtime dependency (third-party package,
  distributed via PyPI) used to parse YAML frontmatter. It is not part
  of the Python standard library.
