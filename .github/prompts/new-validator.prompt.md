---
mode: agent
description: Scaffold a new demisto-sdk validator end to end.
---

# Add a new `validate` validator

Use the conventions documented in
[`.github/instructions/validators.instructions.md`](../instructions/validators.instructions.md)
and the canonical reference
[`PB100_is_no_rolename.py`](../../demisto_sdk/commands/validate/validators/PB_validators/PB100_is_no_rolename.py).

## Inputs to gather (ask the user before generating code)

1. **Content type** — Playbook (`PB`), Integration (`IN`), Script (`SC`),
   README (`RM`), Image (`IM`), Graph relation (`GR`), Best-practice
   (`BA`), Backwards-compat (`BC`), …
2. **Error code** — next free `<PREFIX>NNN` for that prefix. List
   existing files under
   [`demisto_sdk/commands/validate/validators/<PREFIX>_validators/`](../../demisto_sdk/commands/validate/validators)
   to find the next free number.
3. **One-sentence description** of what the validator checks.
4. **Rationale** — why this matters to a content author.
5. **Error message** with `{placeholders}` that name the offending field,
   item, etc.
6. **Related field(s)** — the YAML/JSON key(s) most relevant to the
   check.
7. **Auto-fix?** If yes, gather the fix logic and confirm idempotency.

## Steps to perform

1. Create
   `demisto_sdk/commands/validate/validators/<PREFIX>_validators/<CODE>_<snake_name>.py`
   matching the template in the validators instructions file.
2. Add a unit test under
   `demisto_sdk/commands/validate/tests/<PREFIX>_validators_tests/<CODE>_<snake_name>_test.py`
   covering at least:
   - A passing case.
   - A failing case.
   - The `fix()` round-trip if `is_auto_fixable=True`.
   Use [`TestSuite/`](../../TestSuite) builders to construct fixtures.
3. Register the validator in
   [`default_config.toml`](../../demisto_sdk/commands/validate/default_config.toml)
   (and
   [`sdk_validation_config.toml`](../../demisto_sdk/commands/validate/sdk_validation_config.toml)
   if it should run when validating this SDK repo).
4. Run:
   ```bash
   poetry run pre-commit run validate-validation-config-file --all-files
   poetry run pytest demisto_sdk/commands/validate/tests -k <CODE> -x
   poetry run python demisto_sdk/commands/validate/generate_validate_docs.py
   ```
5. Add a `feature` (or `fix`) changelog entry:
   ```bash
   poetry run sdk-changelog --init -n <PR-number>
   ```

## Hard guardrails

- The validator **must not** make network calls, write to disk, or run
  git/docker commands.
- The error code **must** be globally unique and match the filename
  prefix.
- The validator **must** type-narrow on `ContentTypes`; for multi-type
  validators use a `Union[...]`.
- Pydantic v1 only. Use the project logger and JSON/YAML handlers if you
  need them (see [`copilot-instructions.md`](../copilot-instructions.md)).
