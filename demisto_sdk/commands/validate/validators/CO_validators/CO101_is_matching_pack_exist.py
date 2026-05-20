from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingPackExistValidator(BaseValidator[ContentTypes]):
    error_code = "CO101"
    description = (
        "Validates that each XSOAR handler in a connector has an "
        "xsoar-pack-id label and that the referenced pack exists in the "
        "content repository."
    )
    rationale = (
        "Every XSOAR handler must declare an xsoar-pack-id in its "
        "triggering.labels so the platform knows which pack the handler "
        "depends on. A handler that is missing the label or whose referenced "
        "pack cannot be found in the graph is invalid."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handlers with pack problems: "
        "{handler_details}"
    )
    related_field = "triggering.labels"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check that each XSOAR handler has a valid pack reference.

        Two failure cases:
        1. Handler has ``xsoar_pack_id`` but the pack is NOT found in the
           graph — the referenced pack does not exist.
        2. Handler has no ``xsoar_pack_id`` at all — the handler YAML is
           missing the ``xsoar-pack-id`` triggering label.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            # Case 1: declared pack ID but not resolved in graph
            unresolved = [
                f"handler '{h.id}' -> pack-id '{h.xsoar_pack_id}' not found"
                for h in connector.xsoar_handlers
                if h.xsoar_pack_id and not _pack_exists_in_graph(h.xsoar_pack_id)
            ]

            # Case 2: no pack ID declared at all
            missing_id = [
                f"handler '{h.id}' is missing xsoar-pack-id in triggering.labels"
                for h in connector.xsoar_handlers
                if not h.xsoar_pack_id
            ]

            handler_details = unresolved + missing_id

            if handler_details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(handler_details),
                        ),
                        content_object=connector,
                    )
                )

        return results


def _pack_exists_in_graph(pack_id: str) -> bool:
    """Look up a pack in the content graph by ``object_id``.

    Returns True iff the graph search returns at least one matching pack.
    If the graph interface is not available, returns False (treats the pack
    as missing — consistent with CO100's behavior in
    ``_graph_search_integration``).
    """
    graph = BaseValidator.graph_interface
    if not graph:
        logger.debug("Graph interface not available, treating pack as missing.")
        return False
    results = graph.search(
        content_type=ContentType.PACK,
        object_id=pack_id,
    )
    return bool(results)
