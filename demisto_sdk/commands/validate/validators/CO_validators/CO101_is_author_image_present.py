from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector


class IsAuthorImagePresentValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO101"
    description = (
        "Validates that a connector's metadata.author_image is present and non-empty."
    )
    rationale = (
        "Every connector must declare an author image so the platform can "
        "render the connector's branding. A missing or empty "
        "metadata.author_image leaves the connector without a visual "
        "identity."
    )
    error_message = (
        "Connector '{connector_id}' must have a non-empty " "metadata.author_image."
    )
    related_field = "metadata.author_image"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            author_image = connector.connector_metadata.author_image
            if not author_image or not author_image.strip():
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                        ),
                        content_object=connector,
                    )
                )

        return results
