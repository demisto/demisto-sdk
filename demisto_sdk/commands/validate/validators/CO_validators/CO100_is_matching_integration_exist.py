from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingIntegrationExistValidator(BaseValidator[ContentTypes]):
    error_code = "CO100"
    description = (
        "Validates that each XSOAR handler in a connector references an "
        "integration that exists in the content repository."
    )
    rationale = (
        "Each XSOAR handler references an integration via triggering.labels. "
        "The ConnectorAwareInitializer resolves these references and populates "
        "handler.related_integration. If it is None, the referenced integration "
        "does not exist."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handlers referencing "
        "integrations that could not be found in the content repo: {handler_details}"
    )
    related_field = "triggering.labels"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check that each XSOAR handler has a matched integration.

        The ConnectorAwareInitializer already resolved the integration references.
        If ``handler.related_integration`` is None, the integration was not found.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            if not connector.xsoar_handlers:
                continue

            # Collect unresolved handlers
            unresolved_parts = [
                f"handler '{h.id}' -> integration-id '{h.xsoar_integration_id}'"
                for h in connector.xsoar_handlers
                if h.xsoar_integration_id and h.related_integration is None
            ]

            if unresolved_parts:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(unresolved_parts),
                        ),
                        content_object=connector,
                    )
                )

        return results
