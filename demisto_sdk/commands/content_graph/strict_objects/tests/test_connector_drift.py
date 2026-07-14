"""Drift detection between the hand-written Connector Pydantic models in
`objects/connector.py` and the models built at runtime from
`$UCC_SCHEMAS_DIR/connector.schema.json`.

Skips when the schemas / codegen dep are unavailable.
"""
from typing import Set, Type

import pydantic
import pytest


def _field_names(model: Type[pydantic.BaseModel]) -> Set[str]:
    return set(model.__fields__.keys())


def _missing(hand: Type[pydantic.BaseModel], upstream: Type[pydantic.BaseModel]) -> Set[str]:
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
        pytest.skip("No connector schema available. Set $UCC_SCHEMAS_DIR.")
    return module


def test_connector_metadata_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorMetadata

    upstream = _load_connector_schema_module().Metadata
    missing = _missing(ConnectorMetadata, upstream)
    assert not missing, (
        f"ConnectorMetadata is missing upstream fields: {sorted(missing)}"
    )


def test_connector_settings_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorSettings

    upstream = _load_connector_schema_module().Settings
    missing = _missing(ConnectorSettings, upstream)
    assert not missing, (
        f"ConnectorSettings is missing upstream fields: {sorted(missing)}"
    )


def test_connector_ownership_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorOwnership

    upstream = _load_connector_schema_module().Ownership
    missing = _missing(ConnectorOwnership, upstream)
    assert not missing, (
        f"ConnectorOwnership is missing upstream fields: {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "hand_model_name",
    ["ConnectorMetadata", "ConnectorSettings", "ConnectorOwnership"],
)
def test_report_hand_written_fields_not_in_upstream(hand_model_name, capsys):
    """Informational: hand-written fields upstream doesn't know about."""
    module = _load_connector_schema_module()
    from demisto_sdk.commands.content_graph.objects import connector as objects_connector

    hand = getattr(objects_connector, hand_model_name)
    upstream_map = {
        "ConnectorMetadata": module.Metadata,
        "ConnectorSettings": module.Settings,
        "ConnectorOwnership": module.Ownership,
    }
    extras = _field_names(hand) - _field_names(upstream_map[hand_model_name])
    if extras:
        print(f"\n[INFO] {hand_model_name} declares extra fields: {sorted(extras)}")
