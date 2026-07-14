"""Strict Pydantic model for `connector.yaml`.

Mirrors the pattern used by
[`../strict_objects/integration.py`](../strict_objects/integration.py):
a thin hand-written wrapper on top of an auto-generated base, so that new
upstream fields become available with zero code changes here after the next
`bash regenerate.sh` run.

The generated base is imported lazily so that a missing generated module
(i.e. the infra CI has not yet copied the UCC schemas into `schemas/`) does
not break the whole SDK at import time.

Wired into `ConnectorParser.strict_object` so `validate_structure()` runs
on every parsed `connector.yaml`, populating `structure_errors`, which the
ST110 validator then surfaces to users.
"""
from typing import TYPE_CHECKING, Type

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel

if TYPE_CHECKING:
    # Static type only; keeps mypy/IDE happy without forcing the generated
    # module to exist at import time.
    from demisto_sdk.commands.content_graph.strict_objects._generated.connector_schema import (
        ConnectorYaml as _ConnectorYamlGenerated,
    )


def _load_strict_connector() -> Type[BaseStrictModel]:
    """Build `StrictConnector` on first use.

    Kept as a function (rather than a top-level import) so a missing
    generated module surfaces as a clear runtime error at the exact call
    site instead of an unrelated ImportError deep in the SDK bootstrap.
    """
    try:
        from demisto_sdk.commands.content_graph.strict_objects._generated.connector_schema import (
            ConnectorYaml as _ConnectorYamlGenerated,
        )
    except ImportError as exc:
        raise ImportError(
            "Generated connector schema module is missing. Run "
            "`bash demisto_sdk/commands/content_graph/strict_objects/regenerate.sh` "
            "after the infra CI has copied connector.schema.json into "
            "strict_objects/schemas/."
        ) from exc

    # BaseStrictModel already sets `Extra.forbid` and adds the shared
    # None-prevention validator; the generated class contributes every
    # field + upstream constraint (regex, min_length, min_items, ...).
    class StrictConnector(_ConnectorYamlGenerated, BaseStrictModel):  # type: ignore[misc]
        """Strict schema for connector.yaml, auto-synced with UCC.

        Any new field added to the upstream `connector.schema.json` becomes
        available here after the next `bash regenerate.sh` run - no edit
        required in this file.
        """

    return StrictConnector


# Lazy import guard: expose `StrictConnector` as a module-level name only when
# the generated module is available, so this module can be imported by callers
# that never actually validate a connector (avoiding hard-failing test
# collection when the schemas have not yet been dropped in).
try:
    StrictConnector: Type[BaseStrictModel] = _load_strict_connector()
except ImportError:
    StrictConnector = None  # type: ignore[assignment]
