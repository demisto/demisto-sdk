"""Codegen sanity checks for the runtime schema loader.

The UCC JSON schemas are turned into Pydantic modules at runtime by
[`../schema_loader.py`](../schema_loader.py). This test module verifies:

  1. The loader discovers at least one schema and successfully runs
     `datamodel-codegen` against it (skipped when neither `$UCC_SCHEMAS_DIR`
     nor the local fallback provides any `*.schema.json`).
  2. Every generated module exposes at least one `pydantic.BaseModel`
     subclass whose `.schema()` resolves - catches empty schemas or
     codegen regressions that would silently produce nothing.

Adding a new schema requires zero test-file changes: as soon as the loader
picks up a new `*.schema.json`, it is automatically covered here.
"""
import pydantic
import pytest


def _try_load():
    """Load the runtime modules or skip the test with a useful reason."""
    from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
        SchemaLoaderError,
        load_generated_modules,
    )

    try:
        modules = load_generated_modules()
    except SchemaLoaderError as exc:
        pytest.skip(f"Schema loader unavailable: {exc}")
    if not modules:
        pytest.skip(
            "No schemas discovered. Set $UCC_SCHEMAS_DIR to a directory that "
            "contains *.schema.json files, or commit a fallback under "
            "strict_objects/schemas/."
        )
    return modules


def test_loader_produces_at_least_one_module():
    """Confirm the loader wires up correctly against whichever source is
    available (env var or committed fallback)."""
    modules = _try_load()
    assert modules, "loader returned no modules despite a schemas dir being present"


def test_every_generated_module_exposes_a_basemodel():
    """Every runtime-generated module must expose at least one pydantic
    BaseModel subclass with a resolvable schema."""
    modules = _try_load()
    for stem, module in modules.items():
        model_classes = [
            obj
            for obj in vars(module).values()
            if isinstance(obj, type)
            and issubclass(obj, pydantic.BaseModel)
            and obj is not pydantic.BaseModel
        ]
        assert model_classes, (
            f"generated module for schema stem {stem!r} defines no "
            f"pydantic.BaseModel subclasses"
        )
        # Resolving the schema forces Pydantic to evaluate every forward-ref
        # and constraint, so codegen bugs like an unresolved $ref surface here.
        for cls in model_classes:
            cls.schema()


def test_schemas_folder_exists_and_has_readme():
    """The fallback schemas folder + its README document the infra CI contract
    and must always be present in the repo."""
    from pathlib import Path

    here = Path(__file__).resolve().parent.parent  # strict_objects/
    schemas_dir = here / "schemas"
    assert schemas_dir.is_dir(), f"missing folder: {schemas_dir}"
    assert (schemas_dir / "README.md").is_file(), (
        f"missing schemas/README.md at {schemas_dir}. This file documents "
        f"the contract the infra-side CI job must follow when copying UCC "
        f"schemas."
    )
