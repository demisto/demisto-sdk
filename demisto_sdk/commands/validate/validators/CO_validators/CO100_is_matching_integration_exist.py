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
        "Validates that each XSOAR handler in a connector has an "
        "xsoar-integration-id label and that the referenced integration "
        "exists in the content repository."
    )
    rationale = (
        "Every XSOAR handler must declare an xsoar-integration-id in its "
        "triggering.labels so the platform knows which integration to invoke. "
        "The ConnectorAwareInitializer resolves these references and populates "
        "handler.related_integration. A handler that is missing the label or "
        "whose referenced integration cannot be found is invalid."
    )
    error_message = (
        "Connector '{connector_id}' has XSOAR handlers with integration "
        "problems: {handler_details}"
    )
    related_field = "triggering.labels"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """Check that each XSOAR handler has a valid integration reference.

        Two failure cases:
        1. Handler has ``xsoar_integration_id`` but ``related_integration`` is
           None — the referenced integration was not found in the content repo.
        2. Handler has no ``xsoar_integration_id`` at all — the handler YAML is
           missing the ``xsoar-integration-id`` triggering label.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            # Case 1: declared integration ID but not resolved
            unresolved = [
                f"handler '{h.id}' -> integration-id '{h.xsoar_integration_id}' not found"
                for h in connector.xsoar_handlers
                if h.xsoar_integration_id and h.related_integration is None
            ]

            # Case 2: no integration ID declared at all
            missing_id = [
                f"handler '{h.id}' is missing xsoar-integration-id in triggering.labels"
                for h in connector.xsoar_handlers
                if not h.xsoar_integration_id
            ]

            unresolved_parts = unresolved + missing_id

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
