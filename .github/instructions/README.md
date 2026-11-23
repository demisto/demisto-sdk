# GitHub Copilot instruction files

This directory contains **path-scoped** Copilot instructions that
complement the repo-wide [`../copilot-instructions.md`](../copilot-instructions.md).
Each file declares an `applyTo` glob in its YAML front-matter; Copilot
loads it for any file in the workspace that matches.

> Reference: GitHub Copilot supports a top-level
> `.github/copilot-instructions.md` for the whole repo, plus
> `.github/instructions/*.instructions.md` files with an `applyTo` glob
> for finer-grained scoping.

## Layout

| File | Scope (`applyTo`) |
|---|---|
| [`../copilot-instructions.md`](../copilot-instructions.md) | Whole repo (default) |
| [`commands.instructions.md`](commands.instructions.md) | `demisto_sdk/commands/**/*.py` |
| [`common-helpers.instructions.md`](common-helpers.instructions.md) | `demisto_sdk/commands/common/**/*.py` |
| [`content-graph.instructions.md`](content-graph.instructions.md) | `demisto_sdk/commands/content_graph/**/*.py` |
| [`validators.instructions.md`](validators.instructions.md) | `demisto_sdk/commands/validate/**/*.py` (new framework) |
| [`legacy-validators.instructions.md`](legacy-validators.instructions.md) | `demisto_sdk/commands/common/hook_validations/**/*.py`, `validate/old_validate_manager.py`, `validate/tests/old_validators_test.py` |
| [`integration-authoring.instructions.md`](integration-authoring.instructions.md) | `commands/{init,split,generate_integration,generate_yml_from_python,openapi_codegen,postman_codegen,generate_unit_tests,integration_diff}/**/*.py` |
| [`lint.instructions.md`](lint.instructions.md) | `commands/lint/**/*.py`, `commands/xsoar_linter/**/*.py`, `commands/pre_commit/resources/pylint_plugins/**/*.py` |
| [`scripts.instructions.md`](scripts.instructions.md) | `demisto_sdk/scripts/**/*.py` |
| [`tests.instructions.md`](tests.instructions.md) | `**/tests/**/*.py`, `**/*_test.py`, `conftest.py` |
| [`test-suite.instructions.md`](test-suite.instructions.md) | `TestSuite/**/*.py` |
| [`e2e-tests.instructions.md`](e2e-tests.instructions.md) | `tests_end_to_end/**/*.py` |
| [`ci.instructions.md`](ci.instructions.md) | CI YAML and pre-commit configs |
| [`docs-and-changelog.instructions.md`](docs-and-changelog.instructions.md) | `**/*.md`, `.changelog/**/*.yml`, `docs/**/*` |

## Resolution order

When Copilot processes a file, it merges:

1. The repo-wide [`../copilot-instructions.md`](../copilot-instructions.md).
2. Every `*.instructions.md` whose `applyTo` glob matches the file path.

The more specific files **add to** rather than replace the repo-wide ones.
If two files contradict, the more specific wins.

## Adding a new instruction file

1. Create `.github/instructions/<topic>.instructions.md`.
2. Add a YAML front-matter block:
   ```markdown
   ---
   applyTo: "<glob>"
   ---
   ```
   `applyTo` accepts a single glob or a comma-separated list.
3. Cross-link from this README and from the repo-wide instructions where
   relevant.
4. Keep instructions **declarative and conventions-focused**. Don't paste
   long code blocks unless they are canonical templates.

## Testing what Copilot sees

- In VS Code with GitHub Copilot Chat, ask: "What instructions are
  active for this file?" Copilot will list the matching files.
- The Copilot coding agent and Copilot code review honour the same
  resolution rules.

## Conventions for writing rules here

- Use **bulleted, imperative rules** ("Use X", "Do not Y").
- Group "Hard rules" separately from "Conventions" so AI assistants can
  prioritise.
- Cross-link to the actual code or config that enforces a rule (ruff
  config, mypy config, pre-commit hook). This keeps the doc honest when
  the underlying rule changes.
- When updating an instruction file, also update the repo-wide
  [`../copilot-instructions.md`](../copilot-instructions.md) if the
  change affects something globally relevant.
