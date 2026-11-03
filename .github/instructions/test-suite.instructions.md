---
applyTo: "TestSuite/**/*.py"
---

# Copilot instructions — `TestSuite/`

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md) and
[`tests.instructions.md`](tests.instructions.md).

[`TestSuite/`](../../TestSuite) is a **fixture-builder library** used by
unit tests across the repo. It lets a test materialise a realistic content
repo on disk in a `tmp_path`, then point SDK code at that path.

It is **excluded from the wheel** (see `exclude` in
[`pyproject.toml`](../../pyproject.toml)) and is **not** part of the public
API. Production code under `demisto_sdk/` must not import from `TestSuite/`.

## Layout

- [`repo.py`](../../TestSuite/repo.py) — `Repo` builder (top-level).
- [`pack.py`](../../TestSuite/pack.py) — `Pack` builder (creates a Cortex
  content pack with all sub-folders).
- [`integration.py`](../../TestSuite/integration.py),
  [`playbook.py`](../../TestSuite/playbook.py),
  [`classifier.py`](../../TestSuite/classifier.py),
  [`mapper.py`](../../TestSuite/mapper.py),
  [`layout.py`](../../TestSuite/layout.py),
  [`incident_field.py`](../../TestSuite/incident_field.py),
  [`indicator_field.py`](../../TestSuite/indicator_field.py),
  [`modeling_rule.py`](../../TestSuite/modeling_rule.py),
  [`parsing_rule.py`](../../TestSuite/parsing_rule.py),
  [`correlation_rule.py`](../../TestSuite/correlation_rule.py),
  [`dashboard.py`](../../TestSuite/dashboard.py),
  [`generic_definition.py`](../../TestSuite/generic_definition.py),
  [`generic_field.py`](../../TestSuite/generic_field.py),
  [`generic_module.py`](../../TestSuite/generic_module.py),
  [`generic_type.py`](../../TestSuite/generic_type.py),
  [`job.py`](../../TestSuite/job.py),
  [`agentix_agent.py`](../../TestSuite/agentix_agent.py),
  [`agentix_action.py`](../../TestSuite/agentix_action.py),
  [`case_field.py`](../../TestSuite/case_field.py),
  [`case_layout.py`](../../TestSuite/case_layout.py),
  [`case_layout_rule.py`](../../TestSuite/case_layout_rule.py),
  [`layout_rule.py`](../../TestSuite/layout_rule.py) — per-content-type
  builders.
- [`json_based.py`](../../TestSuite/json_based.py),
  [`file.py`](../../TestSuite/file.py) — generic file primitives all
  builders use.
- [`assets/`](../../TestSuite/assets) — canonical sample content used as
  defaults (e.g. `default_integration/sample.yml`,
  `default_playbook/playbook-sample.yml`).

## Conventions

- **Builders mirror the on-disk content layout** of a Cortex pack. The
  `create_<thing>(name)` method returns a builder for that thing and
  drops a default file on disk under the right sub-folder.
- **Defaults come from `TestSuite/assets/`.** When you need a new default
  for a new content type, add a sample file under `assets/default_<type>/`
  and load it from the builder via the `file` / `json_based` helpers.
- **Builders are mutable.** Tests typically grab the builder, mutate
  `builder.yml` / `builder.json`, then write it back via
  `builder.write_yml(...)` / `builder.write_json(...)` (or via the
  `update(...)` convenience).
- **`Repo` is the entry point.** Tests should construct a `Repo(tmp_path)`
  and create everything from it, so file paths and `CONTENT_PATH`-like
  semantics are consistent.

## Adding a new builder

1. Add `TestSuite/<thing>.py` modelled on the closest existing builder
   (e.g. [`integration.py`](../../TestSuite/integration.py) for code-bearing
   types, [`incident_field.py`](../../TestSuite/incident_field.py) for
   pure-JSON types).
2. Drop a sample file under
   [`TestSuite/assets/default_<thing>/`](../../TestSuite/assets).
3. Expose `create_<thing>(name)` on [`Pack`](../../TestSuite/pack.py).
4. Add a small builder test under `TestSuite/<thing>_test.py` (e.g.
   [`agentix_action_test.py`](../../TestSuite/agentix_action_test.py)) that
   verifies files are written in the right place.

## Hard rules

- **No production-side imports.** `TestSuite/` may freely import from
  `demisto_sdk/` (for handlers, constants, schemas), but nothing under
  `demisto_sdk/` may import from `TestSuite/`.
- **No network, no Docker, no Neo4j calls.** Builders only touch the
  filesystem.
- **Use the project handlers** (`JSON_Handler`, `YAML_Handler`) for
  serialising files — same ban list as the rest of the repo.
- **Be tmp-friendly.** Builders take a `tmp_path` (or a parent builder
  that does) and never write outside that root.
- **Keep the public method surface stable.** Many tests across the repo
  call `pack.create_integration(...)`, `integration.create_default_integration()`,
  etc. — adding kwargs is fine, renaming is not.
