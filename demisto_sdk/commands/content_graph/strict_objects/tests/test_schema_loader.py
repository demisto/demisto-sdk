"""Tests for the runtime UCC schema loader.

Verifies the env-var contract that the infra CI relies on:

  1. `$UCC_SCHEMAS_DIR` overrides the local fallback.
  2. A `definitions/` subfolder is staged so cross-file `$ref` resolves.
  3. Pointing at a bad path raises a clear `SchemaLoaderError` instead of
     silently degrading (loud misconfiguration).
  4. Unsetting the var falls back to the committed `schemas/` folder.
"""
import json
import os
from pathlib import Path

import pydantic
import pytest

from demisto_sdk.commands.content_graph.strict_objects import schema_loader
from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
    ENV_VAR,
    SchemaLoaderError,
    get_schemas_dir,
    load_generated_modules,
    reset_cache,
)


# Minimal schema exercising: top-level $id, an object with a required
# field, and a nested object. We keep this self-contained (no $ref) so
# the test does not depend on datamodel-codegen's URI resolution
# semantics (which vary across versions); real UCC schemas exercise $ref
# resolution end-to-end via the drift tests + infra CI.
_MINIMAL_MAIN_SCHEMA = {
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

# A separate schema file that mimics what infra will drop into
# `definitions/`, so we prove the loader actually stages that subfolder.
_MINIMAL_DEFS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "definitions/tag.schema.json",
    "title": "Tag",
    "type": "object",
    "additionalProperties": False,
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "minLength": 1},
    },
}


@pytest.fixture(autouse=True)
def _reset_loader_cache():
    """Every test starts from a cold cache so `$UCC_SCHEMAS_DIR` changes
    actually take effect."""
    from demisto_sdk.commands.content_graph.strict_objects.connector import (
        reset_strict_connector_cache,
    )

    reset_cache()
    reset_strict_connector_cache()
    yield
    reset_cache()
    reset_strict_connector_cache()


def _write_schema_tree(root: Path) -> None:
    """Populate `root` with the same top-level + `definitions/` layout the
    infra CI is expected to produce."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "definitions").mkdir(exist_ok=True)
    (root / "sample.schema.json").write_text(json.dumps(_MINIMAL_MAIN_SCHEMA))
    (root / "definitions" / "tag.schema.json").write_text(
        json.dumps(_MINIMAL_DEFS_SCHEMA)
    )


def test_env_var_takes_precedence_over_local_fallback(
    tmp_path, monkeypatch
):
    """When `$UCC_SCHEMAS_DIR` is set, the loader must ignore the local
    committed schemas folder and produce a module for the env-var schemas."""
    _write_schema_tree(tmp_path)
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    resolved = get_schemas_dir()
    assert resolved == tmp_path.resolve()

    modules = load_generated_modules()
    assert "sample" in modules, (
        f"expected a module keyed by 'sample' (from sample.schema.json); "
        f"got: {sorted(modules)}"
    )


def test_definitions_subfolder_is_staged_and_generated(
    tmp_path, monkeypatch
):
    """Files under `definitions/` must be staged and produce their own
    generated modules, proving the loader preserves that subfolder (which
    real UCC schemas need for cross-file `$ref` resolution)."""
    _write_schema_tree(tmp_path)
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    modules = load_generated_modules()
    # Top-level schema produced a module.
    sample_yaml_cls = getattr(modules["sample"], "SampleYaml", None)
    assert sample_yaml_cls is not None, (
        f"module for sample.schema.json is missing SampleYaml class; "
        f"got symbols: "
        f"{[n for n in vars(modules['sample']) if not n.startswith('_')]}"
    )
    assert issubclass(sample_yaml_cls, pydantic.BaseModel)

    # And the file under definitions/ was staged + generated.
    tag_module = modules.get("tag")
    assert tag_module is not None, (
        f"definitions/tag.schema.json was not staged / generated; "
        f"got module keys: {sorted(modules)}"
    )
    tag_cls = getattr(tag_module, "Tag", None)
    assert tag_cls is not None
    assert issubclass(tag_cls, pydantic.BaseModel)
    assert tag_cls(name="prod").name == "prod"

    # Sanity: the top-level model actually validates a real payload.
    instance = sample_yaml_cls(id="abc", meta={"name": "my-thing"})
    assert instance.id == "abc"
    assert instance.meta.name == "my-thing"


def test_env_var_pointing_at_bad_path_raises_loudly(monkeypatch, tmp_path):
    """A miswired infra CI must fail loudly, not silently degrade."""
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv(ENV_VAR, str(missing))

    with pytest.raises(SchemaLoaderError, match="does not exist"):
        get_schemas_dir()


def test_unset_env_var_falls_back_to_committed_schemas(monkeypatch):
    """Without the env var, the loader must use the committed
    `strict_objects/schemas/` folder so local dev + tests still work."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    resolved = get_schemas_dir()
    assert resolved is not None
    assert resolved.name == "schemas"
    # And the committed connector schema must be discoverable via the loader.
    modules = load_generated_modules()
    assert "connector" in modules, (
        f"expected fallback loader to expose the committed connector schema; "
        f"got: {sorted(modules)}"
    )
