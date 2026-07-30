from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.connector import Connector
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    ConnectorsValidator,
    ValidationResult,
)

ContentTypes = Connector

EXPECTED_CONNECTION_TITLE = "Connection"
EXPECTED_CONNECTION_DESCRIPTION = (
    "Enter the credentials to securely authorize the connection"
)


class IsValidConnectionMetadataValidator(ConnectorsValidator[ContentTypes]):
    error_code = "CO118"
    description = (
        "Validates the connection.yaml metadata block: title must equal "
        "'Connection' and description must equal the standard authorization "
        "prompt."
    )
    rationale = (
        "The connection page presents a consistent, standardized experience "
        "across all connectors. Its title and description are fixed strings."
    )
    error_message = (
        "Connector '{connector_id}' connection metadata is invalid: {details}."
    )
    related_field = "metadata"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.CONNECTOR_CONNECTION]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for connector in content_items:
            connection = connector.connection
            if connection is None:
                # No connection.yaml - nothing to validate here.
                continue

            details: List[str] = []

            if connection.title != EXPECTED_CONNECTION_TITLE:
                details.append(
                    f"metadata.title must be '{EXPECTED_CONNECTION_TITLE}', "
                    f"got '{connection.title}'"
                )

            if connection.description != EXPECTED_CONNECTION_DESCRIPTION:
                details.append(
                    f"metadata.description must be "
                    f"'{EXPECTED_CONNECTION_DESCRIPTION}', got "
                    f"'{connection.description}'"
                )

            if details:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            connector_id=connector.object_id,
                            details="; ".join(details),
                        ),
                        content_object=connector,
                        path=connector.connection_file.file_path,
                    )
                )

        return results
