# skill-evidence-lint

A Python CLI that statically inspects an AI Skill directory's `SKILL.md`
and checks whether **English effect claims** are backed by **evidence
references inside the same Markdown context** (same paragraph or same list item).

> This is a *coverage* linter. It does **not** verify that a claim is true,
> does not download evidence, and does not open or execute any referenced file.
> Finding a reference is never proof that the evidence is valid.

## Install

Requires Python 3.11 or newer.

The package has not yet been published to PyPI. Install from source:

```bash
git clone https://github.com/xiaohei52056/skill-evidence-lint.git
cd skill-evidence-lint
python -m pip install .
```

(For development, `python -m pip install -e ".[dev]"` installs pytest and ruff as well.)

Once a release is published to PyPI, the install command will simply be:

```bash
pip install skill-evidence-lint   # not yet available
```

## Usage

```bash
# Point at a Skill directory containing SKILL.md, or at the SKILL.md file itself:
skill-evidence-lint path/to/skill-directory
skill-evidence-lint path/to/skill-directory/SKILL.md
```

If a file is passed directly, its basename must be exactly `SKILL.md`; any
other file is rejected.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Check completed. E1/E2 findings are reports, never failures. |
| `2` | Invalid input: path missing, no `SKILL.md`, wrong file name. |
| `3` | Unexpected internal error (a concise summary is printed to stderr, no traceback). |

## What it checks

- **C1** — candidate English effect claims. Four conservative patterns:
  `<verb> … by <number><unit>` ("reduces time by 40%"),
  `achieve/deliver/ensure/guarantee/provide <number><unit>`,
  `<number><unit> faster|slower|less|more|…`,
  and `zero|near-zero <config|setup|latency|downtime|errors|friction|overhead>`.
  Negated and hypothetical sentences are filtered out.
- **E1** — a C1 candidate has no recognized evidence reference in its
  *own* paragraph or *own* enclosing list item. URLs and local paths clear
  E1; backtick command examples do not. Adjacent paragraphs, shared headings,
  or a global "Evidence" section never clear E1.
- **E2** — a local-path reference resolves outside the Skill root, does not
  exist, or is a symlink pointing outside the root. URLs are syntax-checked
  only and are never fetched.

## Product decisions (fixed)

- **Strict evidence association**: same paragraph or same list item only.
- **English only for now**: Chinese claims are not candidates and do not enter
  the coverage denominator.
- **CI reports, never blocks**: E1/E2 findings still exit `0`.
- **Safe and read-only**: the tool never executes Skills, commands, or
  evidence scripts; it never accesses the network. Local evidence paths are
  confined to the Skill root (no `..` traversal, no symlink escape).

## Not implemented in v0.1

E3–E7, auto-fix, LLM truthfulness judgment, network URL reachability, JSON
reporting, multi-file batch checking, and a published GitHub Action.

## Evaluation status

A hand-annotated evaluation against 17 public `SKILL.md` files from two
permissively-licensed GitHub repos (13 Apache-2.0 from `anthropics/skills`,
4 MIT from `obra/superpowers`; pinned commits recorded in
`tests/fixtures/c1_eval/manifest.json`) found **zero in-scope positive
claims** in those documents — the corpus is overwhelmingly procedural, and
C1 also produced **zero false positives** on it. Because the in-scope
denominator is zero, neither real-world precision nor recall can be computed
from this sample. A separate synthetic fixture of 13 in-scope spans was
caught 13/13. See `docs/c1-evaluation.md` for the full audit.

Five additional Anthropic skills (`docx`, `pdf`, `pptx`, `xlsx`,
`doc-coauthoring`) were examined during license review but are **not**
shipped in the fixtures: four carry a proprietary "all rights reserved"
license that forbids redistribution, and one ships with no license at all.

## Development

```bash
py -3.12 -m pip install -e ".[dev]"
py -3.12 -m pytest -ra
py -3.12 -m ruff check .
skill-evidence-lint --help
```

## License

MIT. See [LICENSE](LICENSE).

The hand-annotated C1 evaluation samples under `tests/fixtures/c1_eval/real/`
are third-party documents redistributed under their upstream licenses
(Apache-2.0 for the `anthropics/skills` files, MIT for the `obra/superpowers`
files); see `tests/fixtures/c1_eval/manifest.json` and the bundled upstream
`LICENSE_*.txt` copies for provenance. They are not part of the runtime
package.
