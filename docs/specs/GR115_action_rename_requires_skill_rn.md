# Spec: GR115 — Action Rename Requires Dependent Skill Release Note

## Objective

When an **Agentix Action**'s name (its content identifier) is changed, every
**Agentix Skill** that depends on that action must bump its version by adding a
Release Note (RN). Skills reference actions by id via `<action=action-id>`
tokens in their Markdown body; renaming the action silently breaks that
reference unless the skill is also updated and released. This validator fails
the build when a renamed action has a dependent skill whose pack did **not** get
a new Release Note.

**User:** content / Agentix developers renaming actions.

**Success looks like:** `demisto-sdk validate` reports `GR115` for every
dependent skill that is missing an RN bump after its action was renamed, and
passes when each dependent skill's pack has an RN added (or when no action name
changed).

## Tech Stack

- Python 3.9+ (`demisto-sdk`)
- Pydantic content-graph objects
- Neo4j content graph (for reverse `used_by` dependency resolution)
- `pytest` for unit tests

## Commands

```bash
# Run the GR115 unit tests
cd ../demisto-sdk && poetry run pytest demisto_sdk/commands/validate/tests/GR_validators_test.py -k GR115 -q

# Run the validator against content
cd ../demisto-sdk && poetry run demisto-sdk validate -i <path-to-action>
```

## Project Structure

```
demisto-sdk/demisto_sdk/commands/validate/validators/GR_validators/
  GR115_action_name_changed_requires_skill_rn.py            → base (graph) logic
  GR115_action_name_changed_requires_skill_rn_all_files.py  → ALL_FILES wrapper
  GR115_action_name_changed_requires_skill_rn_list_files.py → USE_GIT / SPECIFIC_FILES wrapper
demisto-sdk/demisto_sdk/commands/validate/sdk_validation_config.toml → register GR115
demisto-sdk/demisto_sdk/commands/validate/tests/GR_validators_test.py → unit tests
```

## Code Style

Follows the existing GR-validator triplet pattern (see GR112). Base class holds
`obtain_invalid_content_items_using_graph`; the two thin wrappers set
`expected_execution_mode` and delegate.

```python
ContentTypes = AgentixAction


class IsActionNameChangedRequiresSkillRNValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR115"
    error_message = (
        "The Agentix Action name was changed from '{old}' to '{new}', but the "
        "dependent skill '{skill}' (pack '{pack}') has no Release Note. "
        "Add a Release Note that bumps the skill's pack version."
    )
    related_field = "name"
    is_auto_fixable = False
```

## Testing Strategy

- Framework: `pytest`, located in
  `demisto_sdk/commands/validate/tests/GR_validators_test.py`.
- Use the `graph_repo` fixture + `create_agentix_action` / `create_agentix_skill`
  helpers, build a graph with `graph_repo.create_graph()`.
- Cases:
  1. Action renamed, dependent skill pack has **no** RN → 1 result.
  2. Action renamed, dependent skill pack **has** RN added → 0 results.
  3. Action **not** renamed (other field changed) → 0 results.
  4. Action added (no old object) → 0 results.
  5. Action renamed but has no dependent skills → 0 results.

## Boundaries

- **Always:** follow the GR triplet pattern; register the code in the config TOML;
  add unit tests; keep functions small with guard clauses.
- **Ask first:** changing the content-graph schema or adding new graph queries.
- **Never:** mutate content items; hardcode pack names; remove existing validators.

## Success Criteria

- `GR115` triplet exists and is importable.
- Registered in `sdk_validation_config.toml`.
- New unit tests pass (the 5 cases above).
- No regressions in existing GR tests.

## Open Questions (resolved by best-practice defaults — flag if wrong)

- **Action "name" field:** uses the content identifier (`object_id`), the id used
  in `<action=id>` references that creates the skill→action dependency.
- **Error-code prefix:** `GR` (graph/relationship), since reverse dependencies
  require the content graph.
- **"Skill bumped a version":** the dependent skill's pack has a Release Note
  added (`was_rn_added(pack)`).
