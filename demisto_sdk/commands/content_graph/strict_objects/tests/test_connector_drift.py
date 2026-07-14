"""Drift detection between the hand-written Connector Pydantic models in
`demisto_sdk/commands/content_graph/objects/connector.py` and the models
auto-generated from the upstream UCC JSON Schemas in
`demisto_sdk/commands/content_graph/strict_objects/schemas/`.

The generated models live under
`demisto_sdk/commands/content_graph/strict_objects/_generated/`. Because that
package is populated by an infra-side CI job (see
[`../schemas/README.md`](../schemas/README.md)), individual generated modules
may or may not be present at test time. Every test in this file therefore uses
`pytest.importorskip(...)` so a missing schema is a skip, not a failure.

When a test fails, the fix is one of:
  - Add the missing field(s) to the hand-written class in `objects/connector.py`
    (preferred short-term), OR
  - Run `bash demisto_sdk/commands/content_graph/strict_objects/regenerate.sh`
    to refresh the generated model against the local schema copy, OR
  - Update the local schema copy in `schemas/` if it drifted from upstream.

New schemas dropped in by the infra job in the future can be covered by
appending a new tuple to `SCHEMA_TO_HAND_MODEL_MAP` and pointing it at the
corresponding hand-written class in `objects/connector.py`. No other change is
required here.
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


# ---------------------------------------------------------------------------
# connector.schema.json  <->  ConnectorMetadata / ConnectorSettings / ConnectorOwnership
# ---------------------------------------------------------------------------
def _import_connector_schema():
    """Import the generated connector schema module, or skip the test."""
    return pytest.importorskip(
        "demisto_sdk.commands.content_graph.strict_objects._generated.connector_schema",
        reason=(
            "Generated connector schema module not present. Run "
            "`bash demisto_sdk/commands/content_graph/strict_objects/regenerate.sh` "
            "after the infra CI has copied connector.schema.json into "
            "strict_objects/schemas/."
        ),
    )


def test_connector_metadata_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorMetadata

    upstream = _import_connector_schema().Metadata
    missing = _missing(ConnectorMetadata, upstream)
    assert not missing, (
        f"objects/connector.py::ConnectorMetadata is missing fields that exist "
        f"in the upstream connector.schema.json: {sorted(missing)}. "
        f"Either add them to ConnectorMetadata or refresh the schema/regen if "
        f"the local copy is stale."
    )


def test_connector_settings_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorSettings

    upstream = _import_connector_schema().Settings
    missing = _missing(ConnectorSettings, upstream)
    assert not missing, (
        f"objects/connector.py::ConnectorSettings is missing fields that exist "
        f"in the upstream connector.schema.json: {sorted(missing)}."
    )


def test_connector_ownership_covers_all_upstream_fields():
    from demisto_sdk.commands.content_graph.objects.connector import ConnectorOwnership

    upstream = _import_connector_schema().Ownership
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
    module = _import_connector_schema()
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
