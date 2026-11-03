from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsMatchingIntegrationExistValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO164"
    description = (
        "Validates that each XSOAR handler in a connector has an "
        "xsoar-integration-id label AND that the label equals the "
        "referenced integration's YML id verbatim."
    )
    rationale = (
        "Every XSOAR handler must declare an xsoar-integration-id in its "
        "triggering.labels so the platform knows which integration to invoke. "
        "The label MUST equal the integration YML id verbatim (case-sensitive, "
        "no slugification). This invariant is what lets CO122/CO139 compare "
        "view_group.id against integration.object_id verbatim - if this "
        "validator passes, `xsoar-integration-id` and `integration.object_id` "
        "are interchangeable."
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

        Three failure cases:
        1. Handler has no ``xsoar_integration_id`` at all - the handler YAML is
           missing the ``xsoar-integration-id`` triggering label.
        2. Handler has ``xsoar_integration_id`` but ``related_integration`` is
           None - the referenced integration was not found in the content repo.
        3. Handler has ``xsoar_integration_id`` that resolved to an integration
           (via graph fallback) but does NOT equal that integration's
           ``object_id`` verbatim - the label is drifted from the YML id.
        """
        results: List[ValidationResult] = []

        for connector in content_items:
            problems: List[str] = []
            for h in connector.xsoar_handlers:
                # Case 1: no xsoar-integration-id label at all.
                if not h.xsoar_integration_id:
                    problems.append(
                        f"handler '{h.id}' is missing "
                        f"xsoar-integration-id in triggering.labels"
                    )
                    continue
                # Case 2: label present but no resolved integration.
                if h.related_integration is None:
                    problems.append(
                        f"handler '{h.id}' -> integration-id "
                        f"'{h.xsoar_integration_id}' not found"
                    )
                    continue
                # Case 3: resolved (via graph fallback) but the label does
                # NOT equal the integration YML id verbatim.
                actual = h.related_integration.object_id
                if h.xsoar_integration_id != actual:
                    problems.append(
                        f"handler '{h.id}' has xsoar-integration-id "
                        f"'{h.xsoar_integration_id}' but the resolved "
                        f"integration's YML id is '{actual}' - they must "
                        f"match verbatim (case-sensitive, no slugification)"
                    )

            if problems:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            handler_details="\n".join(problems),
                        ),
                        content_object=connector,
                    )
                )

        return results
