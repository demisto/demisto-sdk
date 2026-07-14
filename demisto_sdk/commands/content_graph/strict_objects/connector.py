"""Strict Pydantic model for `connector.yaml`.

Mirrors the pattern used by
[`../strict_objects/integration.py`](../strict_objects/integration.py):
a thin hand-written wrapper on top of an auto-generated base, so that new
upstream fields become available with zero code changes here after the
UCC schemas are refreshed.

Runtime model discovery
-----------------------
The generated `ConnectorYaml` base is produced **in-memory** by
[`schema_loader.load_generated_modules`](schema_loader.py:1) from the
`connector.schema.json` file the infra CI job drops at the path pointed
to by `$UCC_SCHEMAS_DIR`. Nothing is committed to the SDK repo for the
generated Python; a local fallback under `strict_objects/schemas/` keeps
`pytest` and IDE workflows green.

Lazy resolution
---------------
`StrictConnector` is resolved on first *use* via :func:`get_strict_connector`,
not at module import time, so:
  * merely importing this module never triggers codegen or requires
    `datamodel-code-generator` to be installed;
  * SDK bootstraps that never touch a connector pay zero cost;
  * tests that swap `$UCC_SCHEMAS_DIR` via `monkeypatch` + `reset_cache`
    always see the new value.

If schemas / codegen dependency are unavailable at runtime,
`get_strict_connector()` returns `None`, and callers (parser + validator)
skip strict-schema validation without crashing the whole SDK.

Wired into `ConnectorParser.strict_object` so `validate_structure()` runs
on every parsed `connector.yaml`, populating `structure_errors`, which
ST110 then surfaces to users.
"""
from typing import Optional, Type

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel
from demisto_sdk.commands.content_graph.strict_objects.schema_loader import (
    SchemaLoaderError,
    get_generated_module,
)


def _build_strict_connector() -> Optional[Type[BaseStrictModel]]:
    """Assemble `StrictConnector` from the runtime-generated base class.

    Returns `None` (rather than raising) when:
      * `$UCC_SCHEMAS_DIR` is unset and no local fallback exists, OR
      * `datamodel-code-generator` is not installed, OR
      * the schemas dir exists but has no `connector.schema.json`.

    Callers treat a `None` result as "skip strict validation for this
    content type" - same pattern used for other optional strict models.
    """
    try:
        module = get_generated_module("connector")
    except SchemaLoaderError:
        # Explicit env-var pointing at a bad dir, etc: log-friendly None.
        return None
    if module is None:
        return None
    generated = getattr(module, "ConnectorYaml", None)
    if generated is None:
        return None

    # BaseStrictModel already sets `Extra.forbid` and adds the shared
    # None-prevention validator; the generated class contributes every
    # field + upstream constraint (regex, min_length, min_items, ...).
    class StrictConnector(generated, BaseStrictModel):  # type: ignore[misc,valid-type]
        """Strict schema for connector.yaml, auto-synced with UCC.

        Any new field added to the upstream `connector.schema.json`
        becomes available here on the next SDK process (or after
        `schema_loader.reset_cache()`) - no edit required in this file.
        """

    return StrictConnector


# Sentinel used to distinguish "not resolved yet" from "resolved to None".
_UNSET = object()
_cached: object = _UNSET


def get_strict_connector() -> Optional[Type[BaseStrictModel]]:
    """Return the resolved `StrictConnector` class, or `None` if unavailable.

    Resolves lazily on first call, then memoizes. Call
    :func:`schema_loader.reset_cache` (typically from a test fixture) if
    you need to force a re-resolution after moving `$UCC_SCHEMAS_DIR`.
    """
    global _cached
    if _cached is _UNSET:
        _cached = _build_strict_connector()
    return _cached  # type: ignore[return-value]


def reset_strict_connector_cache() -> None:
    """Drop the memoized `StrictConnector`; the next call re-resolves it."""
    global _cached
    _cached = _UNSET
