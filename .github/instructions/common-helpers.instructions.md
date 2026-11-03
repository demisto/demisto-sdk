---
applyTo: "demisto_sdk/commands/common/**/*.py"
---

# Copilot instructions — shared helpers (`commands/common/`)

Read together with the repo-wide
[`copilot-instructions.md`](../copilot-instructions.md). This file applies to
[`demisto_sdk/commands/common/`](../../demisto_sdk/commands/common), the
"junk drawer" of cross-cutting helpers that everything else depends on.

Because this directory is imported from **everywhere**, changes here have
the largest blast radius in the repo. Be conservative.

## Modules to know

| Module | Purpose |
|---|---|
| [`tools.py`](../../demisto_sdk/commands/common/tools.py) | Generic file/path/yaml/json/git/version helpers. Look here before adding a new utility. |
| [`constants.py`](../../demisto_sdk/commands/common/constants.py) | Names of folders, content types, marketplaces, server versions, regex patterns. Reuse, don't duplicate. |
| [`content_constant_paths.py`](../../demisto_sdk/commands/common/content_constant_paths.py) | `CONTENT_PATH` and friends. Honours `DEMISTO_SDK_CONTENT_PATH`. |
| [`logger.py`](../../demisto_sdk/commands/common/logger.py) | The **only** sanctioned logger. Use `from … import logger`. |
| [`git_util.py`](../../demisto_sdk/commands/common/git_util.py) | `GitUtil` class — wraps GitPython. Replaces `git.Repo`. |
| [`handlers/`](../../demisto_sdk/commands/common/handlers) | `JSON_Handler`, `YAML_Handler`, `JSON5_Handler`, `XSOAR_Handler`. Always use these. |
| [`docker_helper.py`](../../demisto_sdk/commands/common/docker_helper.py), [`docker/`](../../demisto_sdk/commands/common/docker) | Docker SDK wrappers. |
| [`clients/`](../../demisto_sdk/commands/common/clients) | XSOAR / XSIAM HTTP clients (handles auth, retries, env vars). |
| [`errors.py`](../../demisto_sdk/commands/common/errors.py) | Domain exceptions. Subclass these instead of `Exception`. |
| [`StrEnum.py`](../../demisto_sdk/commands/common/StrEnum.py) | 3.9-safe `StrEnum`. Always import from here. |
| [`MDXServer.py`](../../demisto_sdk/commands/common/MDXServer.py), [`markdown_server/`](../../demisto_sdk/commands/common/markdown_server), [`markdown_lint.py`](../../demisto_sdk/commands/common/markdown_lint.py) | MDX validation for READMEs. Honour `DEMISTO_README_VALIDATION`. |
| [`native_image.py`](../../demisto_sdk/commands/common/native_image.py), [`docker_images_metadata.py`](../../demisto_sdk/commands/common/docker_images_metadata.py) | Native image / docker metadata. |
| [`schemas/`](../../demisto_sdk/commands/common/schemas) | Pykwalify schemas for content YAML/JSON. |
| [`hook_validations/`](../../demisto_sdk/commands/common/hook_validations) | Legacy validators (still consumed by `old_validate_manager`). New checks go under `commands/validate/validators/`, not here. |
| [`files/`](../../demisto_sdk/commands/common/files) | File-type abstractions. |
| [`content/`](../../demisto_sdk/commands/common/content) | Legacy content object model (predecessor of the content graph). |

## Hard rules

1. **No new direct imports of `json`, `ujson`, `orjson`, `json5`,
   `ruamel.yaml`, `logging`, `loguru`, `git.Repo`, `enum.StrEnum`,
   `distutils.version`, `packaging.version.LooseVersion`, or
   `str.StrEnum`.** They are blocked by ruff's `flake8-tidy-imports`
   ban list (see [`pyproject.toml`](../../pyproject.toml)).
2. **`logger` is defined here.** Be careful not to introduce import
   cycles. The logger module must remain importable with no side effects
   beyond loguru sink configuration.
3. **`tools.py` must stay pure-Python and side-effect free at import
   time.** Functions there are imported by *almost everything*, including
   the CLI entry point.
4. **Do not introduce new globals that read env vars at import time.**
   Read env vars inside functions or behind a cached helper, so test
   patching works.
5. **Constants in `constants.py` must be `Final`/`Enum`/`Literal`-typed
   where possible** and grouped near related ones. Don't append at the
   bottom; put new constants in the relevant section.
6. **`StrEnum` must come from
   [`StrEnum.py`](../../demisto_sdk/commands/common/StrEnum.py)** for
   Python 3.9/3.10 compatibility.

## Adding a new helper

Before adding a new function or class:

1. **Search first.** Use `grep` / `ripgrep` for similar names. Many
   utilities already exist with slightly different names (`get_yaml`,
   `get_yaml_object`, `load_yaml`, …) — pick one and extend it rather
   than creating a fourth.
2. **Pick the right module.** File/path/yaml/json/version/regex helpers
   go in `tools.py`. Constants go in `constants.py`. Domain logic
   probably doesn't belong in `common/` at all — put it next to the
   command that owns it.
3. **Type-annotate fully.** mypy `check_untyped_defs` is on, and
   downstream code will rely on the annotations.
4. **Add unit tests** under
   [`demisto_sdk/commands/common/tests/`](../../demisto_sdk/commands/common/tests).
5. **Document with a docstring** including `Args:` / `Returns:` /
   `Raises:`. These helpers are read often.
6. **Avoid surprising side effects** (filesystem writes, network calls,
   subprocess spawns) unless the function name makes it obvious.

## Backwards compatibility

`commands/common/` is consumed externally (by content authors, content
build scripts, partner tooling). Treat its public surface as **semver-
stable**:

- Don't rename or remove a public function/class without a deprecation
  shim and a `breaking` changelog entry.
- Adding optional kwargs is fine. Re-ordering positional args is not.
- Re-exports stay re-exported. Don't move a name without leaving an
  import shim for at least one minor version.

## Don'ts

- Don't add new modules under `hook_validations/`. The replacement is
  [`commands/validate/validators/`](../../demisto_sdk/commands/validate/validators).
- Don't add new modules under `content/`. The replacement is
  [`commands/content_graph/objects/`](../../demisto_sdk/commands/content_graph/objects).
- Don't introduce a second logger or output channel. Everything goes
  through `logger`.
- Don't introduce a wrapper that re-exports a banned module to bypass the
  ruff ban.
