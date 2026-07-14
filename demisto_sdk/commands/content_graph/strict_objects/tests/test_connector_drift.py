"""Phase 0 drift detection: compares the hand-written Connector Pydantic models
in `demisto_sdk/commands/content_graph/objects/connector.py` against the
`ConnectorYaml` / `Metadata` / `Settings` / `Ownership` models generated from
the upstream UCC JSON Schema at
`demisto_sdk/commands/content_graph/strict_objects/schemas/connector.schema.json`.

If any of these tests fail, either:
  - Update the hand-written model in `objects/connector.py` to add the missing
    upstream field(s), OR
  - Re-run `datamodel-codegen` against the latest `connector.schema.json` to
    refresh `_connector_generated.py`.

This module exists only for the Phase 0 proof-of-concept and can be deleted or
promoted to a stricter parity test once the hand-written classes are replaced
by the generated ones.
"""
from typing import Set, Type

import pydantic
import pytest

from demisto_sdk.commands.content_graph.objects.connector import (
    ConnectorMetadata,
    ConnectorOwnership,
    ConnectorSettings,
)
from demisto_sdk.commands.content_graph.strict_objects._connector_generated import (
    Metadata as UpstreamMetadata,
    Ownership as UpstreamOwnership,
    Settings as UpstreamSettings,
)


def _field_names(model: Type[pydantic.BaseModel]) -> Set[str]:
    """Return the set of Pydantic field names declared on `model`."""
    return set(model.__fields__.keys())


def _missing(hand: Type[pydantic.BaseModel], upstream: Type[pydantic.BaseModel]) -> Set[str]:
    """Fields present on `upstream` but not on `hand`."""
    return _field_names(upstream) - _field_names(hand)


def test_connector_metadata_covers_all_upstream_fields():
    missing = _missing(ConnectorMetadata, UpstreamMetadata)
    assert not missing, (
        f"objects/connector.py::ConnectorMetadata is missing fields that exist in "
        f"the upstream connector.schema.json: {sorted(missing)}. "
        f"Either add them to ConnectorMetadata or re-run datamodel-codegen if the "
        f"local schema copy is stale."
    )


def test_connector_settings_covers_all_upstream_fields():
    missing = _missing(ConnectorSettings, UpstreamSettings)
    assert not missing, (
        f"objects/connector.py::ConnectorSettings is missing fields that exist in "
        f"the upstream connector.schema.json: {sorted(missing)}."
    )


def test_connector_ownership_covers_all_upstream_fields():
    missing = _missing(ConnectorOwnership, UpstreamOwnership)
    assert not missing, (
        f"objects/connector.py::ConnectorOwnership is missing fields that exist in "
        f"the upstream connector.schema.json: {sorted(missing)}."
    )


@pytest.mark.parametrize(
    "hand_model, upstream_model, name",
    [
        (ConnectorMetadata, UpstreamMetadata, "ConnectorMetadata"),
        (ConnectorSettings, UpstreamSettings, "ConnectorSettings"),
        (ConnectorOwnership, UpstreamOwnership, "ConnectorOwnership"),
    ],
)
def test_report_hand_written_fields_not_in_upstream(hand_model, upstream_model, name):
    """Informational: hand-written fields that upstream does not know about.

    This test does NOT fail on extras (the hand model may legitimately add
    graph-only fields), but it prints them so a reviewer can decide whether
    they are drift or intentional additions.
    """
    extras = _field_names(hand_model) - _field_names(upstream_model)
    if extras:
        print(f"\n[INFO] {name} declares fields not in upstream schema: {sorted(extras)}")
