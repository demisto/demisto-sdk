"""Tests for the runtime UCC schema loader ($UCC_SCHEMAS_DIR flow)."""
import json
from pathlib import Path

import pydantic
import pytest

from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
    ENV_VAR,
    SchemaLoaderError,
    get_schemas_dir,
    load_generated_modules,
    reset_cache,
)

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
    """Files under `definitions/` must also produce generated modules."""
    _write_schema_tree(tmp_path)
    monkeypatch.setenv(ENV_VAR, str(tmp_path))

    modules = load_generated_modules()
    sample_cls = getattr(modules["sample"], "SampleYaml", None)
    assert sample_cls is not None
    assert issubclass(sample_cls, pydantic.BaseModel)

    tag_module = modules.get("tag")
    assert tag_module is not None, f"got module keys: {sorted(modules)}"
    tag_cls = getattr(tag_module, "Tag", None)
    assert tag_cls is not None
    assert tag_cls(name="prod").name == "prod"

    instance = sample_cls(id="abc", meta={"name": "my-thing"})
    assert instance.meta.name == "my-thing"


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
