---
applyTo: "demisto_sdk/commands/generate_integration/**/*.py,demisto_sdk/commands/openapi_codegen/**/*.py,demisto_sdk/commands/postman_codegen/**/*.py,demisto_sdk/commands/generate_yml_from_python/**/*.py,demisto_sdk/commands/generate_unit_tests/**/*.py,demisto_sdk/commands/integration_diff/**/*.py,demisto_sdk/commands/init/**/*.py,demisto_sdk/commands/split/**/*.py"
---

# Copilot instructions — integration / script authoring tools

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md) and
[`commands.instructions.md`](commands.instructions.md). This file specialises
guidance for the cluster of commands that **generate, scaffold, split, or
diff Cortex integration and script content**:

| Command | Where |
|---|---|
| `init` (scaffold a new pack/integration/script) | [`demisto_sdk/commands/init/`](../../demisto_sdk/commands/init) |
| `split` (split a unified YAML back to a folder layout) | [`demisto_sdk/commands/split/`](../../demisto_sdk/commands/split) |
| `generate-integration` (Python → integration YAML+code) | [`demisto_sdk/commands/generate_integration/`](../../demisto_sdk/commands/generate_integration) |
| `generate-yml-from-python` | [`demisto_sdk/commands/generate_yml_from_python/`](../../demisto_sdk/commands/generate_yml_from_python) |
| `openapi-codegen` (OpenAPI spec → integration) | [`demisto_sdk/commands/openapi_codegen/`](../../demisto_sdk/commands/openapi_codegen) |
| `postman-codegen` (Postman collection → integration) | [`demisto_sdk/commands/postman_codegen/`](../../demisto_sdk/commands/postman_codegen) |
| `generate-unit-tests` | [`demisto_sdk/commands/generate_unit_tests/`](../../demisto_sdk/commands/generate_unit_tests) |
| `integration-diff` | [`demisto_sdk/commands/integration_diff/`](../../demisto_sdk/commands/integration_diff) |

Reference data models:
- [`generate_integration/XSOARIntegration.py`](../../demisto_sdk/commands/generate_integration/XSOARIntegration.py)
  — the dataclass model of an integration YAML used by the generator.
- [`generate_integration/base_code.py`](../../demisto_sdk/commands/generate_integration/base_code.py)
  — the boilerplate Python that every generated integration starts from.
- [`commands/common/schemas/`](../../demisto_sdk/commands/common/schemas)
  — Pykwalify schemas for `integration`, `script`, `playbook`, `dashboard`,
  `incidentfield`, `incidenttype`, `classifier`, `mapper`, `layout`,
  `modelingrule`, `parsingrule`, `correlationrule`, `widget`, `report`,
  `wizard`, `job`, `trigger`, `xsiamdashboard`, `xsiamreport`,
  `xdrctemplate`, `genericdefinition`, `genericfield`, `genericmodule`,
  `generictype`, `pack_metadata`, …
- Default content templates: [`commands/init/templates/`](../../demisto_sdk/commands/init/templates).

## Domain knowledge Copilot must respect

### YAML keys for `integration`

Top-level keys (subset, see schema for full list):

| Key | Meaning |
|---|---|
| `commonfields.id` | Unique integration ID. Cannot contain spaces. |
| `commonfields.version` | Schema version, almost always `-1`. |
| `name` | Display name. |
| `display` | Human-friendly name shown in the UI. |
| `category` | One of the marketplace-allowed categories (see [`pack_metadata` schema](../../demisto_sdk/commands/common/schemas/pack_metadata.json)). |
| `description` | Short description; rendered in the marketplace card. |
| `detaileddescription` | Markdown description shown on the integration page (sourced from a sibling `*_description.md` file when split). |
| `image` | Integration logo (sourced from a sibling `*_image.png` when split, must be 120×50 PNG ≤ 10 KB by content guidelines). |
| `fromversion` / `toversion` | Server version constraints (e.g. `6.10.0`). |
| `marketplaces` | List of `MarketplaceVersions` (`xsoar`, `marketplacev2`, `xpanse`, `xsoar_saas`, `platform`). |
| `defaultEnabled` / `defaultEnabled_x2` | Auto-enable on install (per marketplace). |
| `configuration` | List of integration **params** (see below). |
| `script.script` | Python source (`-` placeholder when split into `.py`). |
| `script.type` | `python` or `powershell` (almost always `python`). |
| `script.subtype` | `python2` or `python3` (always `python3` for new content). |
| `script.dockerimage` | `demisto/python3:<tag>` or `demisto/<image>:<tag>`. |
| `script.commands` | List of integration commands (see below). |
| `script.feed` / `script.isfetch` / `script.isfetchsamples` / `script.ismappable` / `script.isremotesyncin` / `script.isremotesyncout` / `script.longRunning` / `script.longRunningPort` | Capability flags. |
| `script.runonce` | Execute once on install. |
| `tests` | List of test playbook IDs, or `["No tests"]` with a justification. |
| `supportedModules` | Optional list of supported modules. |

### Integration `configuration` (params)

Each entry is a parameter shown to the customer when configuring an
instance:

```yaml
- display: Server URL
  name: url
  type: 0                # ParameterType — see commands/common/constants.py::ParameterType
  required: true
  defaultvalue: https://example.com
  additionalinfo: Optional help text shown next to the field.
  hidden: false          # bool, or list of marketplaces where it should be hidden
```

Common `type` values (defined in
[`ParameterType`](../../demisto_sdk/commands/common/constants.py)):

| Value | Meaning |
|---|---|
| `0` | Short text (single-line string). |
| `4` | Encrypted (password / API key). |
| `8` | Checkbox (boolean). |
| `9` | Authentication (username + password). |
| `12` | Long text (multi-line). |
| `13` | Single select (from `options`). |
| `15` | Multi select (from `options`). |
| `16` | Multi-instance only (single-select). |
| `17` | Credentials (uses XSOAR credential store). |
| `19` | Credentials (single field, e.g. API key from creds vault). |

Use the named enum members where possible rather than the magic numbers.

### Fetch-incidents integrations

A fetch integration **must** include the params from
[`INCIDENT_FETCH_REQUIRED_PARAMS`](../../demisto_sdk/commands/common/constants.py)
(or [`ALERT_FETCH_REQUIRED_PARAMS`](../../demisto_sdk/commands/common/constants.py)
for XSIAM alerts). Generators must inject these when `script.isfetch: true`
or `script.isfetchsamples: true`. See
[`FIRST_FETCH_PARAM`](../../demisto_sdk/commands/common/constants.py),
[`MAX_FETCH_PARAM`](../../demisto_sdk/commands/common/constants.py).

### Feed integrations

Feed integrations (`script.feed: true`) must include
[`FEED_REQUIRED_PARAMS`](../../demisto_sdk/commands/common/constants.py)
(reset feed, fetch indicators interval, TLP color, etc.).

### Integration `commands`

```yaml
- name: example-search                  # kebab-case, lowercased; vendor-prefixed (e.g. `okta-`)
  description: Searches Example for ...
  arguments:
    - name: query
      description: The search query.
      required: true
      isArray: false
      default: false
      auto: PREDEFINED                  # for dropdown-style args
      predefined: ["one", "two"]
      defaultValue: "one"
  outputs:
    - contextPath: Example.Search.Result
      description: Result of the search.
      type: String                      # String|Number|Boolean|Date|Unknown
  deprecated: false
  polling: false                        # generic polling integration support
```

Reputation commands (`ip`, `url`, `domain`, `file`, `email`, `cve`,
`endpoint`) are **bang commands** and have a strict required-args contract
([`BANG_COMMAND_NAMES`](../../demisto_sdk/commands/common/constants.py),
[`BANG_COMMAND_ARGS_MAPPING_DICT`](../../demisto_sdk/commands/common/constants.py))
plus mandatory DBot-Score outputs
([`DBOT_SCORES_DICT`](../../demisto_sdk/commands/common/constants.py)) and
context standard outputs
([`MANDATORY_REPUTATION_CONTEXT_NAMES`](../../demisto_sdk/commands/common/constants.py)).
See the [XSOAR context standards](https://xsoar.pan.dev/docs/integrations/context-standards-mandatory)
referenced by [`XSOAR_CONTEXT_STANDARD_URL`](../../demisto_sdk/commands/common/constants.py).
Generators must emit these when generating reputation commands.

### Script (vs integration)

A `script` YAML has the same `commonfields`, `name`, `script`, `tests`,
`fromversion`/`toversion`, `marketplaces` keys, plus:

| Key | Meaning |
|---|---|
| `args` | Same shape as integration command arguments. |
| `outputs` | Same shape as integration command outputs. |
| `tags` | Free-form tags. |
| `comment` | Description shown in the script picker. |
| `subtype` | `python2` / `python3` — always `python3` for new content. |

Standalone scripts that are reused by multiple playbooks belong under
`Packs/<Pack>/Scripts/<ScriptName>/`.

### `pack_metadata.json`

Every pack has one (see [`pack_metadata` schema](../../demisto_sdk/commands/common/schemas/pack_metadata.json)).
Required keys for new packs:

- `name`, `description`, `support` (`xsoar` / `partner` / `community` /
  `developer`), `author`, `currentVersion`, `created`, `categories`,
  `tags`, `useCases`, `keywords`, `marketplaces`.
- `dependencies` is computed by the SDK; do not hand-author it unless you
  know exactly why.
- `support: xsoar` requires a `xsoar`-team-owned repo path.
- `support: partner` requires a valid `email` / `url`.

## Generator conventions

When implementing or modifying a generator:

1. **Build YAML via the dataclass model** in
   [`XSOARIntegration.py`](../../demisto_sdk/commands/generate_integration/XSOARIntegration.py)
   when generating a full integration. Don't hand-build dicts — the
   dataclasses encode the schema and serialise to a deterministic YAML.
2. **Use the project YAML/JSON handlers** from
   [`commands/common/handlers/`](../../demisto_sdk/commands/common/handlers).
   Never `import yaml` / `import json` directly.
3. **Boilerplate code** comes from
   [`generate_integration/base_code.py`](../../demisto_sdk/commands/generate_integration/base_code.py).
   Do not duplicate it; extend it.
4. **Generated Python must pass [`xsoar_linter`](../../demisto_sdk/commands/xsoar_linter)**
   at the appropriate support level (`base` minimum). Test the
   round-trip in unit tests.
5. **Generated Python must pass `ruff` and `mypy`** *for the SDK's own
   lint*, but the *content's* lint is run by `demisto-sdk pre-commit` or
   `demisto-sdk lint`. Do not bake SDK-specific tool config into
   generated content.
6. **Idempotency.** Re-running the generator on the same input must
   produce a byte-identical result.
7. **Marketplaces.** Default `marketplaces` for new content from
   `init`/generators is `[xsoar, marketplacev2]` unless the user opts
   into a narrower set.
8. **Vendor prefix.** Command names must be vendor-prefixed
   (`<vendor>-<verb>-<noun>`) unless they are reputation/bang commands
   (`ip`, `url`, `file`, …) or shared XSOAR commands (`endpoint`,
   `extractIndicators`).
9. **Default outputs.** Use
   [`load_default_additional_info_dict()`](../../demisto_sdk/commands/common/default_additional_info_loader.py)
   and
   [`commands/common/default_output_descriptions.json`](../../demisto_sdk/commands/common/default_output_descriptions.json)
   to populate descriptions for known parameters/outputs (e.g. `url`,
   `proxy`, `insecure`, DBot scores). Do not hard-code the strings.
10. **`fromversion`** for newly generated integrations defaults to
    [`DEFAULT_CONTENT_ITEM_FROM_VERSION`](../../demisto_sdk/commands/common/constants.py).
    Do not invent a different default.

## Tests

- Use [`TestSuite/`](../../TestSuite) builders to construct input
  artefacts (Python source for `generate-yml-from-python`, OpenAPI/Postman
  fixtures for the codegens, integration directories for `split`/`init`).
- Snapshot the **structure** (dict comparison after parsing) rather than
  the exact YAML bytes — handlers may re-order keys with different
  versions of `ruamel.yaml`.
- For codegens, store the source spec under `tests/test_files/` and the
  expected output next to it; compare via parsed dict + a separate
  `xsoar_linter` round-trip on the generated Python.
- Mock all network calls (OpenAPI specs may be referenced by URL but the
  test must not fetch them).

## Hard rules

- **Don't generate Python 2.** `script.subtype` is always `python3`.
- **Don't generate code that reuses integration param names already
  meaning something else.** `proxy`, `insecure`, `url`, `apikey`,
  `credentials`, `first_fetch`, `max_fetch`, `feedReputation`, `feedBypassExclusionList`,
  etc., have fixed semantics — use them only for that.
- **Don't generate commands without a description and without outputs**
  (or explicitly `outputs: []` if there really are none). The legacy and
  new validators both reject this.
- **Don't generate `tests: []`.** Use `tests: ["No tests"]` and add a
  `tests` block only if the integration genuinely has test playbooks. If
  you set `["No tests"]`, the validator will require an entry in
  `Tests/conf.json`'s `skipped_integrations` with a justification — emit
  a TODO comment for the author.
- **Don't introduce a new `category`** value. Pull from the canonical
  list in the [`pack_metadata` schema](../../demisto_sdk/commands/common/schemas/pack_metadata.json).
- **Don't read the user's home directory** for templates or settings;
  use the in-repo template directories.
