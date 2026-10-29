# Phase 2 Plan: Reliability and Reproducibility Signals

## Goal

Move `skill-evidence-lint` from a working v0.1.0 prototype toward a trustworthy, integration-ready static checker without expanding beyond its core question: whether detectable effect claims have clearly locatable evidence references.

This plan is based on the current Python implementation (Python 3.11+) and supersedes any earlier TypeScript/npm-oriented architecture sketches.

## Non-negotiable boundaries

- Deterministic static analysis only; no LLM judge.
- Never execute a Skill, shell command, or evidence script.
- Never fetch URLs or make network requests during a check.
- Do not open/read evidence files to decide whether a claim is true.
- Do not produce a composite quality score.
- Prefer conservative findings over speculative semantic judgments.
- Findings remain report-only by default; no new CI failure behavior without an explicit contract.

## Workstreams

### P2.1 — Establish a regression baseline (first)

- Run the existing pytest and Ruff suites before changing behavior.
- Review C1, E1, and E2 edge cases and document any known gaps.
- Add regression fixtures for Markdown context boundaries, inline code, URLs, missing paths, traversal attempts, and symlink escapes where supported.
- Preserve deterministic finding order and current exit-code behavior.

**Exit criteria:** the full test/lint suite passes, and every behavior change has a focused regression test.

### P2.2 — Add E3 reproducibility-cue reporting

E3 should report whether a numeric effect claim has a recognizable static reproducibility cue in its own allowed Markdown context. Cues may include:

- an inline or fenced command that looks like a command (detection only; never execute it);
- an explicit input/dataset/configuration description; or
- an explicit metric-definition phrase.

The rule must not claim that a benchmark actually ran or that a result is reproducible. It only reports the presence or absence of a cue. A generic backtick span must not automatically count as a command.

**Exit criteria:** rule semantics and examples are documented; positive and negative cases are covered by unit and acceptance tests; output remains deterministic.

### P2.3 — Define a stable JSON report contract

- Introduce a versioned schema identifier.
- Include claims, references, findings, and summary counts with stable field names.
- Emit valid JSON even when there are no findings.
- Keep existing human-readable CLI output and exit codes compatible unless a documented migration is required.

**Exit criteria:** schema tests cover empty and populated reports, and documentation includes a representative output.

### P2.4 — Reassess CI integration

- Keep the existing test workflow read-only.
- Consider native GitHub annotations or a composite Action only after the CLI output contract is stable.
- Default to advisory/report-only behavior.
- Do not publish a first-party Action or promise PR annotations until implemented and tested.

## Proposed sequence

1. Capture the baseline: pytest, Ruff, and current behavior review.
2. Finalize E3 semantics before implementation.
3. Implement E3 with focused tests.
4. Design and test versioned JSON output.
5. Update README and only then evaluate GitHub integration.

## Out of scope for this phase

- LLM-based claim interpretation or truth judgments.
- URL reachability checks.
- Reading evidence contents.
- Automatic fixes.
- Broad multilingual claim detection.
- E4–E7 until real calibration examples justify their false-positive risk.

## Release discipline

Do not claim real-world precision/recall from a corpus without in-scope positive examples and manual labels. Synthetic fixtures demonstrate tested behavior, not broad real-world accuracy. Keep evaluation limitations visible in release notes and README.
