---
applyTo: "**/*.md,.changelog/**/*.yml,docs/**/*"
---

# Copilot instructions — docs, READMEs, and changelog

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md).

This file applies to all Markdown / docs files and to changelog
fragments under [`.changelog/`](../../.changelog).

## Markdown style

- One H1 (`#`) per file at the top.
- Sentence case for headings.
- Fenced code blocks with a language identifier (` ```bash`, ` ```python`,
  ` ```yaml`, ` ```toml`, ` ```ini`).
- Use **relative links** to other files in this repo
  (`[link](../README.md)`), not absolute `https://github.com/...` links.
  Absolute links are appropriate only for external resources.
- Tables are GitHub-flavoured. Don't try to align columns by padding —
  Markdown renderers don't care.
- Wrap prose at ~100 chars where comfortable, but never break in the
  middle of a `[link](url)`.

## Per-command READMEs

`demisto_sdk/commands/<command>/README.md` is **(re)generated** by the
[`generate-command-docs`](../../demisto_sdk/scripts/generate_commands_docs.py)
pre-commit hook whenever a `*_setup.py` changes. **Do not hand-edit the
generated sections.** If you need to add hand-written prose, put it
above the generated section and the regenerator will preserve it.

To regenerate explicitly:

```bash
poetry run pre-commit run generate-command-docs --all-files
```

Commit the regenerated file alongside the code change.

## Changelog fragments

Changelog entries live under [`.changelog/`](../../.changelog) as YAML
fragments and are assembled into [`CHANGELOG.md`](../../CHANGELOG.md) at
release time by
[`demisto_sdk/scripts/changelog/changelog.py`](../../demisto_sdk/scripts/changelog/changelog.py).

### Required for every user-visible change

```bash
poetry run sdk-changelog --init -n <PR-number>
```

This creates `.changelog/<PR-number>.yml` with the right structure:

```yaml
changes:
  - description: <One sentence, present tense, user-facing.>
    type: <feature|fix|breaking|internal>
pr_number: <PR-number>
```

### Type guidance

| Type | Use for |
|---|---|
| `breaking` | Anything that requires a content author to change their workflow, scripts, configs, or pinned SDK version. Must also be called out in the PR description. |
| `feature` | New CLI command, new flag, new validator, new public API. |
| `fix` | Bug fixes, regressions, edge-case handling. |
| `internal` | Refactors, test-only changes, dependency bumps with no user impact, CI changes. |

### Wording

- Imperative present tense ("Add", "Fix", "Improve" — not "Added",
  "Adds", "Adding").
- Reference the affected command in backticks (`` `validate` ``,
  `` `pre-commit` ``).
- Reference validator codes in backticks (`` `PB100` ``).
- One sentence per `description`. If you need to say more, open multiple
  entries.

### Hard rules

- **One fragment per PR**, named `<PR-number>.yml`. Don't reuse an
  existing PR number.
- **Don't edit `CHANGELOG.md` directly.** It is regenerated.
- **Don't omit a fragment** for user-visible changes; CI checks for it.
  Internal-only changes still need an `internal` fragment.

## Repo-level docs

- [`README.md`](../../README.md) — installation, env vars, command list,
  Docker / offline / custom registry guidance. Update it when you add a
  command, change env-var semantics, or change supported Python versions.
- [`CONTRIBUTION.md`](../../CONTRIBUTION.md) — links out to the canonical
  contributor docs at xsoar.pan.dev. Don't duplicate content here.
- [`docs/development_guide.md`](../../docs/development_guide.md) — local
  dev workflow.
- [`docs/demisto-sdk-docker.md`](../../docs/demisto-sdk-docker.md) —
  Docker image usage.
- [`docs/create_command.md`](../../docs/create_command.md) — command
  scaffolding walkthrough.

When you add a new command, link it from the **Commands** section of
[`README.md`](../../README.md).

## Don'ts

- Don't include screenshots without compressing them.
- Don't paste long log output into a README — link to a Gist or trim.
- Don't use HTML where Markdown will do.
- Don't add badges for services we don't actually integrate with.
