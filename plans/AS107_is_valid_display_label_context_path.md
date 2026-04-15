# AS107 — Validate displayLabel context keys are used in other tasks

## Ticket
**CRTX-236166**

## Summary
Validate that context keys referenced in `displayLabel` fields (`${...}` placeholders)
of autonomous playbook tasks are actually used in **other tasks** within the same
playbook.  If a context key appears only in the task's own `displayLabel` (and its
mirrored `name`/`scriptarguments.value`) but is not consumed by any other task, the
`displayLabel` is referencing a value that has no functional purpose in the playbook
flow.

## Background
In autonomous playbooks, every task that has a `displayLabel` uses it to surface a
human-readable status message in the war room.  When a `displayLabel` contains a
`${…}` placeholder, the referenced context key should be one that is actually used
elsewhere in the playbook — either as a script argument, in a condition, or as input
to another task.  If the context key is not used anywhere else, it indicates the
`displayLabel` is referencing a value that is not part of the playbook's data flow,
which is likely an error.

### Examples from the reference playbook
**File:** `demisto_sdk/commands/validate/test_files/playbook-Execution_of_significantly_renamed_lolbin.yml`

| Task | displayLabel | Context key used | Used in other tasks? | Valid? |
|------|-------------|-----------------|---------------------|--------|
| 481  | `User ${PaloAltoNetworksXQL.GenericQuery.results.actor_effective_username} detected renaming file.` | `PaloAltoNetworksXQL.GenericQuery.results.actor_effective_username` | ✅ Yes — used in task at line 7347 as `root: PaloAltoNetworksXQL.GenericQuery.results` with `accessor: actor_effective_username` | ✅ Valid |
| 205  | `Alert ${issue.id} confirmed as false positive.` | `issue.id` | ✅ Yes — used in task 1 (line 106) as `simple: ${issue.id}` in `scriptarguments` | ✅ Valid |
| 480  | `Script retrieved with SHA256 ${File.SHA256}.` | `File.SHA256` | ❌ No — only appears in task 480's own `name`, `displayLabel`, and `scriptarguments.value` | ❌ Invalid |

### How context keys are used in tasks
Context keys can appear in several places within a task:
- **`scriptarguments`**: as `simple: ${key}` or `complex.root: key`
- **`conditions`**: in condition `left.value.simple: key` with `iscontext: true`
- **`task.name`**: as `${key}` (mirrors displayLabel)
- **`task.displayLabel`**: as `${key}` (the field being validated)

For the purpose of this validation, a context key is considered "used in another task"
if it appears in **any task other than the one containing the displayLabel**, in any
of the above locations (or any other field that references context).

### Matching strategy
To determine if a context key from a `displayLabel` is used elsewhere, we need to
search the raw YAML data of all other tasks for the context key string.  This is
simpler and more robust than trying to parse every possible location where a context
key could appear.

Specifically, for each context key `K` extracted from a `displayLabel`:
1. Serialize each **other** task's raw data to a string representation
2. Check if `K` appears in that string
3. If `K` is found in at least one other task, it's valid
4. If `K` is not found in any other task, it's invalid

## Implementation Plan

### 1. Create the validator file
**File:** `demisto_sdk/commands/validate/validators/AS_validators/AS107_is_valid_display_label_context_path.py`

- Extend `BaseValidator[Playbook]`
- Set `error_code = "AS107"`
- Set `is_auto_fixable = False` (no automatic fix — requires manual replacement)
- In `obtain_invalid_content_items`:
  1. Check if the pack is autonomous (`managed: true`, `source: "autonomous"`)
  2. Collect all context key usages across all tasks (excluding `displayLabel` and
     mirrored fields of the current task)
  3. For each task with a `displayLabel`, extract all `${…}` context key references
  4. Check if each context key is used in at least one other task
  5. If any context key is not used elsewhere, add a `ValidationResult`

### 2. Register in validation config
**File:** `demisto_sdk/commands/validate/sdk_validation_config.toml`

Add `"AS107"` to:
- `[path_based_validations].select` (alongside AS101, AS102, AS103)
- `[use_git].select` (alongside AS101, AS102, AS103)
- `ignorable_errors` list (to allow packs to suppress this if needed)

### 3. Add tests
**File:** `demisto_sdk/commands/validate/tests/AS_validators_test.py`

Test cases:
1. **Non-autonomous pack** — no errors regardless of displayLabel content
2. **Autonomous pack, displayLabel context key used in another task's scriptarguments** — valid (0 errors)
3. **Autonomous pack, displayLabel context key used in another task's conditions** — valid (0 errors)
4. **Autonomous pack, displayLabel context key NOT used in any other task** — invalid (1 error)
5. **Autonomous pack, displayLabel with no context keys (static text)** — valid (0 errors)
6. **Autonomous pack, no displayLabel** — valid (0 errors)
7. **Autonomous pack, displayLabel with multiple context keys, one unused** — invalid (1 error)
8. **Autonomous pack, displayLabel with multiple context keys, all used** — valid (0 errors)

### 4. Files to create/modify
| File | Action |
|------|--------|
| `demisto_sdk/commands/validate/validators/AS_validators/AS107_is_valid_display_label_context_path.py` | **Create** |
| `demisto_sdk/commands/validate/tests/AS_validators_test.py` | **Modify** — add test cases |
| `demisto_sdk/commands/validate/sdk_validation_config.toml` | **Modify** — register AS107 |
