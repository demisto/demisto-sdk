"""Strict pydantic schema for ``connector.yaml`` (Phase 1).

This module pins the schema of the top-level connector file used by
unified-connectors-content. It is plugged into the ST110 structure-
validation pipeline via :py:attr:`ConnectorParser.strict_object
<demisto_sdk.commands.content_graph.parsers.connector.ConnectorParser.strict_object>`,
so any extra or missing field in ``connector.yaml`` is reported as a
structure error like every other content item.

Phase 1 intentionally covers only ``connector.yaml``. The connector's
sub-files (``connection.yaml``, ``capabilities.yaml``, etc.) keep their
existing parser-level Pydantic sub-models for now; they'll get strict
equivalents (with ``extra=forbid``) in a follow-up once the connector
spec is fully stable.
"""

from typing import List, Optional

from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
)


class _StrictConnectorOwnership(BaseStrictModel):
    """``metadata.ownership`` block — required ``team``, optional ``maintainers``."""

    team: str
    maintainers: Optional[List[str]] = None


class _StrictConnectorMetadata(BaseStrictModel):
    """``metadata`` block — connector identity (title, vendor, ownership, …)."""

    title: str
    description: str
    version: str  # semver string, e.g. "1.0.0"
    category: str
    tags: Optional[List[str]] = None
    domain: Optional[str] = None
    vendor: str
    publisher: str
    author_image: Optional[str] = None
    ownership: _StrictConnectorOwnership


class _StrictConnectorSettings(BaseStrictModel):
    """``settings`` block — currently only ``allow_skip_verification``."""

    allow_skip_verification: Optional[bool] = None


class StrictConnector(BaseStrictModel):
    """Top-level schema for ``connector.yaml``.

    Inherits ``extra=forbid`` from :class:`BaseStrictModel` so any
    unrecognised key — at the top level or in nested blocks — surfaces
    as a structure error during validation.
    """

    id: str
    metadata: _StrictConnectorMetadata
    settings: Optional[_StrictConnectorSettings] = None
