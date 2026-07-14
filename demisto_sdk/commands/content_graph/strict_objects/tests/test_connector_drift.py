"""Drift detection between the hand-written Connector Pydantic models in
`demisto_sdk/commands/content_graph/objects/connector.py` and the models
built at runtime from the upstream UCC JSON Schemas via
[`../schema_loader.py`](../schema_loader.py).

The generated models are produced in-memory by the loader (either from the
committed fallback schemas under `../schemas/` or from `$UCC_SCHEMAS_DIR`),
so every test uses `pytest.importorskip` semantics: if the loader has
nothing to work with (no schemas + no codegen dep), the test skips.

When a test fails, the fix is one of:
  - Add the missing field(s) to the hand-written class in
    `objects/connector.py` (short-term).
  - Refresh the committed fallback schema, OR
  - Bump the upstream schema in the infra CI job and re-run.
"""
from typing import Set, Type

import pydantic
import pytest


def _field_names(model: Type[pydantic.BaseModel]) -> Set[str]:
    """Return the set of Pydantic field names declared on `model`."""
    return set(model.__fields__.keys())


def _missing(hand: Type[pydantic.BaseModel], upstream: Type[pydantic.BaseModel]) -> Set[str]:
    """Fields present on `upstream` but not on `hand`."""
    return _field_names(upstream) - _field_names(hand)


def _load_connector_schema_module():
    """Return the runtime-loaded connector schema module, or skip the test."""
    from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
        SchemaLoaderError,
        get_generated_module,
    )

    try:
        module = get_generated_module("connector")
    except SchemaLoaderError as exc:
        pytest.skip(f"Schema loader unavailable: {exc}")
    if module is None:
        pytest.skip(
            "No connector schema available. Set $UCC_SCHEMAS_DIR or commit a "
            "fallback under strict_objects/schemas/connector.schema.json."
        )
    return module


def test_connector_metadata_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorMetadata

    upstream = _load_connector_schema_module().Metadata
    missing = _missing(ConnectorMetadata, upstream)
    assert not missing, (
        f"objects/connector.py::ConnectorMetadata is missing fields that exist "
        f"in the upstream connector.schema.json: {sorted(missing)}. "
        f"Either add them to ConnectorMetadata or refresh the schema/regen if "
        f"the local copy is stale."
    )


def test_connector_settings_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorSettings

    upstream = _load_connector_schema_module().Settings
    missing = _missing(ConnectorSettings, upstream)
    assert not missing, (
        f"objects/connector.py::ConnectorSettings is missing fields that exist "
        f"in the upstream connector.schema.json: {sorted(missing)}."
    )


def test_connector_ownership_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorOwnership

    upstream = _load_connector_schema_module().Ownership
    missing = _missing(ConnectorOwnership, upstream)
    assert not missing, (
        f"objects/connector.py::ConnectorOwnership is missing fields that exist "
        f"in the upstream connector.schema.json: {sorted(missing)}."
    )


@pytest.mark.parametrize(
    "hand_model_name",
    ["ConnectorMetadata", "ConnectorSettings", "ConnectorOwnership"],
)
def test_report_hand_written_fields_not_in_upstream(hand_model_name, capsys):
    """Informational: hand-written fields that upstream does not know about.

    Does NOT fail on extras (the hand model may legitimately add graph-only
    fields), but prints them so a reviewer can decide whether they are drift
    or intentional additions.
    """
    module = _load_connector_schema_module()
    from demisto_sdk.commands.content_graph.objects import connector as objects_connector

    hand = getattr(objects_connector, hand_model_name)
    upstream_map = {
        "ConnectorMetadata": module.Metadata,
        "ConnectorSettings": module.Settings,
        "ConnectorOwnership": module.Ownership,
    }
    upstream = upstream_map[hand_model_name]

    extras = _field_names(hand) - _field_names(upstream)
    if extras:
        print(f"\n[INFO] {hand_model_name} declares fields not in upstream: {sorted(extras)}")
