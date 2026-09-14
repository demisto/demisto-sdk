"""CO169 - IsNoDuplicateHandlerIntegrationValidator.

Per §3.8, handler ↔ integration is **1:1 per connector**. No two
handlers in the same connector may share the same
``triggering.labels.xsoar-integration-id``.

Rationale
---------
If two handlers both claim the same ``xsoar-integration-id``, the
runtime dispatcher has no unambiguous handler to route to for that
integration's events/actions. Every downstream cross-repo validator
(CO164 for integration existence, CO165 for pack match) becomes
ambiguous because "the handler for X" is no longer a single lookup.
Enforcing 1:1 keeps the routing invariant intact.

Scope
-----
Runs on every connector. Handlers with no
``xsoar-integration-id`` label are ignored (CO164 already flags
those separately for the missing-label case).

Per-finding granularity
-----------------------
One ``ValidationResult`` per **duplicated integration id** (not per
offending handler pair). If three handlers share the same
integration id, one result cites all three (comma-joined, sorted).

Path routing: first offending handler's ``file_path`` (best-effort
— multiple handlers are involved but ``.connector-ignore`` needs a
single path anchor).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from demisto_sdk.commands.content_graph.objects.connector import (
    Connector,
    HandlerData,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsNoDuplicateHandlerIntegrationValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO169"
    description = (
        "No two handlers in the same connector may share the same "
        "`triggering.labels.xsoar-integration-id`. Handler ↔ "
        "integration is 1:1 per connector."
    )
    rationale = (
        "The runtime dispatcher routes integration events / actions "
        "to the handler that claims the corresponding "
        "`xsoar-integration-id`. If two handlers claim the same id "
        "the routing is ambiguous and downstream cross-repo "
        "validators (CO164, CO165) can no longer disambiguate. The "
        "1:1 invariant keeps routing deterministic and simplifies "
        "every cross-reference."
    )
    error_message = (
        "Connector '{connector_id}': multiple handlers "
        "({handler_ids}) share the same xsoar-integration-id "
        "'{integration_id}'. Handler ↔ integration must be 1:1. "
        "Split into distinct handlers or fix the label."
    )
    related_field = "triggering.labels.xsoar-integration-id"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_HANDLER]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            # Group handlers by integration id label. Handlers with no
            # label are skipped (CO164 handles the missing-label case).
            by_id: Dict[str, List[HandlerData]] = {}
            for handler in connector.handlers:
                integration_id = handler.xsoar_integration_id
                if not integration_id:
                    continue
                by_id.setdefault(integration_id, []).append(handler)

            # Emit one finding per duplicated integration id, listing
            # every handler that shares it (sorted for determinism).
            for integration_id, handlers in sorted(by_id.items()):
                if len(handlers) < 2:
                    continue
                sorted_handlers = sorted(handlers, key=lambda h: h.id)
                handler_ids = ", ".join(h.id for h in sorted_handlers)

                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_ids=handler_ids,
                            integration_id=integration_id,
                        ),
                        content_object=connector,
                        path=self._first_offender_path(sorted_handlers),
                    )
                )

        return results

    @staticmethod
    def _first_offender_path(handlers: List[HandlerData]) -> Optional[Path]:
        """Return the first handler's ``file_path``, or ``None`` if
        no handler in the group has a resolvable path."""
        for h in handlers:
            fp = h.file_path
            if fp is not None:
                return fp
        return None
