---
applyTo: "demisto_sdk/scripts/**/*.py"
---

# Copilot instructions — `demisto_sdk/scripts/`

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md).

[`demisto_sdk/scripts/`](../../demisto_sdk/scripts) holds **standalone
console-script entry points** that are exposed via `[tool.poetry.scripts]`
in [`pyproject.toml`](../../pyproject.toml). They are typically wired into
[`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml) so that downstream
content repos can consume them as pre-commit hooks.

Current entry points (see [`pyproject.toml`](../../pyproject.toml)):

| Script | Module |
|---|---|
| `sdk-changelog` | [`changelog/changelog.py`](../../demisto_sdk/scripts/changelog/changelog.py) |
| `merge-coverage-report` | `merge_coverage_report:main` |
| `merge-pytest-reports` | [`merge_pytest_reports.py`](../../demisto_sdk/scripts/merge_pytest_reports.py) |
| `validate-content-path` | [`validate_content_path.py`](../../demisto_sdk/scripts/validate_content_path.py) |
| `validate-conf-json` | [`validate_conf_json.py`](../../demisto_sdk/scripts/validate_conf_json.py) |
| `init-validation` | [`init_validation_script.py`](../../demisto_sdk/scripts/init_validation_script.py) |
| `validate-deleted-files` | [`validate_deleted_files.py`](../../demisto_sdk/scripts/validate_deleted_files.py) |
| `validate-file-permission-changes` | [`validate_file_permission_changes.py`](../../demisto_sdk/scripts/validate_file_permission_changes.py) |
| `prevent-mypy-global-ignore` | [`prevent_mypy_global_ignore.py`](../../demisto_sdk/scripts/prevent_mypy_global_ignore.py) |
| `generate-command-docs` | [`generate_commands_docs.py`](../../demisto_sdk/scripts/generate_commands_docs.py) |
| `validate-validation-config-file` | [`validate_validation_config_file.py`](../../demisto_sdk/scripts/validate_validation_config_file.py) |

## Conventions

- Each script has a top-level `def main() -> int | None:` function,
  registered as `<script-name> = "demisto_sdk.scripts.<module>:main"`.
- Use **Typer** for the CLI when there are options. Trivial scripts may
  use `sys.argv` directly, but Typer is preferred for consistency.
- **Exit codes**:
  - `0` on success.
  - Non-zero on failure (typically `1`). For pre-commit hooks, returning
    non-zero blocks the commit — make sure failure modes are intentional.
- **Filenames passed by pre-commit** arrive on `argv` (or via Typer
  `Argument(..., metavar="FILES...")`). Honour the convention; don't
  re-discover files from the working tree if filenames were passed.
- **No interactive prompts.** Scripts run in CI and pre-commit; they must
  be fully non-interactive. If you need confirmation, gate behind a
  `--yes` / env-var flag.
- **Logging** — use the project logger. For pre-commit hooks, prefer
  concise, single-line messages and rely on the exit code to signal
  failure.
- **Tests** live in
  [`demisto_sdk/scripts/tests/`](../../demisto_sdk/scripts/tests) (see
  [`changelog/tests/`](../../demisto_sdk/scripts/changelog/tests) for an
  example with sub-package tests). Unit-test the `main()` function via
  `runner = typer.testing.CliRunner()` or by calling `main` directly with
  a patched `argv`.

## When you add a new script

1. Add the module under `demisto_sdk/scripts/<your_script>.py`.
2. Implement `def main() -> int:`.
3. Register it in `[tool.poetry.scripts]` in
   [`pyproject.toml`](../../pyproject.toml).
4. If it should run as a pre-commit hook in **content** repos, register
   it in [`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml).
5. If it should run as a pre-commit hook in **this repo**, register it in
   [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml).
6. Add tests under `demisto_sdk/scripts/tests/<your_script>_test.py`.
7. Document it in [`README.md`](../../README.md) if it is user-facing.

## Hard rules (in addition to the repo-wide ones)

- **No `print()`.** Use `logger`. (Ruff `T20`.)
- **No `sys.exit(0)` / `sys.exit(1)` from arbitrary places.** Return from
  `main()` and let Typer / the entry-point machinery exit.
- **No file writes outside the working tree** (or the user's
  `~/.demisto-sdk/` if the script is genuinely user-state).
- **Do not import from `TestSuite/` or `tests_end_to_end/`** — they are
  excluded from the wheel and are unavailable when the script runs from
  an installed `demisto-sdk` package.
