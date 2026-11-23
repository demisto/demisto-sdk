---
applyTo: "demisto_sdk/commands/common/hook_validations/**/*.py,demisto_sdk/commands/validate/old_validate_manager.py,demisto_sdk/commands/validate/tests/old_validators_test.py"
---

# Copilot instructions — legacy validators (`hook_validations/`)

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md). This file applies to
the **legacy** validation framework that lives under
[`demisto_sdk/commands/common/hook_validations/`](../../demisto_sdk/commands/common/hook_validations)
and is orchestrated by
[`demisto_sdk/commands/validate/old_validate_manager.py`](../../demisto_sdk/commands/validate/old_validate_manager.py).

> **Status:** This framework is in **maintenance mode**. The replacement is
> the new framework documented in
> [`validators.instructions.md`](validators.instructions.md). All **new**
> checks must go in the new framework; this file describes how to *modify*
> the legacy one safely (bug fixes, content-author-blocking regressions,
> security fixes).

## Scope

| Layer | Where |
|---|---|
| Per-content-type validators | [`hook_validations/integration.py`](../../demisto_sdk/commands/common/hook_validations/integration.py), [`script.py`](../../demisto_sdk/commands/common/hook_validations/script.py), [`playbook.py`](../../demisto_sdk/commands/common/hook_validations/playbook.py), [`incident_field.py`](../../demisto_sdk/commands/common/hook_validations/incident_field.py), [`incident_type.py`](../../demisto_sdk/commands/common/hook_validations/incident_type.py), [`indicator_field.py`](../../demisto_sdk/commands/common/hook_validations/indicator_field.py), [`classifier.py`](../../demisto_sdk/commands/common/hook_validations/classifier.py), [`mapper.py`](../../demisto_sdk/commands/common/hook_validations/mapper.py), [`layout.py`](../../demisto_sdk/commands/common/hook_validations/layout.py), [`dashboard.py`](../../demisto_sdk/commands/common/hook_validations/dashboard.py), [`report.py`](../../demisto_sdk/commands/common/hook_validations/report.py), [`widget.py`](../../demisto_sdk/commands/common/hook_validations/widget.py), [`modeling_rule.py`](../../demisto_sdk/commands/common/hook_validations/modeling_rule.py), [`parsing_rule.py`](../../demisto_sdk/commands/common/hook_validations/parsing_rule.py), [`correlation_rule.py`](../../demisto_sdk/commands/common/hook_validations/correlation_rule.py), [`xsiam_dashboard.py`](../../demisto_sdk/commands/common/hook_validations/xsiam_dashboard.py), [`xsiam_report.py`](../../demisto_sdk/commands/common/hook_validations/xsiam_report.py), [`generic_*.py`](../../demisto_sdk/commands/common/hook_validations), [`job.py`](../../demisto_sdk/commands/common/hook_validations/job.py), [`triggers.py`](../../demisto_sdk/commands/common/hook_validations/triggers.py), [`wizard.py`](../../demisto_sdk/commands/common/hook_validations/wizard.py), [`xdrc_templates.py`](../../demisto_sdk/commands/common/hook_validations/xdrc_templates.py), [`lists.py`](../../demisto_sdk/commands/common/hook_validations/lists.py) |
| Cross-cutting validators | [`base_validator.py`](../../demisto_sdk/commands/common/hook_validations/base_validator.py), [`content_entity_validator.py`](../../demisto_sdk/commands/common/hook_validations/content_entity_validator.py), [`structure.py`](../../demisto_sdk/commands/common/hook_validations/structure.py), [`description.py`](../../demisto_sdk/commands/common/hook_validations/description.py), [`docker.py`](../../demisto_sdk/commands/common/hook_validations/docker.py), [`image.py`](../../demisto_sdk/commands/common/hook_validations/image.py), [`author_image.py`](../../demisto_sdk/commands/common/hook_validations/author_image.py), [`readme.py`](../../demisto_sdk/commands/common/hook_validations/readme.py), [`graph_validator.py`](../../demisto_sdk/commands/common/hook_validations/graph_validator.py), [`id.py`](../../demisto_sdk/commands/common/hook_validations/id.py), [`pack_unique_files.py`](../../demisto_sdk/commands/common/hook_validations/pack_unique_files.py), [`deprecation.py`](../../demisto_sdk/commands/common/hook_validations/deprecation.py), [`field_base_validator.py`](../../demisto_sdk/commands/common/hook_validations/field_base_validator.py), [`python_file.py`](../../demisto_sdk/commands/common/hook_validations/python_file.py), [`xsoar_config_json.py`](../../demisto_sdk/commands/common/hook_validations/xsoar_config_json.py), [`old_release_notes.py`](../../demisto_sdk/commands/common/hook_validations/old_release_notes.py), [`release_notes.py`](../../demisto_sdk/commands/common/hook_validations/release_notes.py), [`release_notes_config.py`](../../demisto_sdk/commands/common/hook_validations/release_notes_config.py), [`reputation.py`](../../demisto_sdk/commands/common/hook_validations/reputation.py), [`pre_process_rule.py`](../../demisto_sdk/commands/common/hook_validations/pre_process_rule.py), [`test_playbook.py`](../../demisto_sdk/commands/common/hook_validations/test_playbook.py) |
| Orchestrator | [`validate/old_validate_manager.py`](../../demisto_sdk/commands/validate/old_validate_manager.py) |
| Error catalogue | [`commands/common/errors.py`](../../demisto_sdk/commands/common/errors.py) — class `Errors` with `error_codes` decorator |
| README | [`validate/old_validate_readme.md`](../../demisto_sdk/commands/validate/old_validate_readme.md) |
| Tests | [`validate/tests/old_validators_test.py`](../../demisto_sdk/commands/validate/tests/old_validators_test.py) and per-validator tests under [`commands/common/hook_validations/tests/`](../../demisto_sdk/commands/common/hook_validations) |

## Architectural shape (very different from the new framework)

The legacy framework is **method-based**, not class-per-check:

- One class per content type (`IntegrationValidator`, `ScriptValidator`,
  `PlaybookValidator`, …) inheriting from
  [`ContentEntityValidator`](../../demisto_sdk/commands/common/hook_validations/content_entity_validator.py)
  → [`BaseValidator`](../../demisto_sdk/commands/common/hook_validations/base_validator.py).
- Each **check** is a method on that class, decorated with
  `@error_codes("XX123,XX124")` from
  [`hook_validations/base_validator.py`](../../demisto_sdk/commands/common/hook_validations/base_validator.py).
- Each method **returns `bool`** (`True` = valid, `False` = invalid) and,
  on failure, calls `self.handle_error(...)` with a message + path + error
  code drawn from `Errors` in
  [`commands/common/errors.py`](../../demisto_sdk/commands/common/errors.py).
- A `is_valid_<thing>()` aggregator method on each class composes the
  individual checks and returns the overall `bool`.

Example check shape (do **not** copy this for new code — use the new
framework instead):

```python
@error_codes("IN123")
def is_valid_some_thing(self) -> bool:
    if <bad>:
        error_message, error_code = Errors.some_descriptor(...)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
    return True
```

## Hard rules

1. **Do not add new checks here.** Add them in the new framework under
   [`commands/validate/validators/`](../../demisto_sdk/commands/validate/validators).
   The only acceptable additions to `hook_validations/` are:
   - Bug fixes to existing checks (false positive / false negative).
   - Security or correctness fixes that cannot wait for a port to the new
     framework.
   - Mechanical changes (typing, logging, lint).
2. **Do not add new error codes to
   [`Errors`](../../demisto_sdk/commands/common/errors.py)** for new checks.
   Reuse existing codes for bug fixes; new codes belong to new-framework
   validators.
3. **Do not change the signature of existing public check methods.** They
   are called by `old_validate_manager` and may be subclassed downstream.
4. **Do not change the message text of `Errors.<descriptor>`** unless the
   text is actively wrong/misleading. Content authors grep for these
   strings; ID-only error suppression (`pack-ignore`) does not.
5. **Do not delete existing checks** as part of "cleanup". A dedicated
   removal PR with a `breaking` changelog entry and a deprecation cycle is
   required.
6. **Respect the project-wide bans** from
   [`copilot-instructions.md`](../copilot-instructions.md): no `print`, no
   `import json/yaml/logging/loguru/git.Repo` directly, paths via
   `pathlib`, etc. Even when the surrounding legacy code violates these,
   bring your *changed lines* into compliance.

## Bug-fix workflow

1. **Reproduce** with a failing test under
   [`hook_validations/tests/`](../../demisto_sdk/commands/common/hook_validations)
   or [`old_validators_test.py`](../../demisto_sdk/commands/validate/tests/old_validators_test.py).
   Use [`TestSuite/`](../../TestSuite) builders for content fixtures.
2. **Fix narrowly.** Touch only the broken check method; do not refactor
   neighbours unless the fix requires it.
3. **Add an `internal` (or `fix`) changelog entry** depending on user
   visibility:
   ```bash
   poetry run sdk-changelog --init -n <PR-number>
   ```
4. **Note the new-framework counterpart.** If the same check exists in
   the new framework (e.g. `IN<NNN>` ↔ `is_valid_<thing>`), fix it there
   too in the same PR. If only the legacy framework has it, link the PR
   in [`plans/`](../../plans) so the port is tracked.

## When you must add a check (truly cannot wait)

If the check **must** ship in legacy because content repos still run the
old framework on a particular code path:

1. Add the method to the right per-type validator class.
2. Wire it into the class's `is_valid_<thing>()` aggregator.
3. Add a new error code in [`Errors`](../../demisto_sdk/commands/common/errors.py),
   following the existing prefix convention.
4. Decorate with `@error_codes("XX###")`.
5. Cover with at least one positive and one negative unit test under
   [`hook_validations/tests/`](../../demisto_sdk/commands/common/hook_validations).
6. **Open a follow-up issue / plan entry** to port it to the new framework.

## Don'ts

- Don't move logic from `hook_validations/` into `commands/common/`
  generic helpers as part of a "cleanup" — it will silently change
  behaviour for `old_validate_manager` consumers.
- Don't change the order of checks inside an `is_valid_<thing>()`
  aggregator. The first failure short-circuits, so re-ordering changes
  which error a user sees first.
- Don't introduce new dependencies on the content graph from inside
  `hook_validations/`; the legacy framework deliberately runs without it
  (the [`graph_validator.py`](../../demisto_sdk/commands/common/hook_validations/graph_validator.py)
  module is the single, intentional exception).
- Don't import from
  [`commands/validate/validators/`](../../demisto_sdk/commands/validate/validators)
  here. The dependency arrow points the other way (legacy → common,
  new framework → common).
