from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsConnectorIntegrationNotExcludedFromTightlyCoupledValidator(
    ConnectorsValidator[ContentTypes]
):
    """CO196 -- connector-side counterpart of CO192's opt-out.

    An integration that sets ``excludefromtightlycoupled: true`` declares it
    has no connector. Once a connector XSOAR handler references it, the flag
    is stale and must be set to ``false`` or removed.

    Handlers whose integration was not resolved are skipped (CO164 owns that).
    """

    error_code = "CO196"
    description = (
        "Validates that no connector XSOAR handler references an integration "
        "that sets 'excludefromtightlycoupled: true'."
    )
    rationale = (
        "'excludefromtightlycoupled: true' marks an integration as having no "
        "connector. When a connector is added for it, the flag must be set "
        "to false or removed so the integration is tightly coupled again."
    )
    error_message = (
        "Connector '{connector_id}' references integration(s) {integration_ids} "
        "that set 'excludefromtightlycoupled: true'. Set the flag to false or "
        "remove it from the integration(s)."
    )
    related_field = "triggering.labels"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            excluded_ids = sorted(
                {
                    handler.related_integration.object_id
                    for handler in connector.xsoar_handlers
                    if handler.related_integration is not None
                    and handler.related_integration.exclude_from_tightly_coupled
                }
            )
            if excluded_ids:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            integration_ids=", ".join(f"'{i}'" for i in excluded_ids),
                        ),
                        content_object=connector,
                    )
                )

        return results
