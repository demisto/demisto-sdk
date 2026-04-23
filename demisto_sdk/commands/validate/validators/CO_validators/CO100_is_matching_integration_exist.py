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
        "Validates that the connector's XSOAR handlers reference an integration "
        "that exists in the content repository."
    )
    rationale = (
        "Each XSOAR handler in a connector references an integration "
        "via triggering.labels. The ConnectorAwareInitializer resolves these "
        "references and populates related_content. If it is None, the "
        "referenced integration does not exist."
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
        """Check that each connector has a matched integration via related_content.

        The ConnectorAwareInitializer already resolved the integration references.
        If ``connector.related_content`` is None, the integration was not found.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            if not connector.xsoar_handlers:
                continue

            if connector.related_content is not None:
                # Integration was found and linked -- valid
                continue

            # Collect handler ID -> integration ID pairs for the error message
            handler_details_parts = [
                f"handler '{h.id}' -> integration-id '{h.xsoar_integration_id}'"
                for h in connector.xsoar_handlers
                if h.xsoar_integration_id
            ]

            if handler_details_parts:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(handler_details_parts),
                        ),
                        content_object=connector,
                    )
                )

        return results
