"""CO100 — IsMatchingIntegrationExist

Validates that for each XSOAR handler in a connector, the referenced
``xsoar-integration-id`` and ``xsoar-pack-id`` from ``triggering.labels``
actually exist in the content repo graph.
"""

from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingIntegrationExistValidator(BaseValidator[ContentTypes], ABC):
    error_code = "CO100"
    description = (
        "Validates that the handler's matching pack and integration ID "
        "exist in the content repository."
    )
    rationale = (
        "Each XSOAR handler in a connector references a pack and integration "
        "via triggering.labels. These must exist in the content repo to ensure "
        "the connector can be properly linked."
    )
    error_message = (
        "Connector '{0}' has handler '{1}' referencing non-existent content: {2}"
    )
    related_field = "triggering.labels"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool = False,
    ) -> List[ValidationResult]:
        """Check that referenced integrations and packs exist in the graph.

        For each XSOAR handler in each connector:
        - If ``xsoar-integration-id`` is set, verify an Integration with that
          display name exists.
        - If ``xsoar-pack-id`` is set, verify a Pack with that object_id exists.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            for handler in connector.handlers:
                if not handler.is_xsoar:
                    continue

                missing: List[str] = []

                # Check integration reference
                if integration_id := handler.xsoar_integration_id:
                    integrations = self.graph_interface.search(
                        content_type=ContentType.INTEGRATION,
                        object_id=integration_id,
                    )
                    if not integrations:
                        # Also try searching by display name since
                        # xsoar-integration-id may be the display name
                        integrations = self.graph_interface.search(
                            content_type=ContentType.INTEGRATION,
                            name=integration_id,
                        )
                    if not integrations:
                        missing.append(
                            f"Integration '{integration_id}' "
                            f"(from xsoar-integration-id)"
                        )

                # Check pack reference
                if pack_id := handler.xsoar_pack_id:
                    packs = self.graph_interface.search(
                        content_type=ContentType.PACK,
                        object_id=pack_id,
                    )
                    if not packs:
                        missing.append(f"Pack '{pack_id}' (from xsoar-pack-id)")

                if missing:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                connector.object_id,
                                handler.id,
                                ", ".join(missing),
                            ),
                            content_object=connector,
                        )
                    )

        return results
