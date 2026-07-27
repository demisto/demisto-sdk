"""Sanity checks: every runtime-generated module imports cleanly and
exposes at least one pydantic.BaseModel with a resolvable schema.

Skips when the loader has nothing (no `$UCC_SCHEMAS_DIR`, missing dep).
"""

import pydantic
import pytest


def _try_load():
    from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
        SchemaLoaderError,
        load_generated_modules,
    )

    try:
        modules = load_generated_modules()
    except SchemaLoaderError as exc:
        pytest.skip(f"Schema loader unavailable: {exc}")
    if not modules:
        pytest.skip("No schemas discovered. Set $UCC_SCHEMAS_DIR.")
    return modules


def test_loader_produces_at_least_one_module():
    modules = _try_load()
    assert modules


def test_every_generated_module_exposes_a_basemodel():
    modules = _try_load()
    for stem, module in modules.items():
        model_classes = [
            obj
            for obj in vars(module).values()
            if isinstance(obj, type)
            and issubclass(obj, pydantic.BaseModel)
            and obj is not pydantic.BaseModel
        ]
        assert (
            model_classes
        ), f"module {stem!r} defines no pydantic.BaseModel subclasses"
        for cls in model_classes:
            cls.schema()
