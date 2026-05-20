---
mode: ask
description: Generate or review a `.changelog/` fragment for a PR.
---

# Add or review a changelog fragment

Changelog policy lives in
[`.github/instructions/docs-and-changelog.instructions.md`](../instructions/docs-and-changelog.instructions.md).
Fragments are assembled into [`CHANGELOG.md`](../../CHANGELOG.md) by
[`sdk-changelog`](../../demisto_sdk/scripts/changelog/changelog.py) at
release time.

## Inputs to gather

1. The **PR number** (used as the fragment filename).
2. The **type** of each change:
   - `breaking` — content authors must adapt.
   - `feature` — new command, flag, validator, public API.
   - `fix` — bug or regression fix.
   - `internal` — refactor, tests, deps, CI with no user impact.
3. A **one-sentence description per change**, imperative present tense,
   referencing affected commands / validator codes in backticks.

## Steps to perform

1. Run:
   ```bash
   poetry run sdk-changelog --init -n <PR-number>
   ```
   This creates `.changelog/<PR-number>.yml`.
2. Edit the fragment so each `description` is:
   - Imperative present tense ("Add", "Fix", "Improve").
   - One sentence.
   - Mentions the affected command (`` `validate` ``) or validator
     (`` `PB100` ``) in backticks.
3. If multiple distinct user-visible things changed in one PR, add
   multiple `changes:` entries.
4. Verify the file parses cleanly:
   ```bash
   poetry run sdk-changelog --validate
   ```
5. Commit `.changelog/<PR-number>.yml` together with the code change.

## Don'ts

- Do **not** edit [`CHANGELOG.md`](../../CHANGELOG.md) directly.
- Do **not** reuse a PR-number filename that already exists.
- Do **not** omit a fragment for user-visible changes; CI will fail.
  Internal-only changes still need an `internal` entry.
