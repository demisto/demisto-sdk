# GitHub Copilot Instructions — `demisto-sdk`

These instructions tell GitHub Copilot (and other AI coding assistants that
respect this file) how to write, modify, and review code in this repository.
They apply to **every file in the repo**, unless a more specific
[`.github/instructions/*.instructions.md`](.github/instructions) file overrides
them for a given path.

> **Audience:** This file is read by Copilot Chat, Copilot code review, the
> Copilot coding agent, and similar AI assistants. Authoritative human docs
> live in [`README.md`](../README.md), [`CONTRIBUTION.md`](../CONTRIBUTION.md),
> [`docs/development_guide.md`](../docs/development_guide.md), and
> [`pyproject.toml`](../pyproject.toml).

---

## 1. What this repository is

[`demisto-sdk`](../README.md) is a Python library and CLI used to develop,
validate, format, generate, upload, download, and otherwise manage
**Cortex XSOAR / Cortex XSIAM content** (integrations, scripts, playbooks,
incident/indicator fields, layouts, dashboards, modeling rules, parsing rules,
correlation rules, etc.).

It is consumed in three primary ways:

1. **CLI** — `demisto-sdk <command> <args>` (entry point in
   [`demisto_sdk/__main__.py`](../demisto_sdk/__main__.py), built with
   [Typer](https://typer.tiangolo.com/)).
2. **Library** — imported by the
   [`content`](https://github.com/demisto/content) repo, by partners, and by
   internal tooling.
3. **`pre-commit` hooks** — see
   [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) and the
   [pre_commit](../demisto_sdk/commands/pre_commit) command.

Suggestions Copilot makes must keep all three usage modes working.

---

## 2. Hard requirements (do not violate)

When generating code, Copilot **must**:

1. **Target Python 3.9–3.12.** Code must be syntactically valid on
   `python_requires = ">=3.9,<3.13"` (see [`pyproject.toml`](../pyproject.toml)).
   - Do not use `match`/`case`, PEP 695 generics, `type` statement, `Self`
     from `typing`, or other 3.10+/3.11+/3.12+ syntax in non-test code.
   - For `StrEnum`, **always** import from
     [`demisto_sdk.commands.common.StrEnum`](../demisto_sdk/commands/common/StrEnum.py)
     (not `enum.StrEnum`, which is 3.11+).
2. **Never import the banned modules listed in
   [`pyproject.toml`](../pyproject.toml) under
   `[tool.ruff.lint.flake8-tidy-imports.banned-api]`.** Use the indicated
   replacement:
   | Banned import | Use instead |
   |---|---|
   | `import json`, `json5`, `orjson`, `ujson` | `JSON_Handler` from [`demisto_sdk.commands.common.handlers`](../demisto_sdk/commands/common/handlers/__init__.py) |
   | `import ruamel.yaml` | `YAML_Handler` from [`demisto_sdk.commands.common.handlers`](../demisto_sdk/commands/common/handlers/__init__.py) |
   | `import logging`, `import loguru` | the project logger from [`demisto_sdk.commands.common.logger`](../demisto_sdk/commands/common/logger.py) |
   | `from git import Repo` | [`GitUtil`](../demisto_sdk/commands/common/git_util.py) |
   | `distutils.version.*`, `packaging.version.LooseVersion` | `packaging.version.Version` |
3. **Never use `print()`, `pprint`, `pdb.set_trace()`, `breakpoint()`, or
   bare `logging.*`.** All user-facing output goes through
   [`logger`](../demisto_sdk/commands/common/logger.py) (`logger.info`,
   `logger.warning`, `logger.error`, `logger.debug`, `logger.success`).
   Ruff rules `T10` and `T20` enforce this.
4. **Use `pathlib.Path`, not `os.path.*`.** Ruff rules `PTH107`, `PTH110`,
   `PTH113`, `PTH119` are enabled.
5. **Do not silently widen mypy ignores.** A pre-commit hook
   ([`prevent-mypy-global-ignore`](../demisto_sdk/scripts/prevent_mypy_global_ignore.py))
   blocks new global `# type: ignore` and module-level
   `# mypy: ignore-errors`. Use targeted ignores
   (`# type: ignore[error-code]`) and prefer fixing the underlying type issue.
6. **Pydantic v1 only.** The repo pins `pydantic = "^1.10"`. Do **not**
   suggest Pydantic v2-only APIs (`model_validator`, `ConfigDict`,
   `model_dump`, `RootModel`, etc.). Use v1 equivalents (`@validator`,
   `class Config`, `.dict()`, `__root__`). The migration is tracked in
   [`plans/pydantic-v2-migration.md`](../plans/pydantic-v2-migration.md);
   do not pre-empt it.
7. **Respect the `exclude` list of the build.** Files under `TestSuite/`,
   `tests_end_to_end/`, `**/tests/**`, `**/test_data/**`, and
   `**/test_files/**` are excluded from the wheel. Production code in
   `demisto_sdk/` must not import from them.
8. **All new public functions, methods and classes must have type
   annotations** and a short docstring. `mypy` runs with
   `check_untyped_defs = true` (see [`pyproject.toml`](../pyproject.toml)).

If a user request would require violating any of the above, Copilot should
push back and propose a compliant alternative instead of generating
non-compliant code.

---

## 3. Repository layout

```
demisto-sdk/
├── demisto_sdk/                        # Main package (shipped on PyPI)
│   ├── __main__.py                     # Typer CLI entry point (`demisto-sdk` script)
│   ├── commands/                       # One sub-package per CLI command
│   │   ├── common/                     # Shared helpers, constants, logger, git, handlers, schemas
│   │   ├── content_graph/              # Neo4j-backed content graph (objects/, parsers/, interface/, strict_objects/)
│   │   ├── validate/                   # New validation framework (validators/<PREFIX>_validators/<CODE>_*.py)
│   │   ├── format/                     # Auto-format content files
│   │   ├── pre_commit/                 # `demisto-sdk pre-commit` orchestrator
│   │   ├── upload/, download/          # XSOAR/XSIAM transport
│   │   ├── generate_*/                 # Code, docs, test, unit-test, integration generators
│   │   ├── lint/, xsoar_linter/        # Linters for content code
│   │   ├── init/, split/, prepare_content/, zip_packs/  # Authoring & packaging tools
│   │   └── ... (see README §Commands)
│   ├── scripts/                        # Standalone entry points (sdk-changelog, validate-* etc.)
│   ├── tests/                          # Cross-cutting tests (workflow, logger, ...)
│   └── utils/                          # Misc utilities
├── TestSuite/                          # In-repo fixture builders used by unit tests (Pack, Integration, Playbook, ...)
├── tests_end_to_end/                   # Live XSOAR / XSIAM / XSOAR-SaaS e2e tests
├── docs/                               # Human docs (development_guide.md, demisto-sdk-docker.md, ...)
├── .github/                            # CI workflows, actions, Copilot instructions (this directory)
├── .gitlab/, .gitlab-ci.yml            # Internal mirror CI
├── .pre-commit-config.yaml             # Pre-commit hooks for *this* repo
├── .pre-commit-hooks.yaml              # Hooks this repo *exposes* to consumers
├── pyproject.toml, poetry.lock         # Poetry-managed deps & tool configs (ruff, mypy, vulture)
└── plans/                              # Long-running refactor plans
```

When deciding where to put new code, prefer:

- A **command** under [`demisto_sdk/commands/<name>/`](../demisto_sdk/commands)
  with a `<name>_setup.py` (Typer registration), `README.md`, and `tests/`.
- A **shared helper** under
  [`demisto_sdk/commands/common/`](../demisto_sdk/commands/common) only if it
  is genuinely cross-command. Look for an existing helper in
  [`tools.py`](../demisto_sdk/commands/common/tools.py),
  [`constants.py`](../demisto_sdk/commands/common/constants.py),
  [`git_util.py`](../demisto_sdk/commands/common/git_util.py), or the
  [`handlers/`](../demisto_sdk/commands/common/handlers) package before adding
  a new one.

---

## 4. Build, install, run, test

The repo is managed by **Poetry** (`poetry.toml` pins `virtualenvs.in-project = true`).

### Setup
```bash
poetry install
poetry run pre-commit install
```

### Common dev loops
```bash
# Run the CLI from your checkout
poetry run demisto-sdk <command> --help

# Lint + format + type-check (the same hooks CI runs)
poetry run pre-commit run --all-files

# Targeted ruff / mypy
poetry run ruff check demisto_sdk
poetry run ruff format demisto_sdk
poetry run mypy demisto_sdk

# Tests
poetry run pytest demisto_sdk -x
poetry run pytest demisto_sdk/commands/validate/tests -x
poetry run pytest -k "test_name_substring"
```

> Copilot should suggest these exact commands when the user asks "how do I
> run X". Do **not** suggest `tox`, `flake8`, `isort`, or `black` directly —
> the project uses `ruff` for all of those, and `pre-commit` orchestrates
> `mypy`.

### CI
- GitHub Actions: see [`.github/workflows/`](workflows). The main workflow
  is [`on-push.yml`](workflows/on-push.yml).
- GitLab CI: see [`.gitlab-ci.yml`](../.gitlab-ci.yml) and
  [`.gitlab/`](../.gitlab).
- Releases:
  [`release-to-pypi.yml`](workflows/release-to-pypi.yml) and
  [`sdk-release.yml`](workflows/sdk-release.yml).

---

## 5. Coding conventions

### General Python style
- **Formatter:** `ruff format` (Black-compatible). Line length is *not*
  enforced (`E501` is ignored), but keep lines reasonable (~100 chars).
- **Imports:** sorted by `ruff` (`I` rule). Absolute imports rooted at
  `demisto_sdk.` are preferred for production code; relative imports are
  acceptable within a single sub-package.
- **Typing:**
  - Prefer `from __future__ import annotations` in new modules to enable
    forward references and `X | Y` style in annotations (still 3.9-safe at
    runtime because annotations are strings).
  - Use `typing.Optional[X]` / `Union[X, Y]` in annotations that are
    *evaluated at runtime* (e.g. Pydantic v1 fields, Typer options).
  - Use `Iterable`, `Sequence`, `Mapping` from `typing` for parameters;
    return concrete `list`, `dict`, `tuple` when ownership is transferred.
- **Docstrings:** Google-style is the de facto standard in this repo
  (`Args:`, `Returns:`, `Raises:`). Keep them short.
- **Errors:** Raise `ValueError`, `RuntimeError`, or a domain-specific
  exception from
  [`demisto_sdk.commands.common.errors`](../demisto_sdk/commands/common/errors.py)
  rather than generic `Exception`. Log at `error` level *and* re-raise — do
  not swallow exceptions.

### Logging
```python
from demisto_sdk.commands.common.logger import logger

logger.info("Doing X for <green>{path}</green>", path=path)   # loguru-style markup
logger.warning("Skipping {item} because ...", item=item)
logger.error("Failed to ...: {err}", err=err)
```
Do **not** import `logging` or `loguru` directly. Loguru-style `<color>...
</color>` markup is supported; f-strings are also fine but prefer
parameterised messages so they show up cleanly in structured logs.

### File I/O — JSON / YAML
```python
from demisto_sdk.commands.common.handlers import (
    DEFAULT_JSON_HANDLER as json,
    DEFAULT_YAML_HANDLER as yaml,
)

data = json.load(path.open())
yaml.dump(data, path.open("w"))
```
Never `import json` / `import yaml` / `import ruamel.yaml` / `import ujson`
/ `import orjson` directly.

### Git
```python
from demisto_sdk.commands.common.git_util import GitUtil
git = GitUtil()
```
Never `from git import Repo`.

### Paths and constants
- Use [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html) — not
  `os.path`, not `open(str, ...)` with manual string joins.
- The content root path comes from
  [`demisto_sdk.commands.common.content_constant_paths.CONTENT_PATH`](../demisto_sdk/commands/common/content_constant_paths.py),
  which respects the `DEMISTO_SDK_CONTENT_PATH` env var.
- Reusable constants live in
  [`demisto_sdk.commands.common.constants`](../demisto_sdk/commands/common/constants.py).
  Reuse existing ones; do not duplicate values.

### Environment variables
The SDK is heavily configured by env vars. When suggesting new ones, follow
the `DEMISTO_SDK_*` or `DEMISTO_*` / `XSIAM_*` prefix convention used by
existing variables in [`README.md`](../README.md). Read them through
`os.environ.get(...)` (or `python-dotenv` for the `.env` file at content root,
already loaded in [`__main__.py`](../demisto_sdk/__main__.py)).

### Click vs Typer
The CLI is migrating from `click` to **Typer**. New commands and new
subcommands must be written in **Typer** (see
[`demisto_sdk/commands/content_graph/content_graph_setup.py`](../demisto_sdk/commands/content_graph/content_graph_setup.py)
and [`demisto_sdk/__main__.py`](../demisto_sdk/__main__.py) for examples).
Do not introduce new `click.command` decorators.

---

## 6. Testing conventions

- Framework: **pytest** with `pytest-mock`, `pytest-subprocess`,
  `requests-mock`, `pytest-freezegun`, `pytest-datadir-ng`,
  `pytest-loguru`. Configured in [`pyproject.toml`](../pyproject.toml) and
  [`conftest.py`](../conftest.py).
- Layout: tests sit next to the code they cover, in a `tests/`
  sub-directory: `demisto_sdk/commands/<cmd>/tests/<thing>_test.py`.
- File names must match `*_test.py` (the `name-tests-test` pre-commit hook
  enforces this — `test_*.py` is **not** accepted in production sub-trees).
- Use builders from [`TestSuite/`](../TestSuite) to construct fake content
  objects (`Pack`, `Integration`, `Script`, `Playbook`, `Repo`, ...). Don't
  hand-craft YAML/JSON in tests when a builder exists.
- Network calls **must** be mocked (`requests-mock`, `mocker.patch`).
  Docker calls should be mocked unless the test is explicitly marked.
- Do not write to `~`, `/tmp`, or the repo root from a test — use
  `tmp_path` / `tmp_path_factory`.
- Aim for tests that are deterministic, hermetic and fast (< 1 s each).
  Mark slow / integration tests appropriately and keep them out of the
  default pytest run.
- New code must come with tests covering the happy path **and** at least one
  failure path. Coverage is reported via `coverage` and Coveralls.

End-to-end tests live in [`tests_end_to_end/`](../tests_end_to_end) and
require a live XSOAR / XSIAM tenant. Don't add unit-test-style assertions
there; instead keep them under the relevant `commands/<cmd>/tests/`.

---

## 7. Pull requests, changelog, commits

1. **Branch from `master`**, open a PR against `master`. Use the
   [PR template](pull_request_template.md).
2. **Add a changelog fragment** for any user-visible change:
   ```bash
   poetry run sdk-changelog --init -n <issue-or-pr-number>
   ```
   This creates a YAML file in [`.changelog/`](../.changelog). Pick the
   correct `type` (`breaking`, `feature`, `fix`, `internal`). Internal-only
   refactors should still get an `internal` entry. The release tooling
   ([`demisto_sdk/scripts/changelog/`](../demisto_sdk/scripts/changelog))
   assembles `CHANGELOG.md` from these fragments.
3. **Commits** should be small, atomic, and have an imperative subject
   ("Add X", "Fix Y") < 72 chars. Squash-merging is the default.
4. **CODEOWNERS** ([`.github/CODEOWNERS`](CODEOWNERS)) auto-assigns
   reviewers. Don't request reviewers manually unless asked.
5. The PR must be green on:
   - `pre-commit` (ruff, ruff-format, mypy, toml-sort, validate-pyproject,
     poetry-check, generate-command-docs, validate-validation-config-file,
     misc hygiene hooks).
   - The full `pytest` suite on supported Python versions.
   - Any `validate-content-path`, `validate-conf-json`,
     `validate-deleted-files`, `validate-file-permission-changes`,
     `prevent-mypy-global-ignore` checks defined in
     [`pyproject.toml`](../pyproject.toml).

---

## 8. Adding a new CLI command

Follow the pattern used by existing commands (see
[`docs/development_guide.md`](../docs/development_guide.md) and the
[`run_playbook`](../demisto_sdk/commands/run_playbook),
[`reattach`](../demisto_sdk/commands/reattach) commands as compact examples):

1. Create `demisto_sdk/commands/<your_command>/`.
2. Implement the logic in `<your_command>.py` as a class (e.g.
   `MyCommand`) — keep it importable as a library.
3. Create `<your_command>_setup.py` exposing a Typer `app` (or
   `@app.command()` function) that parses CLI args and instantiates the
   class.
4. Register it in [`demisto_sdk/__main__.py`](../demisto_sdk/__main__.py).
5. Add a `README.md` describing flags & examples. The
   `generate-command-docs` pre-commit hook runs whenever a `*_setup.py`
   changes — let it regenerate downstream docs.
6. Add `tests/<your_command>_test.py`.
7. Argument naming convention (from
   [`docs/development_guide.md`](../docs/development_guide.md)):
   `-i/--input`, `-o/--output`, `--insecure`, `--no-graph` for graph-opt-out,
   `--console-log-threshold` etc. Reuse existing flag names where the
   semantics match.
8. If the command modifies content, also expose the equivalent fix in
   [`format`](../demisto_sdk/commands/format) when feasible.

---

## 9. Adding a new validator

Validators live under
[`demisto_sdk/commands/validate/validators/<PREFIX>_validators/`](../demisto_sdk/commands/validate/validators)
where `<PREFIX>` is a 2-letter content-type code (`PB` for playbook,
`IN` for integration, `SC` for script, `RM` for README, `IM` for image,
`GR` for graph-relations, `BA`/`BC` for cross-cutting "best-practice" /
"backwards-compat", etc.).

Naming and class layout (see
[`PB100_is_no_rolename.py`](../demisto_sdk/commands/validate/validators/PB_validators/PB100_is_no_rolename.py)
as a canonical example):

```python
from __future__ import annotations
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook  # or Union[...] for multi-type validators


class IsNoRolenameValidator(BaseValidator[ContentTypes]):
    error_code = "PB100"  # Must be globally unique; matches the file name prefix
    description = "<one-sentence what this validates>"
    rationale = "<why this matters to a content author>"
    error_message = "The playbook '{playbook_name}' ... please ..."  # actionable
    related_field = "rolename"  # YAML/JSON key surfaced to the user

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(playbook_name=ci.name),
                content_object=ci,
            )
            for ci in content_items
            if ci.data.get("rolename")
        ]
```

Rules:

- **Filename = `<CODE>_<snake_case_name>.py`** and the class name is the
  CamelCase equivalent ending in `Validator`.
- **`error_code` must be unique** and must match the filename prefix. If
  the validator can autofix the issue, also implement
  `fix(self, content_item)` and set `is_auto_fixable = True`.
- Add it to [`sdk_validation_config.toml`](../demisto_sdk/commands/validate/sdk_validation_config.toml)
  if it should run by default; the `validate-validation-config-file`
  pre-commit hook will catch mistakes.
- Add a unit test under `demisto_sdk/commands/validate/tests/` using the
  `TestSuite` builders.
- Update the auto-generated docs by running
  `poetry run python demisto_sdk/commands/validate/generate_validate_docs.py`
  if applicable.

---

## 10. Working with the content graph

The **content graph** is a Neo4j-backed model of all content items, built by
[`content_graph_builder.py`](../demisto_sdk/commands/content_graph/content_graph_builder.py)
from parsers in
[`demisto_sdk/commands/content_graph/parsers/`](../demisto_sdk/commands/content_graph/parsers).

When suggesting code that needs to inspect content:

- Prefer **graph objects** from
  [`demisto_sdk.commands.content_graph.objects`](../demisto_sdk/commands/content_graph/objects)
  (e.g. `Playbook`, `Integration`, `Script`, `Pack`) over hand-parsing
  YAML/JSON. They provide typed access to every field.
- Use the **interface** layer
  ([`demisto_sdk/commands/content_graph/interface`](../demisto_sdk/commands/content_graph/interface))
  for queries; do not write raw Cypher in command code unless absolutely
  necessary.
- Strict (validation-time) variants live in
  [`strict_objects/`](../demisto_sdk/commands/content_graph/strict_objects).
  Use them in `validate` validators when the lenient `objects/` model is
  not strict enough.

Every content-graph object inherits from a Pydantic v1 `BaseModel`. Respect
that: do not introduce Pydantic v2 syntax there.

---

## 11. Content-related domain knowledge Copilot must respect

- **Pack structure** (per Cortex content spec): `Packs/<PackName>/` contains
  `pack_metadata.json`, plus `Integrations/`, `Scripts/`, `Playbooks/`,
  `IncidentFields/`, `IndicatorFields/`, `IncidentTypes/`,
  `IndicatorTypes/`, `Layouts/`, `Classifiers/`, `Mappers/`, `Dashboards/`,
  `Reports/`, `Widgets/`, `ReleaseNotes/`, `TestPlaybooks/`,
  `ParsingRules/`, `ModelingRules/`, `CorrelationRules/`,
  `XSIAMDashboards/`, `XSIAMReports/`, `Triggers/`, `Wizards/`, etc.
- **YAML is canonical** for integrations, scripts, playbooks; **JSON is
  canonical** for layouts, fields, mappers, classifiers, dashboards,
  reports, widgets, types.
- **Marketplaces:** Content can target `xsoar` (XSOAR 6.x), `marketplacev2`
  (XSIAM), `xpanse`, `xsoar_saas` (XSOAR 8.x SaaS), and combinations.
  Marketplace-specific behaviour is encoded via the `marketplaces` key and
  the `MarketplaceVersions` enum in
  [`demisto_sdk/commands/common/constants.py`](../demisto_sdk/commands/common/constants.py).
  Do not hard-code single-marketplace assumptions.
- **Server versions:** integrations/scripts/playbooks declare
  `fromversion` / `toversion`. Validators should respect these and not
  flag fields that are only valid on newer/older servers.

---

## 12. Things Copilot should NOT suggest

- New top-level dependencies without a clear justification — adding to
  `pyproject.toml` requires a `poetry lock` and reviewer approval.
- Network calls in unit tests.
- Reading from or writing to the user's home directory in command code
  (the SDK uses `~/.demisto-sdk/logs/` for logs only, configured centrally).
- Bare `except:` or `except Exception:` without logging and re-raising.
- Mutable default arguments (`def f(x=[])`).
- Re-exporting the banned modules from a wrapper module to "work around"
  the ruff ban.
- Files named `test_*.py` in production sub-trees (use `*_test.py`).
- Adding new global mypy ignores or top-of-file `# mypy: ignore-errors`.
- Switching to Pydantic v2 syntax.
- Switching to `click` for new commands.

---

## 13. When in doubt

Cross-reference these authoritative sources, in order:

1. [`pyproject.toml`](../pyproject.toml) — the source of truth for tool
   configuration, banned imports, supported Python versions, and dependency
   pins.
2. [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) — the exact
   hooks that gate every commit.
3. [`README.md`](../README.md) — user-facing CLI behaviour and env vars.
4. [`CONTRIBUTION.md`](../CONTRIBUTION.md) and
   [`docs/development_guide.md`](../docs/development_guide.md).
5. The closest existing implementation of the same kind of thing
   (validator, command, content-graph object, generator). Mimic its shape
   instead of inventing a new one.

If a request is ambiguous, ask a clarifying question rather than guessing.
