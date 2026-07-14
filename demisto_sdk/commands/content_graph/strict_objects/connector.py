"""Strict Pydantic model for `connector.yaml`, built at runtime from
`$UCC_SCHEMAS_DIR/connector.schema.json`.

Resolved lazily via :func:`get_strict_connector` so importing this module
never triggers codegen. Returns `None` when the loader has nothing (env
var unset, codegen dep missing) so callers can degrade gracefully.

Wired into `ConnectorParser.strict_object`; ST110 surfaces upstream schema
drift as `structure_errors`.
"""
from typing import Optional, Type

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel
from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
    SchemaLoaderError,
    get_generated_module,
)


def _build_strict_connector() -> Optional[Type[BaseStrictModel]]:
    """Assemble `StrictConnector` from the runtime-generated base class."""
    try:
        module = get_generated_module("connector")
    except SchemaLoaderError:
        return None
    if module is None:
        return None
    generated = getattr(module, "ConnectorYaml", None)
    if generated is None:
        return None

    class StrictConnector(generated, BaseStrictModel):  # type: ignore[misc,valid-type]
        """Strict schema for connector.yaml, auto-synced with UCC."""

    return StrictConnector


_UNSET = object()
_cached: object = _UNSET


def get_strict_connector() -> Optional[Type[BaseStrictModel]]:
    """Resolve `StrictConnector` lazily; memoized after first call."""
    global _cached
    if _cached is _UNSET:
        _cached = _build_strict_connector()
    return _cached  # type: ignore[return-value]


def reset_strict_connector_cache() -> None:
    """Drop the memoized class; next call re-resolves it (tests only)."""
    global _cached
    _cached = _UNSET
