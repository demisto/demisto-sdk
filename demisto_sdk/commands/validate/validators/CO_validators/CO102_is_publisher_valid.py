from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_PUBLISHER = "Palo Alto Networks"


class IsPublisherValidValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO102"
    description = (
        "Validates that a connector's metadata.publisher is " "'Palo Alto Networks'."
    )
    rationale = (
        "Per the connector migration guide (§3.3), every connector is "
        "published by Palo Alto Networks, so metadata.publisher must be set "
        "to 'Palo Alto Networks'."
    )
    error_message = (
        "Connector '{connector_id}' metadata.publisher must be "
        "'{expected}', got '{actual}'."
    )
    related_field = "metadata.publisher"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            publisher = connector.connector_metadata.publisher
            if publisher != EXPECTED_PUBLISHER:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            expected=EXPECTED_PUBLISHER,
                            actual=publisher,
                        ),
                        content_object=connector,
                    )
                )

        return results
