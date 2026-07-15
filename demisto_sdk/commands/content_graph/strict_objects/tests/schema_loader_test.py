"""Tests for the runtime UCC schema loader ($UCC_SCHEMAS_DIR flow)."""

from pathlib import Path

import pydantic
import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
    ENV_VAR,
    SchemaLoaderError,
    get_schemas_dir,
    load_generated_modules,
    reset_cache,
)

json = JSON_Handler()

# Minimal self-contained schemas: no $ref (avoids datamodel-codegen URI
# quirks). Real UCC schemas exercise $ref end-to-end via the drift tests.
_MAIN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "sample.schema.json",
    "title": "SampleYaml",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "meta"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "meta": {
            "title": "Meta",
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "default": "0.0.0"},
            },
        },
    },
}

_DEFS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "definitions/tag.schema.json",
    "title": "Tag",
    "type": "object",
    "additionalProperties": False,
    "required": ["name"],
    "properties": {"name": {"type": "string", "minLength": 1}},
}


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    from demisto_sdk.commands.content_graph.strict_objects.connector import (
        reset_strict_connector_cache,
    )

    reset_cache()
    reset_strict_connector_cache()
    yield
    reset_cache()
    reset_strict_connector_cache()


def _write_schema_tree(root: Path) -> None:
    """Populate `root` with top-level schema + `definitions/` file."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "definitions").mkdir(exist_ok=True)
    (root / "sample.schema.json").write_text(json.dumps(_MAIN_SCHEMA))
    (root / "definitions" / "tag.schema.json").write_text(json.dumps(_DEFS_SCHEMA))


def test_env_var_resolves_to_correct_dir(tmp_path, monkeypatch):
    _write_schema_tree(tmp_path)
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    assert get_schemas_dir() == tmp_path.resolve()
    assert "sample" in load_generated_modules()


def test_definitions_subfolder_is_staged_and_generated(tmp_path, monkeypatch):
    """Top-level schemas produce generated modules; orphan `definitions/`
    files (not referenced by any top-level schema) are staged for peer-`$ref`
    resolution but not codegen'd as standalone modules.

    Rationale: only top-level `<name>.schema.json` files are contract
    surfaces. Files under `definitions/` exist to be `$ref`-ed; codegen
    pulls them in transitively when a top-level schema references them,
    so calling codegen on them separately produces empty stub modules
    that collide with the transitively-generated ones.
    """
    _write_schema_tree(tmp_path)
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    modules = load_generated_modules()
    sample_cls = getattr(modules["sample"], "SampleYaml", None)
    assert sample_cls is not None
    assert issubclass(sample_cls, pydantic.BaseModel)

    instance = sample_cls(id="abc", meta={"name": "my-thing"})
    assert instance.meta.name == "my-thing"

    # `tag.schema.json` is under `definitions/` and no top-level schema
    # references it, so it is intentionally not exposed as a module.
    assert "tag" not in modules, f"unexpected orphan module: keys={sorted(modules)}"


def test_bad_env_var_path_raises_loudly(monkeypatch, tmp_path):
    """Misconfigured infra CI must fail loudly, not silently."""
    monkeypatch.setenv(ENV_VAR, str(tmp_path / "does-not-exist"))
    with pytest.raises(SchemaLoaderError, match="does not exist"):
        get_schemas_dir()


def test_unset_env_var_returns_empty(monkeypatch):
    """No env var -> no schemas discovered; loader returns `{}`."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert get_schemas_dir() is None
    assert load_generated_modules() == {}


# --- Regression: definitions files referenced via sibling `$ref` -------------
# The upstream UCC schemas reference `definitions/*.schema.json` peers as
# `"$ref": "foo.schema.json"` (not `"definitions/foo.schema.json"`). Before
# the fix, `_stage_schemas` only copied definitions under `stage/definitions/`,
# so datamodel-codegen crashed with `[Errno 2] No such file or directory:
# '<stage>/foo.schema.json'`. The loader must mirror definitions to the stage
# root so sibling-style refs resolve.

_PEER_REF_MAIN = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "widget.schema.json",
    "title": "Widget",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "tag"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        # Sibling-style ref, matching the upstream UCC pattern.
        "tag": {"$ref": "tag.schema.json"},
    },
}

_PEER_REF_TAG = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    # No `$id` on purpose: the upstream UCC definitions schemas rely on the
    # file's on-disk location for URI resolution, not on a self-declared $id.
    # Setting `$id: "tag.schema.json"` here would make datamodel-codegen see
    # two files with identical $ids at different paths (stage root and
    # stage/definitions/) and mangle the relative resolution.
    "title": "Tag",
    "type": "object",
    "additionalProperties": False,
    "required": ["name"],
    "properties": {"name": {"type": "string", "minLength": 1}},
}


def test_definitions_resolvable_via_sibling_ref(tmp_path, monkeypatch):
    """Definitions referenced as siblings (no `definitions/` prefix) must resolve.

    Regression for the UCC schema layout that broke codegen in CI:
    `connector.schema.json` references `metadata.schema.json` as a peer file
    via `"$ref": "metadata.schema.json"`, but staging only placed the file
    under `definitions/`, so codegen crashed with `[Errno 2] No such file or
    directory: '<stage>/metadata.schema.json'`. The loader must mirror
    definitions to the stage root so sibling-style refs resolve.
    """
    (tmp_path / "definitions").mkdir()
    (tmp_path / "widget.schema.json").write_text(json.dumps(_PEER_REF_MAIN))
    (tmp_path / "definitions" / "tag.schema.json").write_text(json.dumps(_PEER_REF_TAG))
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    # Codegen must succeed - previously raised SchemaLoaderError with
    # `[Errno 2] No such file or directory: '<stage>/tag.schema.json'`.
    modules = load_generated_modules()
    assert "widget" in modules, f"got module keys: {sorted(modules)}"
    widget_cls = getattr(modules["widget"], "Widget", None)
    assert widget_cls is not None
    instance = widget_cls(id="w1", tag={"name": "prod"})
    assert instance.tag.name == "prod"


def test_get_generated_module_hard_fails_when_env_var_set(tmp_path, monkeypatch):
    """When the operator opted in via `$UCC_SCHEMAS_DIR`, codegen failures
    must NOT be swallowed silently by `get_generated_module`.

    Silent swallow was the reason CI showed `All validations passed` even
    though `[UCC-schema-loader] datamodel-codegen failed ...` had just been
    logged - a false-green run that hid the fact that strict validation
    never actually ran.
    """
    from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
        get_generated_module,
    )

    # Deliberately broken JSON schema -> codegen will raise, wrapped as
    # SchemaLoaderError by load_generated_modules.
    (tmp_path / "broken.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "broken.schema.json",
                "type": "object",
                # Reference a peer file that does not exist anywhere.
                "properties": {"x": {"$ref": "nowhere.schema.json"}},
            }
        )
    )
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    with pytest.raises(SchemaLoaderError):
        get_generated_module("broken")


def test_get_generated_module_silent_when_env_var_unset(monkeypatch):
    """When `$UCC_SCHEMAS_DIR` is unset, `get_generated_module` stays silent.

    This is the non-strict / opt-out mode. Only the opt-in path (env var set)
    should propagate SchemaLoaderError.
    """
    from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
        get_generated_module,
    )

    monkeypatch.delenv(ENV_VAR, raising=False)
    assert get_generated_module("anything") is None
