---
applyTo: "demisto_sdk/commands/validate/**/*.py"
---

# Copilot instructions — `validate` command and validators

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md). This file specialises
guidance for the new validation framework that lives under
[`demisto_sdk/commands/validate/`](../../demisto_sdk/commands/validate).

## Where things live

```
demisto_sdk/commands/validate/
├── validate_manager.py            # Orchestrator: collects content + runs validators
├── validate_setup.py              # Typer CLI registration
├── initializer.py                 # Bootstraps content graph for validation
├── config_reader.py               # Reads validation config TOML files
├── validation_results.py          # Result aggregation + reporting
├── default_config.toml            # Default ON/OFF/ignore config for content repos
├── sdk_validation_config.toml     # Config used when validating *this* SDK repo
├── generate_validate_docs.py      # Re-builds validator docs
├── tools.py
└── validators/
    ├── base_validator.py          # BaseValidator[ContentTypes], ValidationResult
    ├── README.md
    ├── PB_validators/             # Playbook validators (PB1xx)
    ├── IN_validators/             # Integration validators (IN1xx)
    ├── SC_validators/             # Script validators (SC1xx)
    ├── RM_validators/             # README validators (RM1xx)
    ├── IM_validators/             # Image validators (IM1xx)
    ├── GR_validators/             # Graph-relationship validators (GR1xx)
    ├── BA_validators/             # Cross-cutting "best-practice" (BA1xx)
    ├── BC_validators/             # Backwards-compatibility (BC1xx)
    └── ... see the directory tree for the full list
```

Two-letter prefixes map to content types or to cross-cutting categories
(`BA`, `BC`, `GR`). When adding a validator, **find an existing file with
the same prefix and copy its shape**.

## Validator file template

```python
# demisto_sdk/commands/validate/validators/<PREFIX>_validators/<CODE>_<snake_name>.py
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.<thing> import <Thing>
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = <Thing>


class <CamelCaseName>Validator(BaseValidator[ContentTypes]):
    error_code = "<PREFIX><NUM>"          # e.g. "PB136" — must be globally unique
    description = "Validate that <X>."    # one short sentence
    rationale = "<Why this matters to a content author / why we ship it>."
    error_message = "<Actionable message with {placeholders} for the content author>."
    related_field = "<yaml/json key>"     # surfaced in error reports
    is_auto_fixable = False               # set True only if you implement fix()

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for ci in content_items:
            if <bad condition>:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(name=ci.name),
                        content_object=ci,
                    )
                )
        return results

    # Optional: only when is_auto_fixable = True
    # def fix(self, content_item: ContentTypes) -> FixResult: ...
```

## Required choices

| Field | Rule |
|---|---|
| **filename** | `<CODE>_<snake_case>.py`. The `<CODE>` must match `error_code`. |
| **`error_code`** | Globally unique. Pick the next free number for the prefix. |
| **`description`** | One imperative sentence, present tense. |
| **`rationale`** | Why it matters; surfaced in docs and error messages. |
| **`error_message`** | Actionable. Tell the user *what to change*. Use named `{placeholders}` and call `.format(...)` in `obtain_invalid_content_items`. |
| **`related_field`** | The single most-relevant YAML/JSON key (string). Use `""` if not applicable. |
| **`is_auto_fixable`** | `True` only if `fix()` is implemented and idempotent. |
| **`expected_git_statuses`** | Override (set of `GitStatuses`) only if the validator must only run on added / modified / renamed files. Default is "always". |
| **`expected_execution_mode`** | Override only if the validator must skip nightly / use-git / all-files modes. |

## Multi-type validators

If a check applies to several content types, use a `Union`:

```python
from typing import Union
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script

ContentTypes = Union[Integration, Script]


class MyValidator(BaseValidator[ContentTypes]):
    ...
```

The `BaseValidator` will type-narrow correctly inside
`obtain_invalid_content_items`.

## Configuration

After adding a validator:

1. If it should run by default in **content** repos, add an entry under the
   appropriate section in
   [`default_config.toml`](../../demisto_sdk/commands/validate/default_config.toml).
2. If it should run when validating **this SDK repo**, also add it to
   [`sdk_validation_config.toml`](../../demisto_sdk/commands/validate/sdk_validation_config.toml).
3. The pre-commit hook
   [`validate-validation-config-file`](../../.pre-commit-config.yaml) (driven
   by [`validate_validation_config_file.py`](../../demisto_sdk/scripts/validate_validation_config_file.py))
   verifies consistency between the registry of validators and the TOML
   config. Run `poetry run pre-commit run validate-validation-config-file
   --all-files` before pushing.

## Tests

- Add a test file under
  `demisto_sdk/commands/validate/tests/<PREFIX>_validators_tests/<CODE>_<snake_name>_test.py`
  (or the existing per-prefix test layout — match neighbours).
- Cover at minimum:
  1. A passing case (no results).
  2. A failing case (one result, correct error code, correct rendered
     message).
  3. If `is_auto_fixable=True`: that `fix()` mutates the content_object so
     the validator passes on a re-run, and that the fix is idempotent.
- Build content with [`TestSuite/`](../../TestSuite) builders. Then convert
  to a graph object via the test helpers in
  `demisto_sdk/commands/validate/tests/test_tools.py` (or the closest
  neighbour test) — do **not** instantiate Pydantic graph objects directly.

## Don'ts

- Don't reach for the filesystem inside a validator. The graph object
  already carries `path`, `data`, parsed sub-objects, etc.
- Don't perform git operations inside a validator. The framework handles
  selection of changed files.
- Don't make network calls. If you genuinely need to (e.g. to validate a
  marketplace image URL), gate the call behind
  `is_sdk_defined_working_offline()` from
  [`tools`](../../demisto_sdk/commands/common/tools.py) and add a clear
  test-time mock.
- Don't write log lines per content item from inside
  `obtain_invalid_content_items`. Use the returned `ValidationResult`
  list — the framework formats and reports them.
- Don't change `error_code`s of existing validators. They are part of the
  public contract; add a new code instead and deprecate the old one.

## Regenerating docs

If you add or change a validator, regenerate the docs:

```bash
poetry run python demisto_sdk/commands/validate/generate_validate_docs.py
```

Commit the regenerated files alongside your code change.
